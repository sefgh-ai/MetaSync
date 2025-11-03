import os
import json
import time
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import requests
from supabase import create_client, Client

# -------------------------------------------------
#  Environment variables (Vercel)
# -------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([GITHUB_TOKEN, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing: GITHUB_TOKEN, SUPABASE_URL, or SUPABASE_SERVICE_ROLE_KEY")

# Supabase client with SERVICE ROLE (bypasses RLS)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# GitHub constants
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {GITHUB_TOKEN}",
}
BASE_URL = "https://api.github.com"
PER_PAGE = 100
LANGUAGES = ["Python", "Java", "HTML", "CSS", "JavaScript", "SQL"]


# -------------------------------------------------
#  Error Logging to Supabase
# -------------------------------------------------
def log_error(
    source: str,
    repo_full_name: Optional[str],
    error_type: str,
    error_message: str,
    request_url: Optional[str] = None,
    request_method: Optional[str] = None,
    response_status: Optional[int] = None,
    response_body: Optional[str] = None,
):
    payload = {
        "source": source,
        "repo_full_name": repo_full_name,
        "error_type": error_type,
        "error_message": str(error_message)[:500],
        "request_url": request_url,
        "request_method": request_method,
        "response_status": response_status,
        "response_body": (response_body or "")[:1000] if response_body else None,
    }
    try:
        supabase.table("error_logs").insert(payload).execute()
        print(f"[ERROR LOGGED] {source} | {error_type} | {repo_full_name or 'N/A'}")
    except Exception as e:
        print(f"[FATAL] Failed to log error: {e}\nPayload: {payload}")


# -------------------------------------------------
#  Rate Limit Handler
# -------------------------------------------------
def handle_rate_limit(response: requests.Response):
    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
    reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
    if remaining < 10:
        sleep_sec = max(reset_time - int(time.time()), 60) + 10
        print(f"[RATE LIMIT] Pausing {sleep_sec}s (remaining: {remaining})")
        time.sleep(sleep_sec)


# -------------------------------------------------
#  Core Functions
# -------------------------------------------------
def yesterday_str() -> str:
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def search_repos(lang: str, date_str: str) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1
    while len(repos) < 1000:
        query = f'language:{lang} created:{date_str}'
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": PER_PAGE,
            "page": page,
        }
        try:
            r = requests.get(f"{BASE_URL}/search/repositories", headers=HEADERS, params=params, timeout=15)
            r.raise_for_status()
            handle_rate_limit(r)
        except requests.exceptions.RequestException as e:
            log_error(
                source="search",
                repo_full_name=None,
                error_type="RequestError",
                error_message=str(e),
                request_url=e.request.url if hasattr(e, 'request') and e.request else None,
                request_method="GET",
                response_status=getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                response_body=getattr(e.response, 'text', None) if hasattr(e, 'response') else None,
            )
            break

        data = r.json()
        items = data.get("items", [])
        if not items:
            break

        repos.extend(items)
        print(f"[INFO] {lang} page {page}: +{len(items)} (total {len(repos)})")

        page += 1
        time.sleep(2)
    return [repo for repo in repos if repo.get("size", 0) > 0]


