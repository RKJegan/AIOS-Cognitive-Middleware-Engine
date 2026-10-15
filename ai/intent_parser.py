from core.logger import get_logger
from ai.categories import CATEGORIES

log = get_logger()

NEEDS_NAME = {"create_folder", "create_file", "delete", "copy", "move", "rename", "compress"}


class IntentParser:
    def parse(self, raw_intent):
        cleaned = {
            "intent": raw_intent.get("intent") or "unknown",
            "action": raw_intent.get("action"),
            "name": raw_intent.get("name"),
            "location_ref": raw_intent.get("location_ref"),
            "destination_ref": raw_intent.get("destination_ref"),
            "raw_text": raw_intent.get("raw_text", ""),
        }

        if isinstance(cleaned["intent"], str):
            cleaned["intent"] = cleaned["intent"].strip().lower()
        if cleaned["intent"] not in CATEGORIES:
            log.warning(f"Unknown category '{cleaned['intent']}' -> unknown")
            cleaned["intent"] = "unknown"
        if isinstance(cleaned["action"], str):
            cleaned["action"] = cleaned["action"].strip().lower() or None

        for key in ("name", "location_ref", "destination_ref"):
            val = cleaned[key]
            if isinstance(val, (int, float)):
                val = str(val)
            if isinstance(val, str):
                val = val.strip() or None
                if val and val.lower() in ("null", "none"):
                    val = None
            cleaned[key] = val

        if cleaned["action"] in NEEDS_NAME and not cleaned["name"]:
            log.warning(f"'{cleaned['action']}' with no name: {raw_intent}")
        return cleaned
