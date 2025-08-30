import os
import time
import webbrowser
import threading
from datetime import datetime
from pathlib import Path

from tts import speak, set_voice, list_voices, stop_speaking, pause_speaking, resume_speaking
from listener import listen
from music import MusicPlayer
from news import get_headlines
from config import MUSIC_FOLDER
from ai import ask_ai_stream  # streaming Ollama client

# ------------------------ Settings ------------------------
WAKE_WORDS = {"prajwol", "prajwal", "hey prajwal", "hey prajwol","siri"}
QUESTION_TIMEOUT_SECS = 10
NOTES_FILE = "notes.txt"
# ----------------------------------------------------------


# ---------- Desktop apps you want to launch by name ----------
APP_PATHS = {
    "notepad": r"C:\Windows\System32\notepad.exe",
    "calculator": r"C:\Windows\System32\calc.exe",
    # Adjust this VS Code path if yours is different:
    "vs code": r"C:\Users\prajw\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "visual studio code": r"C:\Users\prajw\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "code": r"C:\Users\prajw\AppData\Local\Programs\Microsoft VS Code\Code.exe",
}
APP_ALIASES = {
    "vscode": "vs code",
    "vs code": "vs code",
    "visual studio code": "visual studio code",
    "code": "vs code",
}
APP_KEYWORDS = {"open app", "launch", "start", "run"}


def normalize_app_name(name: str) -> str:
    n = (name or "").strip().lower()
    return APP_ALIASES.get(n, n)


def open_app(name: str) -> bool:
    key = normalize_app_name(name)
    path = APP_PATHS.get(key)
    if path and Path(path).exists():
        os.startfile(path)  # nosec - local desktop automation
        return True
    return False
# -------------------------------------------------------------


# ----------------------------- Notes -----------------------------
def add_note(text: str):
    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(text.strip() + "\n")
# -----------------------------------------------------------------


# ----------------------------- Timers ----------------------------
def set_timer(seconds: int):
    def ding():
        speak("Time's up.")
    t = threading.Timer(seconds, ding)
    t.daemon = True
    t.start()
# -----------------------------------------------------------------


# Optional jokes
try:
    import pyjokes
except Exception:
    pyjokes = None


def nrm(x: str) -> str:
    return (x or "").lower().strip()


def say(msg: str):
    print(f"[say] {msg}")
    speak(msg)


# -------------- Natural “thinking” (single cue) ---------------
def quick_thinking_cue():
    """Say one natural cue instead of repeating fillers."""
    speak("Hmm… let me think.", chunked=False)
# --------------------------------------------------------------


def say_help():
    say(
        "You can say: open YouTube, search Google for cats, "
        "directions to Kathmandu, play music, pause, resume, next, previous, stop music, "
        "news or news about technology, what's the time, what's the date, "
        "change voice to female or male, list voices, tell me a joke, "
        "open app notepad, launch vscode, take a note buy milk, set a timer for two minutes, "
        "stop talking, wait, resume speaking, go to sleep, or exit."
    )


def open_site_or_search(text: str):
    rest = nrm(text).split("open", 1)[1].strip() if text.lower().startswith("open ") else ""
    if not rest:
        say("What should I open?")
        return
    # domain-ish? open directly; otherwise search
    if "." in rest and " " not in rest:
        url = rest if rest.startswith(("http://", "https://")) else "https://" + rest
        say(f"Opening {rest}")
        webbrowser.open(url)
    else:
        say("Okay, searching.")
        webbrowser.open(f"https://www.google.com/search?q={rest}")


