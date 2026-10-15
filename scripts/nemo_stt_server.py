"""NVIDIA NeMo speech-to-text as a tiny local HTTP service.

Run it from a SEPARATE Python 3.12+ environment that has NeMo installed
(NeMo Speech 3.0 needs Python >= 3.12, your main app can stay on 3.10):

    py -3.12 -m venv .venv-nemo
    .venv-nemo\\Scripts\\activate
    pip install "nemo-toolkit[asr]"
    python scripts/nemo_stt_server.py --model nvidia/parakeet-tdt-0.6b-v3 --device cpu

Endpoints: GET /health   POST /transcribe  (body = raw float32 mono 16 kHz audio)
Uses only the standard library for HTTP, so it works the same on any machine.
"""
import argparse
import json
import os
import tempfile
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np


def load_model(name, device):
    import nemo.collections.asr as nemo_asr
    model = nemo_asr.models.ASRModel.from_pretrained(model_name=name)
    if device == "cpu":
        model = model.to("cpu")
    else:
        model = model.to("cuda")
    model.eval()
    return model


def make_transcriber(model):
    def transcribe(audio):
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(pcm.tobytes())
            out = model.transcribe([path])
            first = out[0] if isinstance(out, (list, tuple)) else out
            if isinstance(first, (list, tuple)):      # some NeMo versions return (texts, ...)
                first = first[0]
            return getattr(first, "text", first) or ""
        finally:
            os.remove(path)
    return transcribe


def make_handler(transcribe):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self._send(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})

        def do_POST(self):
            if self.path != "/transcribe":
                return self._send(404, {"error": "not found"})
            n = int(self.headers.get("Content-Length", 0))
            audio = np.frombuffer(self.rfile.read(n), dtype=np.float32)
            try:
                self._send(200, {"text": str(transcribe(audio)).strip()})
            except Exception as e:                       # keep the server alive on bad audio
                self._send(500, {"error": str(e)})

        def log_message(self, *a):
            pass
    return Handler


def serve(transcribe, port):
    server = HTTPServer(("127.0.0.1", port), make_handler(transcribe))
    server.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="nvidia/parakeet-tdt-0.6b-v3")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    print(f"Loading {args.model} on {args.device} ...")
    transcriber = make_transcriber(load_model(args.model, args.device))
    print(f"NeMo STT ready on http://127.0.0.1:{args.port}")
    serve(transcriber, args.port)
