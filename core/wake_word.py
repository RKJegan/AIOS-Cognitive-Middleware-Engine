"""openWakeWord listener. Fires on_wake() once per detection then expects the caller
to pause/resume it (see main.py) so it doesn't re-trigger mid-command."""
from core.logger import get_logger
from config.settings import Settings

log = get_logger()


class WakeWordListener:
    def __init__(self, on_wake, settings=None):
        self.on_wake = on_wake
        self.settings = settings or Settings.load()
        self.wake_word = self.settings.wake_word
        self._running = False
        self._paused = False
        self.available = True
        try:
            from pathlib import Path
            from openwakeword.model import Model
            target = self.settings.wake_word_model_path or self.wake_word
            self.model = Model(wakeword_models=[target], inference_framework="onnx")
            self.wake_word = Path(target).stem if self.settings.wake_word_model_path else self.wake_word
        except Exception as e:
            log.warning(f"Wake word engine unavailable ({e}); use the hotkey or typed commands instead")
            self.available = False
            self.model = None

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def start(self):
        if not self.available:
            return
        import pyaudio
        import numpy as np
        self._running = True
        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1280)
        log.info(f"Wake word listener started: '{self.wake_word}'")
        while self._running:
            chunk = stream.read(1280, exception_on_overflow=False)
            if self._paused:
                continue
            audio = np.frombuffer(chunk, dtype=np.int16)
            score = self.model.predict(audio).get(self.wake_word, 0)
            if score > self.settings.wake_threshold:
                log.info(f"Wake word detected (score={score:.2f})")
                self.model.reset()
                self.on_wake()

    def stop(self):
        self._running = False
