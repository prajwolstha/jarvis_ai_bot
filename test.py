from tts import list_voices, set_voice, speak

print("\n".join(list_voices()))
set_voice("zira")    # or "david"/"hazel" depending on what you saw printed
speak("This is a SAPI voice test. If you hear me, your T T S is fixed.")
