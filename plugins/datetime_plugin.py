from datetime import datetime
from core.narrator import narrate

PLUGIN_NAME = "datetime"
ACTIONS = {"time", "date", "day"}


def handle(intent):
    now = datetime.now()
    action = intent.get("action")
    text = now.strftime("It's %I:%M %p") if action == "time" else now.strftime("Today is %A, %d %B %Y")
    narrate(text)
    return {"status": "success", "message": text, "data": now.isoformat(timespec="seconds")}
