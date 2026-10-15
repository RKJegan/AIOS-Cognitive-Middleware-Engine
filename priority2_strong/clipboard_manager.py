from collections import deque
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


class ClipboardManager:
    def __init__(self, history_size=20):
        self.history = deque(maxlen=history_size)

    def copy(self, text):
        try:
            import pyperclip
            pyperclip.copy(text or "")
            self.history.appendleft(text or "")
            narrate(f"Copied: {text}")
            return {"status": "success", "message": "Copied to clipboard", "data": {"text": text}}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't copy (install pyperclip): {e}", "data": None}

    def paste(self):
        try:
            import pyperclip
            text = pyperclip.paste()
            narrate(f"Clipboard has: {text[:80]}")
            return {"status": "success", "message": "Read clipboard", "data": {"text": text}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def show_history(self):
        items = list(self.history)
        narrate(f"{len(items)} item(s) in clipboard history")
        return {"status": "success", "message": f"{len(items)} item(s)", "data": items}

    def select(self, index_text):
        try:
            i = int(index_text) - 1
            value = list(self.history)[i]
            import pyperclip
            pyperclip.copy(value)
            narrate(f"Selected: {value[:80]}")
            return {"status": "success", "message": "Selected from history", "data": {"text": value}}
        except (ValueError, IndexError):
            return {"status": "error", "message": "No such history item", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def clear(self):
        self.history.clear()
        try:
            import pyperclip
            pyperclip.copy("")
        except Exception:
            pass
        narrate("Clipboard cleared")
        return {"status": "success", "message": "Cleared", "data": None}

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action == "copy":
            return self.copy(name)
        if action == "paste":
            return self.paste()
        if action == "history":
            return self.show_history()
        if action == "select":
            return self.select(name)
        if action == "clear":
            return self.clear()
        return {"status": "unhandled", "message": f"Clipboard action '{action}' not implemented yet", "data": None}
