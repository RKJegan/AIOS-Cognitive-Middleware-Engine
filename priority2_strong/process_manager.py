import subprocess
import time
import psutil
from core.logger import get_logger
from core.narrator import narrate
from security.safety_layer import SafetyLayer
from security.protected import PROTECTED_PROCESSES

log = get_logger()


class ProcessManager:
    RISK_LEVELS = {"kill": "dangerous", "restart": "dangerous", "end_all": "dangerous"}

    def __init__(self, app_controller, safety=None):
        self.app = app_controller
        self.safety = safety or SafetyLayer()
        self.safety.register_risks(self.RISK_LEVELS)

    def _exe_for(self, name):
        key = (name or "").lower().strip()
        if key.endswith(".exe"):
            return key
        return self.app._resolve_exe_name(key)

    def _matches(self, name):
        if (name or "").isdigit():
            try:
                return [psutil.Process(int(name))]
            except psutil.NoSuchProcess:
                return []
        names = self.app._exe_names(self._exe_for(name))
        found = []
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and p.info["name"].lower() in names:
                    found.append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return found

    def list_top(self, limit=10):
        rows = []
        for p in psutil.process_iter(["pid", "name", "memory_percent"]):
            try:
                if p.info["name"]:
                    rows.append({"pid": p.info["pid"], "name": p.info["name"],
                                 "memory_percent": round(p.info["memory_percent"], 1)})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        top = sorted(rows, key=lambda r: r["memory_percent"], reverse=True)[:limit]
        narrate("Biggest memory users: " + ", ".join(r["name"] for r in top[:5]))
        return {"status": "success", "message": f"Top {len(top)} by memory", "data": top}

    def find(self, name):
        found = self._matches(name)
        info = [{"pid": p.pid, "name": p.name()} for p in found]
        narrate(f"{name} is running ({len(info)} process{'es' if len(info) != 1 else ''})" if info else f"{name} isn't running")
        return {"status": "success" if info else "not_found", "message": f"{len(info)} match(es)", "data": info}

    def _guard(self, found):
        for p in found:
            try:
                if p.name().lower() in PROTECTED_PROCESSES:
                    narrate(f"{p.name()} is a protected process.")
                    return {"status": "blocked", "message": f"'{p.name()}' is protected", "data": None}
            except psutil.NoSuchProcess:
                continue
        return None

    def kill(self, name):
        found = self._matches(name)
        if not found:
            return {"status": "not_found", "message": f"'{name}' isn't running", "data": None}
        blocked = self._guard(found)
        if blocked:
            return blocked
        check = self.safety.validate("kill", f"{name} ({len(found)} process(es))")
        if check["status"] != "approved":
            return check
        for p in found:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _gone, alive = psutil.wait_procs(found, timeout=3)
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        log.info(f"Killed {len(found)} process(es): {name}")
        narrate(f"Ended {name}")
        return {"status": "success", "message": f"Ended {name}", "data": None}

    def restart(self, name):
        found = self._matches(name)
        if not found:
            return {"status": "not_found", "message": f"'{name}' isn't running", "data": None}
        blocked = self._guard(found)
        if blocked:
            return blocked
        try:
            exe = found[0].exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return {"status": "error", "message": "Can't read that process's path", "data": None}
        check = self.safety.validate("restart", f"{name}")
        if check["status"] != "approved":
            return check
        for p in found:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        psutil.wait_procs(found, timeout=3)
        time.sleep(0.5)
        subprocess.Popen([exe])
        narrate(f"Restarted {name}")
        return {"status": "success", "message": f"Restarted {name}", "data": None}

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action in ("end_all", "close_all"):
            return self.app.close_all_apps()
        if action == "list":
            return self.list_top()
        if action in ("find", "kill", "restart"):
            if not name:
                return {"status": "needs_clarification", "message": "Which process?", "data": None}
            return getattr(self, action)(name)
        return {"status": "unhandled", "message": f"Process action '{action}' not implemented", "data": None}
