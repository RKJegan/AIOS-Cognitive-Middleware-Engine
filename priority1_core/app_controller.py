import os
import re
import subprocess
import time
import psutil
from core.logger import get_logger
from core.narrator import narrate
from config.settings import Settings
from security.safety_layer import SafetyLayer
from security.protected import PROTECTED_PROCESSES, PROTECTED_APPS

log = get_logger()

PROCESS_ALIASES = {
    "calc.exe": {"calc.exe", "calculatorapp.exe"},
    "notepad.exe": {"notepad.exe"},
}
DEFAULT_REGISTRY = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
}


class AppController:
    def __init__(self, settings=None, safety=None):
        self.settings = settings or Settings.load()
        self.safety = safety or SafetyLayer()
        self.opened_apps = set()
        if not self.settings.app_registry:
            self.settings.app_registry = dict(DEFAULT_REGISTRY)
            self.settings.save()

    @staticmethod
    def _valid_name(name):
        return bool(name) and bool(re.match(r"^[\w .\-]{1,80}$", name))

    def _exe_name(self, key):
        path = self.settings.app_registry.get(key)
        return os.path.basename(path).lower() if path else f"{key}.exe"

    def _is_running_exe(self, exe_name):
        names = PROCESS_ALIASES.get(exe_name, {exe_name})
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() in names:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def open_app(self, target):
        if not self._valid_name(target):
            return {"status": "error", "message": "Invalid application name", "data": None}
        key = target.lower().strip()

        path = self.settings.app_registry.get(key)
        if path:
            try:
                subprocess.Popen(path)
                log.info(f"Opened '{key}' via registry: {path}")
                narrate(f"Opening {key}")
                self.opened_apps.add(key)
                return {"status": "success", "message": f"Opened {key}", "data": {"source": "registry", "exe": self._exe_name(key)}}
            except Exception as e:
                log.error(f"Registry path failed for '{key}': {e}")

        try:
            os.startfile(key)
            log.info(f"Opened '{key}' via OS lookup")
            narrate(f"Opening {key}")
            self.opened_apps.add(key)
            return {"status": "success", "message": f"Opened {key}", "data": {"source": "os_lookup", "exe": None}}
        except OSError as e:
            log.warning(f"OS lookup failed for '{key}': {e}")

        narrate(f"I couldn't find {key}. You can register its path if you have it.")
        return {"status": "not_found", "message": f"Couldn't find '{key}'. Call register_app(name, path) to add it.", "data": None}

    def close_app(self, target):
        if not self._valid_name(target):
            return {"status": "error", "message": "Invalid application name", "data": None}
        key = target.lower().strip()
        exe_name = self._exe_name(key)

        if exe_name in PROTECTED_PROCESSES:
            narrate(f"I can't close {key}, it's a protected system process.")
            return {"status": "blocked", "message": f"'{exe_name}' is protected", "data": None}

        names = PROCESS_ALIASES.get(exe_name, {exe_name})
        matched = [p for p in psutil.process_iter(["pid", "name"])
                   if p.info.get("name") and p.info["name"].lower() in names]
        if not matched:
            return {"status": "not_found", "message": f"'{key}' isn't running", "data": None}
        for p in matched:
            try:
                p.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self.opened_apps.discard(key)
        narrate(f"Closing {key}")
        log.info(f"Closed {len(matched)} process(es) matching: {exe_name}")
        return {"status": "success", "message": f"Closed {key}", "data": None}

    def close_all_apps(self):
        if not self.opened_apps:
            return {"status": "not_found", "message": "No apps have been opened this session", "data": None}
        check = self.safety.validate("close_all", "all apps opened this session")
        if check["status"] != "approved":
            return check
        results = [self.close_app(k) for k in list(self.opened_apps)]
        ok = sum(1 for r in results if r["status"] == "success")
        narrate(f"Closed {ok} app(s)")
        return {"status": "success", "message": f"Closed {ok} app(s)", "data": results}

    def uninstall_app(self, target):
        if not self._valid_name(target):
            return {"status": "error", "message": "Invalid application name", "data": None}
        key = target.lower().strip()
        if key in PROTECTED_APPS:
            narrate(f"{key} is a protected system component and shouldn't be uninstalled.")
            return {"status": "blocked", "message": f"'{key}' is protected", "data": None}

        check = self.safety.validate("uninstall", key)
        if check["status"] != "approved":
            return check

        msg = (f"I don't remove applications myself, that has to be done manually for safety. "
               f"To uninstall {key}: open Settings, go to Apps, find {key}, and click Uninstall.")
        narrate(msg)
        return {"status": "manual_action_required", "message": msg,
                "data": {"steps": ["Open Settings", "Go to Apps", f"Find {key}", "Click Uninstall"]}}

    def register_app(self, name, path):
        key = name.lower().strip()
        self.settings.app_registry[key] = path
        self.settings.save()
        return {"status": "success", "message": f"Added '{key}' to registry", "data": None}

    # ---- process_management (shared handler) ----
    def list_processes(self, limit=15):
        procs = sorted(psutil.process_iter(["pid", "name", "memory_percent"]),
                        key=lambda p: p.info.get("memory_percent") or 0, reverse=True)[:limit]
        data = [{"pid": p.info["pid"], "name": p.info["name"]} for p in procs]
        return {"status": "success", "message": f"Top {len(data)} processes", "data": data}

    def find_process(self, name):
        if not name:
            return {"status": "error", "message": "Need a process name", "data": None}
        n = name.lower()
        matches = [{"pid": p.info["pid"], "name": p.info["name"]}
                   for p in psutil.process_iter(["pid", "name"])
                   if p.info.get("name") and n in p.info["name"].lower()]
        return {"status": "success" if matches else "not_found", "message": f"{len(matches)} match(es)", "data": matches}

    def kill_process(self, name):
        return self.close_app(name)

    def restart_process(self, name):
        close_result = self.close_app(name)
        time.sleep(1)
        open_result = self.open_app(name)
        ok = open_result["status"] == "success"
        return {"status": "success" if ok else "error",
                "message": f"Restarted {name}" if ok else f"Closed but couldn't reopen {name}",
                "data": {"close": close_result, "open": open_result}}

    def handle(self, intent):
        action = intent.get("action")
        target = intent.get("name")
        if action == "close_all":
            return self.close_all_apps()
        if action == "close":
            return self.close_app(target)
        if action == "uninstall":
            return self.uninstall_app(target)
        if action in ("end_all",):
            return self.close_all_apps()
        if action == "list":
            return self.list_processes()
        if action == "find":
            return self.find_process(target)
        if action == "kill":
            return self.kill_process(target)
        if action == "restart":
            return self.restart_process(target)
        return self.open_app(target)

    def verify_open(self, intent, result):
        if intent.get("action") != "open" or result.get("status") != "success":
            return None
        data = result.get("data")
        if not isinstance(data, dict):
            return None
        exe = data.get("exe")
        if not exe:
            return None
        for _ in range(5):
            if self._is_running_exe(exe):
                return True
            time.sleep(0.3)
        return False

    def kill_process(self, name):
        check = self.safety.validate("kill", name)
        if check["status"] != "approved":
            return check
        return self.close_app(name)

    def restart_process(self, name):
        check = self.safety.validate("restart", name)
        if check["status"] != "approved":
            return check
        close_result = self.close_app(name)
        time.sleep(1)
        open_result = self.open_app(name)
        ok = open_result["status"] == "success"
        return {"status": "success" if ok else "error",
                "message": f"Restarted {name}" if ok else f"Closed but couldn't reopen {name}",
                "data": {"close": close_result, "open": open_result}}