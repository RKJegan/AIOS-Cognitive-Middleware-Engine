import subprocess
from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate
from core.paths import PROJECT_ROOT
from security.safety_layer import SafetyLayer

log = get_logger()

SAFE_COMMAND_PREFIXES = ("python", "python3", "pip", "node", "npm", "npx", "echo", "dir", "ls")


class DeveloperOperations:
    def __init__(self, cwd=None, safety=None):
        self.cwd = Path(cwd) if cwd else PROJECT_ROOT
        self.safety = safety or SafetyLayer()

    def set_cwd(self, path):
        p = Path(path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            return {"status": "error", "message": f"'{path}' is not a folder", "data": None}
        self.cwd = p
        narrate(f"Developer operations now target {p}")
        return {"status": "success", "message": f"cwd set to {p}", "data": {"cwd": str(p)}}

    def _run(self, args):
        try:
            result = subprocess.run(args, cwd=self.cwd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0, (result.stdout + result.stderr).strip()
        except Exception as e:
            return False, str(e)

    def git_status(self):
        ok, out = self._run(["git", "status", "--short"])
        narrate("Git status checked")
        return {"status": "success" if ok else "error", "message": out[:500] or "clean", "data": {"output": out}}

    def git_commit(self, message):
        if not message:
            return {"status": "error", "message": "Need a commit message", "data": None}
        self._run(["git", "add", "-A"])
        ok, out = self._run(["git", "commit", "-m", message])
        narrate("Committed" if ok else "Commit failed")
        return {"status": "success" if ok else "error", "message": out[:500], "data": None}

    def git_push(self):
        check = self.safety.validate("git_push", str(self.cwd))
        if check["status"] != "approved":
            return check
        ok, out = self._run(["git", "push"])
        narrate("Pushed" if ok else "Push failed")
        return {"status": "success" if ok else "error", "message": out[:500], "data": None}

    def git_pull(self):
        ok, out = self._run(["git", "pull"])
        narrate("Pulled" if ok else "Pull failed")
        return {"status": "success" if ok else "error", "message": out[:500], "data": None}

    def create_venv(self, name):
        name = name or "venv"
        ok, out = self._run(["python", "-m", "venv", name])
        narrate(f"Created virtual environment {name}" if ok else "Failed to create venv")
        return {"status": "success" if ok else "error", "message": out[:500] or f"venv '{name}' created", "data": None}

    def install_package(self, package):
        if not package:
            return {"status": "error", "message": "Need a package name", "data": None}
        check = self.safety.validate("install_package", package)
        if check["status"] != "approved":
            return check
        ok, out = self._run(["pip", "install", package])
        narrate(f"Installed {package}" if ok else f"Failed to install {package}")
        return {"status": "success" if ok else "error", "message": out[-500:], "data": None}

    def run_command(self, command_text):
        if not command_text:
            return {"status": "error", "message": "Need a command", "data": None}
        first = command_text.strip().split()[0].lower()
        if first not in SAFE_COMMAND_PREFIXES:
            check = self.safety.validate("run_script", command_text)
            if check["status"] != "approved":
                return check
        ok, out = self._run(command_text.split())
        narrate("Command finished" if ok else "Command failed")
        return {"status": "success" if ok else "error", "message": out[-800:], "data": {"output": out}}

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action == "git_status":
            return self.git_status()
        if action == "git_commit":
            return self.git_commit(name)
        if action == "git_push":
            return self.git_push()
        if action == "git_pull":
            return self.git_pull()
        if action == "create_venv":
            return self.create_venv(name)
        if action == "install_package":
            return self.install_package(name)
        if action == "run_command":
            return self.run_command(name)
        return {"status": "unhandled", "message": f"Developer action '{action}' not implemented yet", "data": None}
