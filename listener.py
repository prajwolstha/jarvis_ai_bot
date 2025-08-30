# listener.py
from __future__ import annotations
import time
from typing import Optional
import speech_recognition as sr

# Default mic index; set to None to use system default
DEFAULT_MIC_INDEX: Optional[int] = None

# Ambient noise calibration (seconds)
CALIBRATION_TIME = 0.5

# VAD / recognition tuning
PAUSE_THRESHOLD = 0.8      # seconds of silence that stops listening
PHRASE_THRESHOLD = 0.3     # minimum speech length considered valid
NON_SPEAKING_DURATION = 0.2


def list_microphones() -> list[str]:
    """
    Returns a list of available microphone names.
    Use the index from this list as DEFAULT_MIC_INDEX if you want a specific device.
    """
    return sr.Microphone.list_microphone_names()


# listener.py
# ...
# Make pauses feel natural (increase these a bit)
PAUSE_THRESHOLD = 1.8         # seconds of silence to end phrase (was 0.8)
PHRASE_THRESHOLD = 0.15       # min speech length (short)
NON_SPEAKING_DURATION = 0.3   # pre/post roll

def listen(timeout=None, phrase_time_limit=None, language="en-US",
           mic_index: int | None = DEFAULT_MIC_INDEX, debug: bool = False,
           # NEW: optional VAD overrides per call
           pause_threshold: float | None = None,
           non_speaking_duration: float | None = None,
           phrase_threshold: float | None = None) -> Optional[str]:
    r = sr.Recognizer()

    # Apply defaults, allow per-call overrides
    r.pause_threshold = pause_threshold if pause_threshold is not None else PAUSE_THRESHOLD
    r.non_speaking_duration = non_speaking_duration if non_speaking_duration is not None else NON_SPEAKING_DURATION
    r.phrase_threshold = phrase_threshold if phrase_threshold is not None else PHRASE_THRESHOLD
    # ...

    # Pick the microphone
    try:
        mic = sr.Microphone(device_index=mic_index)
    except Exception as e:
        if debug:
            print(f"[listener] Could not open microphone (index={mic_index}): {e!r}")
        return None

    with mic as source:
        # Small ambient noise calibration
        try:
            r.adjust_for_ambient_noise(source, duration=CALIBRATION_TIME)
            if debug:
                print(f"[listener] Calibrated. energy_threshold={r.energy_threshold:.1f}")
        except Exception as e:
            if debug:
                print(f"[listener] adjust_for_ambient_noise failed: {e!r}")

        # Listen for speech
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            if debug:
                print("[listener] Timeout waiting for speech start.")
            return None
        except Exception as e:
            if debug:
                print(f"[listener] Error during listen(): {e!r}")
            return None

    # Recognize
    try:
        text = r.recognize_google(audio, language=language)
        if debug:
            print(f"[listener] Heard ({language}): {text}")
        return text
    except sr.UnknownValueError:
        if debug:
            print("[listener] Speech unintelligible.")
        return None
    except sr.RequestError as e:
        if debug:
            print(f"[listener] Recognition service error: {e!r}")
        return None
    except Exception as e:
        if debug:
            print(f"[listener] Unexpected recognition error: {e!r}")
        return None


# Convenience: quick CLI test
if __name__ == "__main__":
    print("Available mics:", list_microphones())
    print("Say something (Ctrl+C to quit)…")
    try:
        while True:
            txt = listen(timeout=5, phrase_time_limit=8, language="en-US", debug=True)
            print("->", txt)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nBye!")
