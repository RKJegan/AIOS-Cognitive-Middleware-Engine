"""Thin wrapper kept for `python -m ai.speech_to_text` and older imports."""
from ai.stt_engine import STTEngine, record_and_transcribe  # noqa: F401

if __name__ == "__main__":
    engine = STTEngine()
    print("Speak one command (it stops by itself when you pause)...")
    audio = engine.listen()
    print("Heard nothing." if audio is None else f"You said: {engine.transcribe(audio)}")
