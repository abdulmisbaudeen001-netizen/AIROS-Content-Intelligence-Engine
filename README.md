# AIROS Content Intelligence Engine (ACIE) v1.0

Autonomous AI publishing system. Discovers trending topics, researches them from multiple sources, writes original articles, and publishes to Blogger — automatically, three times a day.

---

## Setup

### 1. Clone and install

```bash
pip install -r requirements.txt
playwright install chromium   # optional — only needed for JS-heavy scraping
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your keys
```

Required values:
- `OPENROUTER_API_KEY` — from openrouter.ai
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — from Google Cloud Console
- `BLOGGER_BLOG_ID` — from your Blogger dashboard URL

### 3. Google Cloud Setup

1. Go to console.cloud.google.com
2. Create a project → Enable **Blogger API v3**
3. Create OAuth2 credentials → Web Application
4. Add `http://localhost:8000/auth/callback` as authorized redirect URI
5. Copy Client ID and Client Secret to `.env`

### 4. Authorize Blogger (one-time)

```bash
python app.py
# Visit: http://localhost:8000/auth/url
# Open the URL in your browser, grant access
# Google redirects back to /auth/callback automatically
# You'll see: {"status": "success"}
```

After this, tokens are saved and AIROS publishes without manual login.

### 5. Run

```bash
python app.py
```

AIROS starts, connects to the database, and begins the scheduler.

---

## Manual triggers

```bash
# Trigger a full publishing run
curl -X POST http://localhost:8000/run/morning

# Run pipeline for a specific topic
curl -X POST "http://localhost:8000/run/topic/AI%20breakthrough%202025"

# Check active workflows
curl http://localhost:8000/status

# View recent articles
curl http://localhost:8000/articles

# View learning insights
curl http://localhost:8000/insights
```

---

## Architecture

```
app.py                    FastAPI + scheduler startup
scheduler.py              Morning / afternoon / evening triggers
orchestrator/
  orchestrator.py         Pipeline coordinator (the brain)
agents/
  trend_agent.py          Agent 1: Discover trending topics
  source_agent.py         Agent 2: Collect sources per topic
  verification_agent.py   Agent 3: Verify facts across sources
  knowledge_agent.py      Agent 4: Add context and analysis
  editor_agent.py         Agent 5: Design article structure
  writer_agent.py         Agent 6: Write the full article
  seo_agent.py            Agent 7: SEO optimization
  quality_agent.py        Agent 8: Policy and quality gate
  publisher_agent.py      Agent 9: Publish to Blogger
  learning_agent.py       Agent 10: Learn from performance
services/
  llm_service.py          OpenRouter gateway (model-agnostic)
  rss_service.py          RSS feed collection
  search_service.py       Trend signal discovery
  scraper_service.py      Web scraping + Playwright fallback
  analytics_service.py    Post performance tracking
cms/
  blogger.py              Blogger OAuth2 + publish API
database/
  connection.py           SQLAlchemy setup
  models.py               All ORM tables
  repository.py           All DB operations
memory/
  short_memory.py         Current workflow state
  long_memory.py          Learning insights cache
```

---

## LLM Model Chain

All agents call `llm_service.generate()` — they never know which model responds.

Routing:
1. `openrouter/auto` (free router — primary)
2. `deepseek/deepseek-chat-v3-0324:free` (fallback)
3. `tencent/hunyuan-a13b-instruct:free` (fallback)
4. `qwen/qwen3-8b:free` (emergency fallback)

To add a model, edit `LLM_FALLBACK_CHAIN` in `config.py`.

---

## Publishing Schedule

| Window    | Default Time |
|-----------|-------------|
| Morning   | 07:00       |
| Afternoon | 13:00       |
| Evening   | 19:00       |

Change in `config.py`: `SCHEDULE_MORNING_HOUR`, etc.

---

## Quality Gates

Articles must pass all thresholds before publishing:

| Score       | Minimum |
|-------------|---------|
| Quality     | 80      |
| SEO         | 75      |
| Policy      | 90      |
| Originality | 75      |
| Readability | 70      |

Failed articles are revised automatically (up to 2 times), then published regardless.
