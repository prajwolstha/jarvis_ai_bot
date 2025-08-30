# news.py
from __future__ import annotations
import requests
from typing import List
from config import NEWS_API_KEY

_BASE = "https://newsapi.org/v2/top-headlines"

def get_headlines(topic: str | None = None, country: str = "us", limit: int = 5) -> List[str]:
    if not NEWS_API_KEY or NEWS_API_KEY.strip() in {"", "YOUR_NEWSAPI_KEY_HERE"}:
        raise RuntimeError("Missing NEWS_API_KEY in config.py")

    params = {"apiKey": NEWS_API_KEY, "country": country, "pageSize": max(1, min(limit, 20))}
    if topic:
        params["q"] = topic

    try:
        r = requests.get(_BASE, params=params, timeout=12)
    except Exception as e:
        raise RuntimeError(f"Network error calling NewsAPI: {e!r}")
    if r.status_code != 200:
        raise RuntimeError(f"NewsAPI HTTP {r.status_code}: {r.text[:400]}")
    data = r.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI error: {data}")
    return [a.get("title") for a in data.get("articles", []) if a.get("title")]
