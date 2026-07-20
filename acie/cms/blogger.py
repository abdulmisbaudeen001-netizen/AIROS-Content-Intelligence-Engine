"""
AIROS Content Intelligence Engine
Blogger CMS Adapter — OAuth2 flow + publish operations.

OAuth2 Flow (one-time setup):
  1. Visit GET /auth/url  → opens Google consent page
  2. Google redirects to GOOGLE_REDIRECT_URI (your Render URL + /auth/callback)
  3. GET /auth/callback exchanges the code → tokens saved to TOKEN_FILE
  4. All future calls auto-refresh the access token using the saved refresh token

IMPORTANT:
  - GOOGLE_REDIRECT_URI must exactly match what is registered in Google Cloud Console.
  - On Render, set RENDER_SERVICE_URL to your full service URL.
    Example: https://airos-engine.onrender.com
  - The redirect URI will be: https://airos-engine.onrender.com/auth/callback
"""

import json
import urllib.parse
from pathlib import Path
from typing import Optional

import httpx

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    BLOGGER_BLOG_ID,
    TOKEN_FILE,
)
from logger import get_logger

logger = get_logger("blogger")

SCOPES = "https://www.googleapis.com/auth/blogger"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
BLOGGER_API = "https://www.googleapis.com/blogger/v3"


# ---------------------------------------------------------------------------
# Token storage
# Tokens are saved to TOKEN_FILE (/tmp/.acie_tokens.json on Render).
# Never committed to GitHub — lives only on the Render instance.
# ---------------------------------------------------------------------------

def _load_tokens() -> Optional[dict]:
    path = Path(TOKEN_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_tokens(tokens: dict):
    Path(TOKEN_FILE).write_text(json.dumps(tokens, indent=2))
    logger.info("OAuth2 tokens saved.")


def _refresh_access_token(refresh_token: str) -> Optional[str]:
    """Exchange a refresh token for a new short-lived access token."""
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(TOKEN_URL, data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            data = resp.json()

        access_token = data.get("access_token")
        tokens = _load_tokens() or {}
        tokens["access_token"] = access_token
        if "refresh_token" in data:
            tokens["refresh_token"] = data["refresh_token"]
        _save_tokens(tokens)

        logger.info("Access token refreshed successfully.")
        return access_token

    except Exception as e:
        logger.error(f"Token refresh failed | {e}")
        return None


def get_access_token() -> Optional[str]:
    """Return a valid access token, refreshing automatically if needed."""
    tokens = _load_tokens()
    if not tokens:
        logger.warning("No OAuth2 tokens on file. Complete the auth flow at /auth/url.")
        return None

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        logger.warning("Refresh token missing. Re-authorize at /auth/url.")
        return None

    return _refresh_access_token(refresh_token)


# ---------------------------------------------------------------------------
# OAuth2 flow — called once during initial Render setup
# ---------------------------------------------------------------------------

def get_auth_url() -> str:
    """
    Build the Google OAuth2 consent URL.
    The redirect URI must match exactly what is registered in Google Cloud Console.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    logger.info(f"Auth URL generated | redirect_uri={GOOGLE_REDIRECT_URI}")
    return url


def exchange_code(code: str) -> bool:
    """
    Exchange the authorization code Google sends to /auth/callback.
    Saves both access token and refresh token to TOKEN_FILE.
    Returns True on success.
    """
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(TOKEN_URL, data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "code": code,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            tokens = resp.json()

        if "refresh_token" not in tokens:
            logger.error("No refresh token in response. Ensure 'access_type=offline' and 'prompt=consent' in auth URL.")
            return False

        _save_tokens(tokens)
        logger.info("OAuth2 authorization complete. Tokens saved.")
        return True

    except Exception as e:
        logger.error(f"Code exchange failed | {e}")
        return False


def is_authenticated() -> bool:
    """Return True if a valid refresh token is on file."""
    tokens = _load_tokens()
    return bool(tokens and tokens.get("refresh_token"))


# ---------------------------------------------------------------------------
# Blogger API
# ---------------------------------------------------------------------------

def publish_post(
    title: str,
    body_html: str,
    labels: Optional[list] = None,
    is_draft: bool = False,
) -> Optional[dict]:
    """
    Publish an article to Blogger.

    Args:
        title:     Article headline (used as Blogger post title).
        body_html: Full HTML body of the article.
        labels:    Tag/category list (max 5 recommended).
        is_draft:  If True, saves as draft instead of going live.

    Returns:
        dict with {post_id, url} on success, None on failure.
    """
    access_token = get_access_token()
    if not access_token:
        logger.error("Cannot publish — no access token. Complete OAuth2 setup first.")
        return None

    if not BLOGGER_BLOG_ID:
        logger.error("BLOGGER_BLOG_ID is not set in Render environment variables.")
        return None

    payload = {
        "title": title,
        "content": body_html,
        "labels": labels or [],
    }

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{BLOGGER_API}/blogs/{BLOGGER_BLOG_ID}/posts/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                params={"isDraft": str(is_draft).lower()},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        post_id = data.get("id", "")
        post_url = data.get("url", "")

        logger.info(f"Published | post_id={post_id} | url={post_url}")
        return {"post_id": post_id, "url": post_url}

    except httpx.HTTPStatusError as e:
        logger.error(f"Blogger API error | status={e.response.status_code} | body={e.response.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"Blogger publish failed | {e}")
        return None


def update_post(post_id: str, title: str, body_html: str) -> bool:
    """Update an existing Blogger post by ID."""
    access_token = get_access_token()
    if not access_token:
        return False

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.put(
                f"{BLOGGER_API}/blogs/{BLOGGER_BLOG_ID}/posts/{post_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"title": title, "content": body_html},
            )
            resp.raise_for_status()

        logger.info(f"Post updated | id={post_id}")
        return True

    except Exception as e:
        logger.error(f"Post update failed | id={post_id} | {e}")
        return False
