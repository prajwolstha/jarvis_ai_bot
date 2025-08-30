# listener_whisper.py
from __future__ import annotations
from typing import Optional
import tempfile
import os

import speech_recognition as sr

# --------- Mic tuning (reuse your working device) ----------
DEFAULT_MIC_INDEX: Optional[int] = None   # set to your working index if needed
CALIBRATION_TIME = 0.6
PAUSE_THRESHOLD = 0.5
PHRASE_THRESHOLD = 0.2
NON_SPEAKING_DURATION = 0.15
# -----------------------------------------------------------

# Try to import faster-whisper first; fall back to openai-whisper
_USE_FASTER = False
try:
    from faster_whisper import WhisperModel
    _USE_FASTER = True
except Exception:
    try:
        import whisper  # type: ignore
        _USE_FASTER = False
    except Exception:
        whisper = None  # type: ignore
        _USE_FASTER = False

# Lazy-loaded models
_faster_model = None
_whisper_model = None

def _get_faster_model(device: str = "cpu", compute_type: str = "auto"):
    global _faster_model
    if _faster_model is None:
        # choose model size: "small" is a good balance; use "base" for weaker CPUs
        _faster_model = WhisperModel("small", device=device, compute_type=compute_type)
    return _faster_model

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper  # type: ignore
        # choose model size: "small" is a good start; "base" is lighter
        _whisper_model = whisper.load_model("small")
    return _whisper_model

def _new_recognizer() -> sr.Recognizer:
    r = sr.Recognizer()
    r.pause_threshold = PAUSE_THRESHOLD
    r.phrase_threshold = PHRASE_THRESHOLD
    r.non_speaking_duration = NON_SPEAKING_DURATION
    return r

def listen(
    timeout: float | None = None,
    phrase_time_limit: float | None = None,
    language: str = "en",              # IMPORTANT: Whisper expects "en", "ne", etc. (no region)
    mic_index: int | None = DEFAULT_MIC_INDEX,
    debug: bool = False,
) -> Optional[str]:
    """
    Record from mic using speech_recognition, then transcribe locally with Whisper.
    Returns text or None.
    """
    # 1) Capture audio from mic (same as your current flow)
    r = _new_recognizer()
    try:
        mic = sr.Microphone(device_index=mic_index)
    except Exception as e:
        if debug: print(f"[whisper-listener] Could not open microphone (index={mic_index}): {e!r}")
        return None

    try:
        with mic as source:
            try:
                r.adjust_for_ambient_noise(source, duration=CALIBRATION_TIME)
                if debug: print(f"[whisper-listener] Calibrated. energy_threshold={r.energy_threshold:.1f}")
            except Exception as e:
                if debug: print(f"[whisper-listener] Ambient noise adjust failed: {e!r}")
                return None

            try:
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                if debug: print("[whisper-listener] Timeout waiting for speech start.")
                return None
            except Exception as e:
                if debug: print(f"[whisper-listener] Error during listen(): {e!r}")
                return None
    except Exception as e:
        if debug: print(f"[whisper-listener] mic open/close error: {e!r}")
        return None

    # 2) Dump to a temp WAV for Whisper
    wav_bytes = audio.get_wav_data()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        tmp_path = f.name
        f.write(wav_bytes)

    # 3) Transcribe with Whisper (faster-whisper preferred)
    try:
        if _USE_FASTER:
            model = _get_faster_model(device="cpu", compute_type="auto")  # set device="cuda" if you have Nvidia GPU
            # VAD filtering helps on noisy mics
            segments, info = model.transcribe(tmp_path, language=language, vad_filter=True, beam_size=1)
            text = "".join(seg.text for seg in segments).strip()
            if debug: print(f"[whisper-listener] ({language}) → {text!r}")
            return text or None
        else:
            if 'whisper' not in globals() or whisper is None:
                if debug: print("[whisper-listener] Neither faster-whisper nor openai-whisper available.")
                return None
            model = _get_whisper_model()
            # original whisper uses language codes like "ne", "en"
            result = model.transcribe(tmp_path, language=language, fp16=False)
            text = (result.get("text") or "").strip()
            if debug: print(f"[whisper-listener] ({language}) → {text!r}")
            return text or None
    except Exception as e:
        if debug: print(f"[whisper-listener] Transcription error: {e!r}")
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
