"""Speech-to-text: pluggable backends, voice-activity endpointing, hallucination filtering.
Backends:  faster_whisper (CPU/GPU, default)  |  nemo_http (NVIDIA NeMo model served by
scripts/nemo_stt_server.py, runs in its own Python 3.12 env)  |  auto (nemo if reachable)."""
import re
import time
from collections import deque
import numpy as np
from core.logger import get_logger
from config.settings import Settings

log = get_logger()
RATE = 16000

HALLUCINATIONS = {
    "you", "thank you", "thanks", "thanks for watching", "bye", "so", "ah", "oh", "uh", "um", "hmm",
    "okay", "ok", "yeah", "yes", "the", "a", "and", "i", "huh", "mm", "mhm",
}


def clean_transcript(text):
    t = re.sub(r"\s+", " ", (text or "")).strip()
    return t.strip(" \t\r\n-–—_")


def is_junk(text):
    t = clean_transcript(text)
    letters = re.sub(r"[^a-zA-Z]", "", t)
    if len(letters) < 3:
        return True
    norm = re.sub(r"[^a-z ]", "", t.lower()).strip()
    if norm in HALLUCINATIONS:
        return True
    words = norm.split()
    if len(words) >= 3 and len(set(words)) == 1:        # "gunsel gunsel gunsel"
        return True
    if re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", t):   # CJK in an English session
        return True
    return False


class Endpointer:
    """Energy-based utterance detector. Feed 50 ms float32 blocks; it says when speech started/ended."""

    def __init__(self, rate=RATE, block_seconds=0.05, silence_seconds=1.0, start_timeout=6.0,
                 max_seconds=15.0, min_speech_seconds=0.25, calibration_blocks=6, preroll_blocks=6,
                 floor=0.012, factor=3.0):
        self.block_seconds = block_seconds
        self.silence_blocks_needed = max(1, int(silence_seconds / block_seconds))
        self.start_timeout, self.max_seconds = start_timeout, max_seconds
        self.min_speech_blocks = max(1, int(min_speech_seconds / block_seconds))
        self.calibration_blocks, self.floor, self.factor = calibration_blocks, floor, factor
        self.preroll = deque(maxlen=preroll_blocks)
        self.noise, self.threshold = [], None
        self.frames, self.started, self.speech_blocks, self.silent = [], False, 0, 0
        self.elapsed = 0.0

    @staticmethod
    def _rms(block):
        return float(np.sqrt(np.mean(np.square(block)))) if len(block) else 0.0

    def feed(self, block):
        """Returns None while listening, 'done' when an utterance finished, 'timeout' if nobody spoke."""
        self.elapsed += self.block_seconds
        level = self._rms(block)
        if self.threshold is None:
            self.noise.append(level)
            self.preroll.append(block)
            if len(self.noise) >= self.calibration_blocks:
                self.threshold = max(self.floor, float(np.median(self.noise)) * self.factor)
            return None

        if not self.started:
            self.preroll.append(block)
            if level > self.threshold:
                self.started = True
                self.frames = list(self.preroll)
                self.speech_blocks = 1
            elif self.elapsed > self.start_timeout:
                return "timeout"
            return None

        self.frames.append(block)
        if level > self.threshold:
            self.speech_blocks += 1
            self.silent = 0
        else:
            self.silent += 1
        if self.silent >= self.silence_blocks_needed or self.elapsed > self.start_timeout + self.max_seconds:
            return "done" if self.speech_blocks >= self.min_speech_blocks else "timeout"
        return None

    def audio(self):
        return np.concatenate(self.frames).astype(np.float32) if self.frames else np.zeros(0, np.float32)


