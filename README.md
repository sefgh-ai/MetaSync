# MetaSync 🚀

A powerful GitHub repository analytics tool that automatically tracks and analyzes repositories created yesterday across multiple programming languages.

## Features ✨

- 🔄 **Automatic Daily Syncing** - Runs every day at midnight UTC via Vercel cron jobs
- 📊 **Real-time Dashboard** - Beautiful web interface to view all tracked repositories
- 🌐 **Multi-language Support** - Tracks Python, Java, HTML, CSS, JavaScript, and SQL repos
- 📈 **Advanced Analytics** - Stars, forks, lines of code, and language breakdowns
- 🔍 **Smart Filtering** - Only tracks repos with README files and meaningful code
- ☁️ **Cloud-powered** - Runs on Vercel with Supabase backend
- 🛡️ **Error Logging** - Comprehensive error tracking in Supabase

## Live Dashboard 🎨

The dashboard displays:

- **Total repositories** tracked
- **Total stars** and **forks** across all repos
- **Lines of code** analyzed
- **Language breakdown** with visual charts
- **Recent repositories** with direct GitHub links
- **Auto-refresh** every 30 seconds

## Setup Instructions 🛠️

### 1. Prerequisites

- GitHub account with a Personal Access Token
- Supabase account with a project
- Vercel account for deployment

### 2. Supabase Setup

Create two tables in your Supabase project:

**Table: `repositories`**

```sql
CREATE TABLE repositories (
  id BIGSERIAL PRIMARY KEY,
  full_name TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  stars INTEGER DEFAULT 0,
  forks INTEGER DEFAULT 0,
  size INTEGER DEFAULT 0,
  language TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE,
  has_readme BOOLEAN DEFAULT FALSE,
  lines_count INTEGER DEFAULT 0,
  synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_language ON repositories(language);
CREATE INDEX idx_created_at ON repositories(created_at);
```

**Table: `error_logs`**

```sql
CREATE TABLE error_logs (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  repo_full_name TEXT,
  error_type TEXT NOT NULL,
  error_message TEXT,
  request_url TEXT,
  request_method TEXT,
  response_status INTEGER,
  response_body TEXT,
  logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_error_logged_at ON error_logs(logged_at);
```

### 3. Environment Variables

Set these in your Vercel project settings:

```env
GITHUB_TOKEN=your_github_personal_access_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

### 4. Update Dashboard Configuration

Edit `index.html` and replace the placeholders:

```javascript
const SUPABASE_URL = 'https://your-project.supabase.co';
const SUPABASE_ANON_KEY = 'your_supabase_anon_key';
```

### 5. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

## API Endpoints 🔌

### `GET /api/stats`

Returns real-time statistics about all tracked repositories.

**Response:**

```json
{
  "summary": {
    "total_repos": 1250,
    "total_stars": 45890,
    "total_forks": 12340,
    "total_lines": 8567890
  },
  "languages": {
    "Python": {
      "count": 420,
      "stars": 18500,
      "forks": 4200,
      "lines": 3200000
    }
  },
  "recent_repos": [...],
  "success": true
}
```

### `POST /api/sync`

Manually trigger the repository sync process (also runs automatically via cron).

## How It Works 🔧

1. **Cron Job** triggers `/api/sync` every day at midnight UTC
2. **GitHub Search** queries repos created yesterday for each language
3. **Filtering** checks for README and minimum lines of code
4. **Line Counting** analyzes repository content (smart estimation for large repos)
5. **Database Storage** saves repo data to Supabase
6. **Dashboard** displays real-time stats from Supabase
7. **Error Logging** tracks any issues for debugging

## Technologies Used 💻

- **Backend**: Python 3.11
- **Database**: Supabase (PostgreSQL)
- **Hosting**: Vercel Serverless Functions
- **APIs**: GitHub REST API v3
- **Frontend**: HTML5, CSS3, Vanilla JavaScript

## Configuration ⚙️

Modify `LANGUAGES` array in `main.py` to track different languages:

```python
LANGUAGES = ["Python", "Java", "HTML", "CSS", "JavaScript", "SQL"]
```

Adjust sync schedule in `vercel.json`:

```json
"schedule": "0 0 * * *"  // Daily at midnight UTC
```

## Features in Detail 📋

### Smart Line Counting

- Large repos (>500KB): Estimates based on size
- Small repos: Analyzes actual file content
- Skips binary files (images, PDFs, etc.)
- Uses base64 decoding for file contents

### Rate Limit Handling

- Monitors GitHub API rate limits
- Automatic pausing when limit is near
- Respects reset times

### Error Handling

- Logs all errors to Supabase
- Continues processing on failures
- Detailed error context for debugging

## License 📄

MIT License - feel free to use and modify!

## Contributing 🤝

Contributions welcome! Feel free to submit issues and pull requests.

---

Made with ❤️ for the open-source community

Well fucking fetchs the repos from the github currently via github api key . Storing only popular languages with stars as filter . the
