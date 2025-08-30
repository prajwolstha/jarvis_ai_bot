# ai.py — streaming Ollama client for fast first audio
from __future__ import annotations
import requests
from typing import Iterator, Optional
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

def ask_ai(prompt: str, system: Optional[str] = None, max_tokens: int = 160) -> str:
    """Non-streaming (kept for compatibility)."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(
        url,
        json={
            "model": OLLAMA_MODEL,
            "messages": msgs,
            "stream": False,
            "options": {
                "temperature": 0.6,
                "num_predict": max_tokens,   # cap length
                "num_ctx": 2048,            # enough context but not huge
                "num_thread": 0,            # let Ollama pick CPU threads
                "keep_alive": "10m",        # keep model warm
            },
        },
        timeout=120,
    )
    if r.status_code != 200:
        return f"Local AI error HTTP {r.status_code}: {r.text[:200]}"
    data = r.json()
    return data.get("message", {}).get("content", "").strip()

def ask_ai_stream(prompt: str, system: Optional[str] = None, max_tokens: int = 160) -> Iterator[str]:
    """
    Streaming generator. Yields small text chunks so the caller can speak them immediately.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    with requests.post(
        url,
        json={
            "model": OLLAMA_MODEL,
            "messages": msgs,
            "stream": True,
            "options": {
                "temperature": 0.6,
                "num_predict": max_tokens,
                "num_ctx": 2048,
                "num_thread": 0,
                "keep_alive": "10m",
            },
        },
        stream=True,
        timeout=120,
    ) as r:
        if r.status_code != 200:
            yield f"[AI error {r.status_code}] {r.text[:200]}"
            return
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            # each line is a JSON object like {"message":{"role":"assistant","content":"token"},"done":false}
            try:
                import json
                obj = json.loads(line)
                if "message" in obj and "content" in obj["message"]:
                    yield obj["message"]["content"]
                if obj.get("done"):
                    break
            except Exception:
                # ignore parse glitches
                continue
