import os
import json
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def handler(event, context=None):
    """
    API endpoint to get real-time statistics about repositories
    """
    try:
        # Get all repositories
        response = supabase.table("repositories").select("*").execute()
        repos = response.data

        # Calculate statistics
        total_repos = len(repos)
        total_stars = sum(repo.get("stars", 0) for repo in repos)
        total_forks = sum(repo.get("forks", 0) for repo in repos)
        total_lines = sum(repo.get("lines_count", 0) for repo in repos)

        # Language breakdown
        language_stats = {}
        for repo in repos:
            lang = repo.get("language", "Unknown")
            if lang not in language_stats:
                language_stats[lang] = {
                    "count": 0,
                    "stars": 0,
                    "forks": 0,
                    "lines": 0
                }
            language_stats[lang]["count"] += 1
            language_stats[lang]["stars"] += repo.get("stars", 0)
            language_stats[lang]["forks"] += repo.get("forks", 0)
            language_stats[lang]["lines"] += repo.get("lines_count", 0)

        # Get recent repos (last 20)
        recent_repos = sorted(repos, key=lambda x: x.get("created_at", ""), reverse=True)[:20]

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps({
                "summary": {
                    "total_repos": total_repos,
                    "total_stars": total_stars,
                    "total_forks": total_forks,
                    "total_lines": total_lines,
                },
                "languages": language_stats,
                "recent_repos": recent_repos,
                "success": True
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({
                "error": str(e),
                "success": False
            })
        }
