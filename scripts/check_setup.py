"""Run: python -m scripts.check_setup   -- reports what's importable/working on THIS machine."""
import importlib
import shutil

CHECKS = [
    ("loguru", "logging"), ("requests", "Ollama HTTP client"), ("psutil", "process/system info"),
    ("pygetwindow", "window close by title"), ("playwright", "automation browser"),
    ("pyttsx3", "text-to-speech"), ("openwakeword", "wake word"), ("pyaudio", "microphone input"),
    ("keyboard", "global hotkeys"), ("whisper", "speech-to-text"), ("sounddevice", "mic recording"),
    ("pycaw", "volume control"), ("comtypes", "volume control (dep)"), ("wmi", "brightness control"),
    ("plyer", "desktop notifications"), ("apscheduler", "workflow scheduling"), ("pyperclip", "clipboard"),
    ("pytesseract", "OCR"), ("PIL", "screenshots"), ("screeninfo", "multi-monitor"),
    ("PyPDF2", "PDF reading"), ("docx", "Word document reading"), ("git", "git operations (gitpython)"),
    ("keyring", "credential storage"), ("tkinter", "narration HUD overlay"),
]


def main():
    print("Package check:")
    for module, purpose in CHECKS:
        try:
            importlib.import_module(module)
            print(f"  OK    {module:14s} ({purpose})")
        except Exception as e:
            print(f"  MISS  {module:14s} ({purpose}) - {e}")

    print("\nExternal tools:")
    print(f"  {'OK   ' if shutil.which('ollama') else 'MISS '} ollama on PATH")
    print(f"  {'OK   ' if shutil.which('git') else 'MISS '} git on PATH")
    print(f"  {'OK   ' if shutil.which('tesseract') else 'MISS '} tesseract on PATH (set tesseract_cmd in settings if not)")
    print(f"  {'OK   ' if shutil.which('claude') else 'MISS '} claude (Claude Code CLI) on PATH")


if __name__ == "__main__":
    main()
