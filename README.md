# AIROS Content Intelligence Engine (ACIE) v1.0

Autonomous AI publishing system. Discovers trending topics, researches them from multiple independent sources, writes original articles, and publishes to Blogger — automatically, three times a day.

---

## Environment Variables (Render)

All secrets are set in **Render → your service → Environment**. Nothing goes in code or GitHub.

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | From openrouter.ai |
| `GOOGLE_CLIENT_ID` | Yes | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Yes | From Google Cloud Console |
| `BLOGGER_BLOG_ID` | Yes | From Blogger dashboard URL |
| `DATABASE_URL` | Yes | Render provides this when you attach a PostgreSQL database |
| `RENDER_SERVICE_URL` | Yes | Your Render service URL e.g. `https://airos-engine.onrender.com` |
| `TOKEN_FILE` | No | Defaults to `/tmp/.acie_tokens.json` |
| `PORT` | No | Render sets this automatically |
| `DEBUG` | No | Set to `true` for verbose output |

---

## Deployment on Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "AIROS ACIE v1.0"
git remote add origin https://github.com/yourname/airos-acie.git
git push -u origin main
```

`.gitignore` already blocks `.env`, tokens, database files, and logs.

### 2. Create Render service

1. Go to render.com → New → Web Service
2. Connect your GitHub repo
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Add a **PostgreSQL** database → Render auto-sets `DATABASE_URL`
6. Add all environment variables in the **Environment** tab

### 3. Google Cloud Setup

1. Go to console.cloud.google.com
2. Create a project → Enable **Blogger API v3**
3. Credentials → Create → OAuth 2.0 Client ID → Web Application
4. Add authorized redirect URI: `https://your-render-url.onrender.com/auth/callback`
5. Copy Client ID and Client Secret into Render environment variables

### 4. Authorize Blogger (one-time, after deploy)

```
1. Visit: https://your-render-url.onrender.com/auth/url
2. Copy the auth_url from the response
3. Open it in your browser
4. Sign in with Google and grant access
5. Google redirects back to /auth/callback automatically
6. You will see: {"status": "success"}
```

Tokens are saved to `/tmp/.acie_tokens.json` on the Render instance.
AIROS will publish without manual login from this point forward.

---

## Manual Triggers (via Render URL)

```bash
# Check system health
curl https://your-render-url.onrender.com/

# Check Blogger authorization status
curl https://your-render-url.onrender.com/auth/status

# Trigger a publishing run manually
curl -X POST https://your-render-url.onrender.com/run/morning

# Run pipeline for a specific topic
curl -X POST "https://your-render-url.onrender.com/run/topic/AI%20chip%20shortage"

# Monitor active workflows
curl https://your-render-url.onrender.com/status

# View published articles
curl https://your-render-url.onrender.com/articles

# View learning insights
curl https://your-render-url.onrender.com/insights
```

---

## Architecture

```
app.py                     FastAPI application + startup
config.py                  All settings — reads from Render environment
scheduler.py               3 daily publishing windows + retry queue
orchestrator/
  orchestrator.py          Pipeline brain — coordinates all agents
agents/
  trend_agent.py           Agent 1: Discover trending topics
  source_agent.py          Agent 2: Collect sources per topic
  verification_agent.py    Agent 3: Cross-verify facts
  knowledge_agent.py       Agent 4: Add context and analysis
  editor_agent.py          Agent 5: Design article structure
  writer_agent.py          Agent 6: Write the full article
  seo_agent.py             Agent 7: SEO optimization
  quality_agent.py         Agent 8: Policy and quality gate
  publisher_agent.py       Agent 9: Publish to Blogger
  learning_agent.py        Agent 10: Learn from performance
services/
  llm_service.py           OpenRouter gateway — model-agnostic
  rss_service.py           RSS feed collection
  search_service.py        Trend signal discovery
  scraper_service.py       Web scraping + Playwright fallback
  analytics_service.py     Post performance tracking
cms/
  blogger.py               Blogger OAuth2 + Blogger API
database/
  connection.py            SQLAlchemy + PostgreSQL
  models.py                All database tables
  repository.py            All database operations
memory/
  short_memory.py          Live workflow state
  long_memory.py           Learning insights cache
utils/
  retry.py                 Exponential backoff decorator
```

---

## LLM Model Chain

Agents call `llm_service.generate()` only — they never know which model responded.

```
1. openrouter/auto                        (primary — free router)
2. deepseek/deepseek-chat-v3-0324:free   (fallback)
3. tencent/hunyuan-a13b-instruct:free    (fallback)
4. qwen/qwen3-8b:free                    (emergency fallback)
```

To add a model: edit `LLM_FALLBACK_CHAIN` in `config.py`.

---

## Publishing Schedule

| Window | Time |
|---|---|
| Morning | 07:00 |
| Afternoon | 13:00 |
| Evening | 19:00 |

Change in `config.py`: `SCHEDULE_MORNING_HOUR`, `SCHEDULE_AFTERNOON_HOUR`, `SCHEDULE_EVENING_HOUR`.

---

## Quality Gates

Articles must pass all thresholds or are revised (up to 2 attempts) before publishing.

| Score | Minimum |
|---|---|
| Quality | 80 |
| SEO | 75 |
| Policy | 90 |
| Originality | 75 |
| Readability | 70 |
