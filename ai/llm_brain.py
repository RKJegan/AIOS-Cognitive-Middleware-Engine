import json
import requests
from core.logger import get_logger
from config.settings import Settings
from ai.categories import CATEGORIES
from ai.action_vocab import ACTION_VOCAB, normalize
from ai.retriever import ExampleRetriever

log = get_logger()

HEADER = """You are the intent parser for a Windows automation assistant.
Convert the user's request into ONE JSON object and nothing else.
Keys: intent, action, and (only when they apply) name, location_ref, destination_ref.
- name = the item acted on (app, file, text, setting value, workflow...)
- location_ref = where it is / which browser / which drive
- destination_ref = where it goes / the new value / the time ("in 10 minutes")
If the request is not a command for the computer, answer {"intent": "unknown", "action": "unknown"}.
Use EXACTLY these actions for each category (never invent new ones):
""" + "\n".join(f"- {c}: {', '.join(a)}" for c, a in ACTION_VOCAB.items() if c != "unknown")


class LLMBrain:
    def __init__(self, settings=None, retriever=None):
        self.settings = settings or Settings.load()
        self.model = self.settings.model_name
        self.host = self.settings.ollama_host
        self.retriever = retriever or ExampleRetriever()

    def _build_prompt(self, user_text):
        examples = self.retriever.top(user_text, k=self.settings.rag_top_k)
        lines = "\n".join(e.as_json_line() for e in examples)
        return (f"{HEADER}\n\nMost similar solved examples:\n{lines}\n\n"
                f'User said: "{user_text}"\nJSON:')

    @staticmethod
    def _fallback(user_text):
        return {"intent": "unknown", "action": None, "name": None,
                "location_ref": None, "destination_ref": None, "raw_text": user_text}

    def ask(self, user_text):
        payload = {
            "model": self.model, "prompt": self._build_prompt(user_text), "stream": False,
            "format": "json", "keep_alive": "60m", "options": {"temperature": 0, "num_predict": 150},
        }
        try:
            response = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            log.error(f"Ollama request failed: {e}")
            return self._fallback(user_text)

        raw = response.json().get("response", "").strip()
        try:
            intent = json.loads(raw)
            if isinstance(intent, list) and intent:
                intent = intent[0]
            if not isinstance(intent, dict):
                raise ValueError("not an object")
        except (json.JSONDecodeError, ValueError):
            log.error(f"Bad JSON from LLM: {raw[:200]}")
            return self._fallback(user_text)

        for key in ("name", "location_ref", "destination_ref"):
            intent.setdefault(key, None)
        intent["raw_text"] = user_text

        fixed, note = normalize(intent, spoken_text=user_text)
        if note:
            log.info(f'Corrected model output for "{user_text}": {note}')
        log.bind(command=True).info(f'User said: "{user_text}" -> {fixed}')
        return fixed

    def complete(self, prompt, timeout=120):
        payload = {"model": self.model, "prompt": prompt, "stream": False,
                   "keep_alive": "60m", "options": {"temperature": 0.3}}
        try:
            response = requests.post(f"{self.host}/api/generate", json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.RequestException as e:
            log.error(f"Ollama completion failed: {e}")
            return ""
