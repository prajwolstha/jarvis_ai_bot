import win32com.client

speaker = win32com.client.Dispatch("SAPI.SpVoice")
speaker.Speak("If you hear this, Windows SAPI is working.")
