# nepali_support.py
from tts import set_lang

CURRENT_LANG = "en-US"   # default

# Nepali → English command dictionary
NE_TO_EN = [
    ("समाचार", "news"),
    ("खोल", "open"),
    ("युट्युब", "youtube"),
    ("गुगलमा खोज", "search google for"),
    ("समय", "time"),
    ("मिति", "date"),
    ("संगीत", "music"),
    ("संगीत बजाउ", "play music"),
    ("रोक", "pause"),
    ("चालु गर", "resume"),
    ("अगाडि", "next"),
    ("पछाडि", "previous"),
    ("ठट्टा", "joke"),
    ("नोट लेख", "take a note "),
    ("एप", "app"),
    ("खोज", "search"),
    ("मार्गनिर्देशन", "directions to "),
    ("सुत", "go to sleep"),
]

def is_nepali_text(s: str) -> bool:
    """Check if input has Devanagari characters."""
    return any("\u0900" <= ch <= "\u097F" for ch in s)

def normalize_nepali_command(txt: str) -> str:
    """Map Nepali words to English commands."""
    t = txt
    for ne, en in NE_TO_EN:
        t = t.replace(ne, en)
    return t

def switch_language(txt: str) -> str:
    """
    Switch global CURRENT_LANG depending on the detected language.
    Returns the normalized text (ready to be passed to handle_question).
    """
    global CURRENT_LANG
    if is_nepali_text(txt):
        CURRENT_LANG = "ne-NP"
        set_lang("ne-NP")
        return normalize_nepali_command(txt)
    else:
        CURRENT_LANG = "en-US"
        set_lang("en-US")
        return txt
