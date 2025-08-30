# tts.py — Windows SAPI-only TTS with stop/wait/resume
import threading
import time
import re
from typing import List, Optional

try:
    import win32com.client  # requires pywin32
except Exception as e:
    raise RuntimeError(
        "win32com is missing. Install pywin32:\n  pip install pywin32"
    ) from e

# SAPI engine (synchronous)
_sapi = win32com.client.Dispatch("SAPI.SpVoice")

_STOP = threading.Event()
_PAUSE = threading.Event()
_LOCK = threading.RLock()  # serialize voice access


_current_lang = "en-US"   # default

def set_lang(lang_code: str):
    """Set the current language for speech output (e.g. 'en-US' or 'ne-NP')."""
    global _current_lang
    _current_lang = lang_code


def list_voices() -> List[str]:
    """Return available voice descriptions."""
    toks = _sapi.GetVoices()
    out = []
    for i in range(toks.Count):
        v = toks.Item(i).GetDescription()
        out.append(f"id={i} | name={v}")
    return out


def set_voice(name_contains: Optional[str] = None) -> Optional[str]:
    """Select voice whose description contains substring (case-insensitive)."""
    if not name_contains:
        return None
    target = name_contains.lower()
    toks = _sapi.GetVoices()
    for i in range(toks.Count):
        desc = toks.Item(i).GetDescription()
        if target in desc.lower():
            _sapi.Voice = toks.Item(i)
            return desc
    return None


def stop_speaking():
    """Stop after the current chunk—SAPI can’t interrupt a running Speak, so we chunk small."""
    _STOP.set()
    # no direct hard-stop API; we finish current chunk and then stop


def pause_speaking():
    """Pause: stop after current chunk and wait until resume."""
    _PAUSE.set()
    _STOP.set()  # forces current chunk to end, then loop will wait


def resume_speaking():
    """Resume: allow speak() to continue with remaining chunks."""
    _STOP.clear()
    _PAUSE.clear()


def _chunks(text: str):
    """Split into short chunks (sentences) so stop/pause take effect quickly."""
    parts = re.split(r"([.!?])", text)
    merged = []
    cur = ""
    for i in range(0, len(parts), 2):
        s = parts[i].strip()
        p = parts[i + 1] if i + 1 < len(parts) else ""
        piece = (s + p).strip()
        if not piece:
            continue
        if len(cur) + len(piece) < 220:
            cur = (cur + " " + piece).strip()
        else:
            if cur:
                merged.append(cur)
            cur = piece
    if cur:
        merged.append(cur)
    return merged or [text.strip()]


def speak(text: str, chunked: bool = True):
    """Speak text using SAPI. If chunked, split to short chunks."""
    if not text:
        return
    parts = _chunks(text) if chunked else [text]
    _STOP.clear()
    for p in parts:
        # wait if paused
        while _PAUSE.is_set():
            time.sleep(0.05)
        if _STOP.is_set():
            break
        with _LOCK:
            # 0 = SVSFlagsAsync off (sync), but we keep chunks short so “stop/wait” are responsive
            _sapi.Speak(p)
        if _STOP.is_set():
            break