def handle_question(text: str, player: MusicPlayer) -> str:
    """
    Handle commands while ACTIVE.
    Return one of: "continue", "sleep", "exit"
    """
    cmd = nrm(text)
    print(f"[handle] {cmd!r}")

    # -------- talk control --------
    if cmd.startswith("say "):
        say(cmd[4:].strip());                     return "continue"
    if cmd in {"stop talking", "stop speaking", "be quiet", "shut up"}:
        stop_speaking();                          return "continue"
    if cmd in {"wait", "pause speaking"}:
        pause_speaking(); say("Okay, I will wait."); return "continue"
    if cmd in {"resume speaking", "continue speaking"}:
        resume_speaking(); say("Resuming.");      return "continue"

    # -------- exit / sleep --------
    if cmd in {"quit", "exit", "close", "shutdown"}:
        say("Goodbye!");                          return "exit"
    if cmd in {"go to sleep", "sleep", "stop listening"}:
        say("Going to sleep. Say prajwal to wake me."); return "sleep"

    # -------- help / time / date --------
    if cmd in {"help", "what can you do", "commands"}:
        say_help();                                return "continue"
    if "time" in cmd:
        say(f"The time is {datetime.now().strftime('%I:%M %p')}");   return "continue"
    if "date" in cmd or "day" in cmd:
        say(f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"); return "continue"

    # -------- voice control --------
    if cmd.startswith("change voice to "):
        target = cmd.replace("change voice to", "", 1).strip()
        chosen = None
        if target in {"female", "girl", "woman"}:
            for pick in ("zira", "hazel", "aria", "jenny", "sara"):
                chosen = set_voice(pick)
                if chosen: break
        elif target in {"male", "man", "boy"}:
            for pick in ("david", "george", "guy", "ryan"):
                chosen = set_voice(pick)
                if chosen: break
        else:
            chosen = set_voice(target)
        if chosen:
            say(f"Okay, I’ll use the {chosen} voice.")
        else:
            say("I couldn’t find that voice. I printed your installed voices in the terminal.")
            print("\n=== Installed voices ===")
            for v in list_voices(): print(v)
        return "continue"

    if cmd in {"list voices", "show voices"}:
        print("\n=== Installed voices ===")
        for v in list_voices(): print(v)
        say("I listed your voices in the terminal.");                 return "continue"

    # -------- LOCAL APPS (priority) --------
    for kw in APP_KEYWORDS:
        if cmd.startswith(kw + " "):
            app = cmd[len(kw):].strip()
            if open_app(app):
                say(f"Opening {normalize_app_name(app)}.")
            else:
                say("I couldn't find that app. You can add it to my list.")
            return "continue"

    # Also catch "open vs code" (without the word 'app')
    for app_key in APP_PATHS.keys():
        if cmd.startswith("open " + app_key):
            if open_app(app_key):
                say(f"Opening {app_key}.")
            else:
                say("I couldn't find that app. You can add it to my list.")
            return "continue"

    # -------- web / maps (tight matches so we don’t collide with 'who is ...') --------
    if cmd.startswith("open website "):
        query = cmd.replace("open website", "", 1).strip()
        if "." in query and " " not in query:
            url = query if query.startswith(("http://", "https://")) else "https://" + query
            say(f"Opening {query}")
            webbrowser.open(url)
        else:
            say("Okay, searching.")
            webbrowser.open(f"https://www.google.com/search?q={query}")
        return "continue"

    if cmd.startswith("open "):
        open_site_or_search(text);                                     return "continue"

    if cmd.startswith("directions to "):
        place = cmd.replace("directions to", "", 1).strip()
        if place:
            say(f"Showing directions to {place}")
            webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={place}")
        else:
            say("Where do you want to go?")
        return "continue"

    if cmd.startswith("navigate to "):
        place = cmd.replace("navigate to", "", 1).strip()
        if place:
            say(f"Navigating to {place}")
            webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={place}")
        else:
            say("Where do you want to go?")
        return "continue"

    if "open youtube" in cmd:
        say("Opening YouTube"); webbrowser.open("https://www.youtube.com"); return "continue"

    if cmd.startswith("google ") or "search google for" in cmd:
        query = cmd.split("for", 1)[1].strip() if "for" in cmd else cmd.replace("google", "", 1).strip()
        if query:
            say("Okay, searching."); webbrowser.open(f"https://www.google.com/search?q={query}")
        else:
            say("What should I search for?")
        return "continue"

    # -------- music --------
    if "play music" in cmd or "play song" in cmd:
        try:
            title = player.play(); say(f"Playing {title}")
        except Exception:
            say("Your music folder seems empty.")
        return "continue"
    if cmd == "pause" or "pause music" in cmd:
        player.pause(); say("Paused");           return "continue"
    if cmd == "resume" or "resume music" in cmd:
        player.resume(); say("Resumed");         return "continue"
    if "next song" in cmd or cmd == "next":
        say(f"Next track: {player.next()}");     return "continue"
    if "previous" in cmd or "back" in cmd:
        say(f"Previous track: {player.prev()}"); return "continue"
    if "stop music" in cmd or "stop song" in cmd:
        player.stop(); say("Stopped");           return "continue"

    # -------- utilities: notes / timers --------
    if cmd.startswith("take a note ") or cmd.startswith("note "):
        # everything after the first space is the note
        parts = text.split(" ", 2)
        content = parts[2] if len(parts) >= 3 else ""
        if content.strip():
            add_note(content)
            say("Saved.")
        else:
            say("What should I note?")
        return "continue"

    if cmd.startswith("set a timer for "):
        import re
        m = re.search(r"(\d+)\s*(second|seconds|minute|minutes|min|mins)", cmd)
        if m:
            n = int(m.group(1))
            secs = n * 60 if "min" in m.group(2) else n
            set_timer(secs)
            say(f"Timer set for {n} {'minute' if secs>=60 else 'second'}.")
        else:
            say("Tell me how long.")
        return "continue"

    # -------- news (keep it short: only first headline) --------
    if cmd.startswith("news about "):
        topic = cmd.replace("news about", "", 1).strip()
        say(f"Checking headlines about {topic}.")
        try:
            headlines = get_headlines(topic=topic, limit=3)
        except Exception as e:
            print("[news error]", repr(e))
            say("I couldn't fetch the news right now.")
            return "continue"
        if headlines:
            speak(headlines[0])
        else:
            say(f"I couldn't find headlines about {topic}.")
        return "continue"

    if cmd == "news" or "headlines" in cmd:
        say("Fetching top headlines.")
        try:
            headlines = get_headlines(limit=3)
        except Exception as e:
            print("[news error]", repr(e))
            say("I couldn't fetch the news right now.")
            return "continue"
        if headlines:
            speak(headlines[0])
        else:
            say("No headlines found.")
        return "continue"

    # -------- jokes --------
    if "joke" in cmd or "make me laugh" in cmd:
        if pyjokes:
            try:
                say(pyjokes.get_joke())
            except Exception as e:
                print("[joke error]", repr(e)); say("I had trouble telling a joke.")
        else:
            say("I can tell jokes if you install the pyjokes package.")
        return "continue"

    # -------- default fallback → local AI (ONE short sentence) --------
    quick_thinking_cue()

    sentence = ""
    punct = {".", "!", "?", "…"}
    for chunk in ask_ai_stream(
        cmd,
        system="You are a helpful voice assistant. Reply in ONE short sentence.",
        max_tokens=60,
    ):
        sentence += chunk
        if any(sentence.strip().endswith(p) for p in punct) or len(sentence) > 140:
            speak(sentence.strip())
            break
    return "continue"


def main():
    say("I'm in standby. Say 'prajwal' to wake me.")
    player = MusicPlayer(MUSIC_FOLDER)
    player.scan()

    active = False
    while True:
        if not active:
            # Short, strict wake capture
            heard = listen(timeout=8, phrase_time_limit=3, language="en-US", debug=False)
            if not heard:
                continue
            txt = nrm(heard)
            if any(ww in txt for ww in WAKE_WORDS):
                active = True
                # NOTE: no "I'm listening" TTS here

                # Let the first command be long and natural:
                #   - no phrase_time_limit (unlimited)
                #   - stop when you pause ~1.8s (set in listener.py or override here)
                first_cmd = listen(
                    timeout=20,                 # wait up to 20s for you to start
                    phrase_time_limit=None,     # unlimited, ends on pause
                    language="en-US",
                    debug=False,
                    pause_threshold=1.8,        # override if you want
                    non_speaking_duration=0.3
                )
                if first_cmd:
                    state = handle_question(first_cmd, player)
                    if state == "sleep":
                        active = False
                        # no extra chatter
                    elif state == "exit":
                        break
            continue

        # ACTIVE: keep taking long commands until you say "go to sleep"/"exit"
        cmd_text = listen(
            timeout=30,                 # wait up to 30s for you to start talking
            phrase_time_limit=None,     # unlimited speech; ends when you pause ~1.8s
            language="en-US",
            debug=False,
            pause_threshold=1.8,
            non_speaking_duration=0.3
        )
        if not cmd_text:
            # You didn't speak; stay active, don't re-wake
            continue

        state = handle_question(cmd_text, player)
        if state == "sleep":
            active = False
        elif state == "exit":
            break

    # (The following code is unreachable and has been removed to fix syntax errors.)

if __name__ == "__main__":
    main()
