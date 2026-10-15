import re
import threading
import time
from datetime import datetime, timedelta
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


def _toast(title, message):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=8)
    except Exception as e:
        log.warning(f"Toast failed ({e}); narrating instead")
        narrate(f"{title}: {message}")


def _parse_in(text):
    m = re.search(r"in\s+(\d+)\s*(second|minute|hour)s?", text or "", re.IGNORECASE)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    seconds = n * {"second": 1, "minute": 60, "hour": 3600}[unit]
    return seconds


class NotificationSystem:
    def __init__(self):
        self.timers = []

    def notify_now(self, message):
        _toast("Cognitive Middleware", message or "")
        return {"status": "success", "message": "Notification shown", "data": None}

    def remind(self, message, when_text):
        seconds = _parse_in(when_text)
        if seconds is None:
            narrate("I can only schedule reminders phrased like 'in 10 minutes' right now.")
            return {"status": "unhandled", "message": "Could not parse reminder time (only 'in N minutes/hours' supported)", "data": None}

        fire_at = datetime.now() + timedelta(seconds=seconds)
        timer = threading.Timer(seconds, lambda: _toast("Reminder", message))
        timer.daemon = True
        timer.start()
        self.timers.append(timer)
        narrate(f"I'll remind you: {message}, at {fire_at.strftime('%H:%M')}")
        return {"status": "success", "message": f"Reminder set for {fire_at.strftime('%H:%M')}", "data": {"fire_at": fire_at.isoformat()}}

    def handle(self, intent):
        action, name, dest = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        if action == "notify":
            return self.notify_now(name)
        if action == "remind":
            return self.remind(name, dest or intent.get("raw_text"))
        return {"status": "unhandled", "message": f"Notification action '{action}' not implemented yet", "data": None}
