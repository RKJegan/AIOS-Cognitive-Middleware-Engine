from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


class TextAssistant:
    def __init__(self, brain, document_controller=None):
        self.brain = brain
        self.docs = document_controller

    def summarize(self, name, location_ref):
        text = name
        if location_ref and self.docs:
            path = str(Path(location_ref) / name)
            result = self.docs.read(path)
            if result["status"] != "success":
                return result
            text = result["data"]["text"]
        if not text:
            return {"status": "error", "message": "Nothing to summarize", "data": None}
        summary = self.brain.complete(f"Summarize this in 3-4 sentences, plain text only:\n\n{text[:4000]}")
        if not summary:
            return {"status": "error", "message": "Summarization failed (is Ollama running?)", "data": None}
        narrate(summary)
        return {"status": "success", "message": "Summarized", "data": {"summary": summary}}

    def translate(self, text, target_language):
        if not text or not target_language:
            return {"status": "error", "message": "Need text and a target language", "data": None}
        translated = self.brain.complete(f"Translate to {target_language}. Reply with ONLY the translation:\n\n{text}")
        narrate(translated or "Translation failed")
        return {"status": "success" if translated else "error", "message": translated, "data": {"translation": translated}}

    def draft(self, topic):
        if not topic:
            return {"status": "error", "message": "Need a topic", "data": None}
        draft = self.brain.complete(f"Write a short, professional email about: {topic}. Just the email body.")
        narrate("Here's a draft")
        return {"status": "success" if draft else "error", "message": draft or "Drafting failed", "data": {"draft": draft}}

    def explain(self, text):
        explanation = self.brain.complete(f"Explain this simply, 2-3 sentences:\n\n{text}")
        narrate(explanation or "Couldn't explain that")
        return {"status": "success" if explanation else "error", "message": explanation, "data": None}

    def handle(self, intent):
        action, name, loc, dest = intent.get("action"), intent.get("name"), intent.get("location_ref"), intent.get("destination_ref")
        if action == "summarize":
            return self.summarize(name, loc)
        if action == "translate":
            return self.translate(name, dest)
        if action == "draft":
            return self.draft(name)
        if action == "explain":
            return self.explain(name)
        return {"status": "unhandled", "message": f"Text assistant action '{action}' not implemented yet", "data": None}