def has_readme(full_name: str) -> bool:
    url = f"{BASE_URL}/repos/{full_name}/contents/README.md"
    try:
        r = requests.head(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return True
        elif r.status_code == 404:
            return False
        else:
            log_error(
                source="readme_check",
                repo_full_name=full_name,
                error_type="UnexpectedStatus",
                error_message=f"HEAD returned {r.status_code}",
                request_url=url,
                request_method="HEAD",
                response_status=r.status_code,
            )
            return False
    except requests.exceptions.RequestException as e:
        log_error(
            source="readme_check",
            repo_full_name=full_name,
            error_type="RequestError",
            error_message=str(e),
            request_url=url,
            request_method="HEAD",
            response_status=getattr(e.response, 'status_code', None),
        )
        return False


def count_lines(full_name: str, default_branch: str = "main") -> int:
    lines = 0
    branch_url = f"{BASE_URL}/repos/{full_name}/git/refs/heads/{default_branch}"
    try:
        br = requests.get(branch_url, headers=HEADERS, timeout=10)
        br.raise_for_status()
        tree_sha = br.json().get("object", {}).get("sha")
        if not tree_sha:
            return 0
    except Exception as e:
        log_error(
            source="line_count",
            repo_full_name=full_name,
            error_type="BranchError",
            error_message=str(e),
            request_url=branch_url,
        )
        return 0

    tree_url = f"{BASE_URL}/repos/{full_name}/git/trees/{tree_sha}?recursive=1"
    try:
        tree_r = requests.get(tree_url, headers=HEADERS, timeout=15)
        tree_r.raise_for_status()
        for node in tree_r.json().get("tree", []):
            if node["type"] != "blob":
                continue
            path = node["path"].lower()
            if path.endswith((".png", ".jpg", ".gif", ".pdf", ".bin", ".exe", ".zip", ".lock")):
                continue
            content_url = f"{BASE_URL}/repos/{full_name}/contents/{node['path']}"
            content_r = requests.get(content_url, headers=HEADERS, timeout=10)
            if content_r.status_code != 200:
                continue
            try:
                raw = base64.b64decode(content_r.json()["content"]).decode("utf-8", errors="ignore")
                lines += sum(1 for line in raw.split("\n") if line.strip())
            except Exception as e:
                # Skip files that can't be decoded or parsed
                continue
    except Exception as e:
        log_error(
            source="line_count",
            repo_full_name=full_name,
            error_type="TreeError",
            error_message=str(e),
            request_url=tree_url,
        )
    return lines


def repo_exists(full_name: str) -> bool:
    try:
        resp = supabase.table("repositories").select("full_name").eq("full_name", full_name).limit(1).execute()
        return bool(resp.data)
    except Exception as e:
        log_error(
            source="duplicate_check",
            repo_full_name=full_name,
            error_type="SupabaseError",
            error_message=str(e),
        )
        return False


def insert_repo(repo: Dict[str, Any], lines: int) -> bool:
    payload = {
        "full_name": repo["full_name"],
        "name": repo["name"],
        "description": repo.get("description") or "",
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "size": repo["size"],
        "language": repo["language"],
        "created_at": repo["created_at"],
        "updated_at": repo["updated_at"],
        "has_readme": True,
        "lines_count": lines,
    }
    try:
        supabase.table("repositories").insert(payload).execute()
        return True
    except Exception as e:
        log_error(
            source="insert_repo",
            repo_full_name=repo["full_name"],
            error_type="SupabaseInsertError",
            error_message=str(e),
        )
        return False


# -------------------------------------------------
#  Vercel Handler
# -------------------------------------------------
def handler(event, context=None):
    date_str = yesterday_str()
    print(f"\n=== FETCHING REPOS FOR {date_str} ===")

    total_inserted = 0
    for lang in LANGUAGES:
        print(f"\n--- PROCESSING {lang} ---")
        try:
            candidates = search_repos(lang, date_str)
        except Exception as e:
            log_error("search_loop", None, "Critical", f"Failed to search {lang}: {e}")
            continue

        inserted_lang = 0
        for idx, repo in enumerate(candidates, 1):
            full_name = repo["full_name"]

            if idx % 50 == 0:
                print(f"  → checked {idx}/{len(candidates)}")

            if repo_exists(full_name):
                continue

            if not has_readme(full_name):
                continue

            if repo["size"] > 500:
                lines = repo["size"] // 50
            else:
                lines = count_lines(full_name, repo.get("default_branch", "main"))
            if lines <= 10:
                continue

            if insert_repo(repo, lines):
                inserted_lang += 1
                total_inserted += 1

            time.sleep(0.5)

        print(f"  → inserted {inserted_lang} repos for {lang}")

    print(f"\n=== DONE | TOTAL INSERTED: {total_inserted} ===")
    return {
        "statusCode": 200,
        "body": json.dumps({"date": date_str, "inserted": total_inserted}),
    }
