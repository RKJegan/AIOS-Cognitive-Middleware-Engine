"""Session memory so 'close it' / 'delete that' resolve to what the last command touched."""
import re
from collections import deque

OBJECT_VERBS = {"close", "open", "delete", "copy", "move", "rename", "kill", "restart", "minimize", "maximize"}
PRONOUN = re.compile(r"\b(it|that|them)\b", re.IGNORECASE)


class ContextEngine:
    def __init__(self, size=10):
        self.history = deque(maxlen=size)

    def record(self, steps, results):
        for step, result in zip(steps, results):
            if result.get("status") == "success" and step.get("name"):
                self.history.append({
                    "intent": step.get("intent"), "action": step.get("action"),
                    "name": step.get("name"), "location_ref": step.get("location_ref"),
                })

    def last(self):
        return self.history[-1] if self.history else None

    def resolve(self, text, prior=None):
        """prior = (name, location_ref) from an earlier clause in the same sentence."""
        words = text.strip().split()
        if not words or len(words) > 6 or words[0].lower() not in OBJECT_VERBS:
            return text
        if not PRONOUN.search(text):
            return text

        if prior and prior[0]:
            name, loc = prior
        elif self.last():
            name, loc = self.last()["name"], self.last()["location_ref"]
        else:
            return text

        replacement = f"{name} from {loc}" if loc and words[0].lower() in {"delete", "copy", "move", "rename"} else name
        return PRONOUN.sub(replacement, text, count=1)
