"""Simple in-process scheduler: 'every day at HH:MM' or 'in N minutes/hours', runs saved workflows."""
import re
import threading
import time
from datetime import datetime, timedelta
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()

DAILY_RE = re.compile(r"every day at (\d{1,2}):?(\d{2})?\s*(am|pm)?", re.IGNORECASE)
IN_RE = re.compile(r"in\s+(\d+)\s*(second|minute|hour)s?", re.IGNORECASE)


def _next_daily(hour, minute):
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


class ScheduleManager:
    def __init__(self, workflow_manager):
        self.wm = workflow_manager
        self.jobs = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def _parse(self, text):
        text = (text or "").strip()
        m = DAILY_RE.search(text)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            if (m.group(3) or "").lower() == "pm" and hour != 12:
                hour += 12
            return ("daily", hour, minute)
        m = IN_RE.search(text)
        if m:
            n, unit = int(m.group(1)), m.group(2).lower()
            return ("once", n * {"second": 1, "minute": 60, "hour": 3600}[unit])
        return None

    def _arm(self, job_id, workflow_name, spec):
        def fire():
            if self.jobs.get(job_id, {}).get("cancelled"):
                return
            narrate(f"Running scheduled workflow: {workflow_name}")
            self.wm.run_workflow(workflow_name)
            if spec[0] == "daily":
                self._arm(job_id, workflow_name, spec)

        delay = (_next_daily(spec[1], spec[2]) - datetime.now()).total_seconds() if spec[0] == "daily" else spec[1]
        timer = threading.Timer(max(delay, 1), fire)
        timer.daemon = True
        timer.start()
        self.jobs[job_id]["timer"] = timer

    def schedule(self, workflow_name, when_text):
        if not workflow_name:
            return {"status": "error", "message": "Need a workflow name", "data": None}
        spec = self._parse(when_text)
        if not spec:
            narrate("I can schedule 'every day at HH:MM' or 'in N minutes/hours'.")
            return {"status": "unhandled", "message": "Could not parse schedule", "data": None}
        with self._lock:
            job_id = self._next_id
            self._next_id += 1
            self.jobs[job_id] = {"workflow": workflow_name, "when": when_text, "cancelled": False}
        self._arm(job_id, workflow_name, spec)
        narrate(f"Scheduled '{workflow_name}' {when_text}")
        return {"status": "success", "message": f"Scheduled job {job_id}", "data": {"job_id": job_id}}

    def list_jobs(self):
        active = [{"id": jid, **{k: v for k, v in j.items() if k != "timer"}}
                  for jid, j in self.jobs.items() if not j.get("cancelled")]
        narrate(f"{len(active)} scheduled job(s)")
        return {"status": "success", "message": f"{len(active)} job(s)", "data": active}

    def cancel(self, job_id_text):
        try:
            job_id = int(job_id_text)
        except (TypeError, ValueError):
            return {"status": "error", "message": "Need a numeric job id", "data": None}
        job = self.jobs.get(job_id)
        if not job:
            return {"status": "not_found", "message": f"No job {job_id}", "data": None}
        job["cancelled"] = True
        if job.get("timer"):
            job["timer"].cancel()
        narrate(f"Cancelled schedule {job_id}")
        return {"status": "success", "message": f"Cancelled job {job_id}", "data": None}

    def handle(self, intent):
        action, name, dest = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        if action == "schedule":
            return self.schedule(name, dest or intent.get("raw_text"))
        if action == "list":
            return self.list_jobs()
        if action == "cancel":
            return self.cancel(name)
        return {"status": "unhandled", "message": f"Scheduling action '{action}' not implemented yet", "data": None}