class FasterWhisperBackend:
    name = "faster_whisper"

    def __init__(self, settings):
        self.settings = settings
        self.model = None

    def _load(self):
        if self.model is not None:
            return
        from faster_whisper import WhisperModel
        errors = []
        for size in [self.settings.whisper_model_size, "small.en", "base.en"]:
            try:
                self.model = WhisperModel(size, device=self.settings.whisper_device, compute_type=self.settings.whisper_compute)
                log.info(f"faster-whisper loaded '{size}' on {self.settings.whisper_device}")
                return
            except Exception as e:
                errors.append(f"{size}: {e}")
        raise RuntimeError("; ".join(errors))

    def transcribe(self, audio, hint_words=()):
        self._load()
        prompt = "Computer voice commands: open, close, create, delete, copy, move, search, notepad, chrome, calculator"
        if hint_words:
            prompt += ", " + ", ".join(list(hint_words)[:15])
        segments, _ = self.model.transcribe(
            audio, language=self.settings.whisper_language or None, beam_size=5, temperature=0.0,
            vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
            condition_on_previous_text=False, no_speech_threshold=0.6, initial_prompt=prompt,
        )
        kept = [s.text for s in segments if not (getattr(s, "no_speech_prob", 0) > 0.6 and getattr(s, "avg_logprob", 0) < -1.0)]
        return clean_transcript(" ".join(kept))


class NemoHttpBackend:
    name = "nemo_http"

    def __init__(self, settings):
        self.url = f"http://127.0.0.1:{settings.nemo_server_port}"

    def healthy(self):
        import requests
        try:
            return requests.get(f"{self.url}/health", timeout=1.5).status_code == 200
        except Exception:
            return False

    def transcribe(self, audio, hint_words=()):
        import requests
        r = requests.post(f"{self.url}/transcribe", data=audio.astype(np.float32).tobytes(),
                          headers={"Content-Type": "application/octet-stream"}, timeout=60)
        r.raise_for_status()
        return clean_transcript(r.json().get("text", ""))


class STTEngine:
    def __init__(self, settings=None, hint_words_fn=None):
        self.settings = settings or Settings.load()
        self.hint_words_fn = hint_words_fn or (lambda: ())
        self.whisper = FasterWhisperBackend(self.settings)
        self.nemo = NemoHttpBackend(self.settings)

    def _order(self):
        mode = self.settings.stt_backend
        if mode == "nemo_http":
            return [self.nemo, self.whisper]
        if mode == "auto":
            return [self.nemo, self.whisper] if self.nemo.healthy() else [self.whisper]
        return [self.whisper]

    def transcribe(self, audio):
        if audio is None or len(audio) < RATE * 0.2:
            return ""
        hints = tuple(self.hint_words_fn())
        for backend in self._order():
            try:
                text = backend.transcribe(audio, hints)
                log.info(f"[{backend.name}] Transcribed: {text}")
                return "" if is_junk(text) else text
            except Exception as e:
                log.warning(f"STT backend {backend.name} failed ({e}); trying next")
        return ""

    def listen(self, start_timeout=None, silence_seconds=None, max_seconds=None):
        """Block until one utterance is captured (or nobody speaks). Returns float32 audio or None."""
        import queue
        import sounddevice as sd
        s = self.settings
        ep = Endpointer(silence_seconds=silence_seconds or s.utterance_silence_seconds,
                        start_timeout=start_timeout or s.session_start_timeout,
                        max_seconds=max_seconds or s.utterance_max_seconds,
                        floor=s.vad_energy_floor)
        q = queue.Queue()
        block = int(RATE * ep.block_seconds)
        with sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=block,
                            callback=lambda indata, f, t, st: q.put(indata[:, 0].copy())):
            while True:
                state = ep.feed(q.get())
                if state == "done":
                    return ep.audio()
                if state == "timeout":
                    return None


def record_and_transcribe(duration=5, settings=None):
    """Back-compat helper used by older scripts: fixed-length recording."""
    import sounddevice as sd
    settings = settings or Settings.load()
    audio = sd.rec(int(duration * RATE), samplerate=RATE, channels=1, dtype="float32")
    sd.wait()
    return STTEngine(settings).transcribe(audio.flatten())
