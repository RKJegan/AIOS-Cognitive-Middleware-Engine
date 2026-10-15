"""pyttsx3 TTS. Degrades silently (console-only) if no TTS engine is available."""
import threading
from core.logger import get_logger

log = get_logger()
_engine = None
_lock = threading.Lock()
_available = True


def _get_engine():
    global _engine, _available
    if _engine is None and _available:
        try:
            import pyttsx3
            _engine = pyttsx3.init()
            _engine.setProperty("rate", 175)
        except Exception as e:
            log.warning(f"TTS unavailable: {e}")
            _available = False
    return _engine


def speak(text):
    if not _available or not text:
        return

    def _run():
        with _lock:
            engine = _get_engine()
            if not engine:
                return
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                log.warning(f"TTS failed: {e}")

    threading.Thread(target=_run, daemon=True).start()
