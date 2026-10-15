"""Claude Code as a folder-jailed coding backend. The ONLY feature that leaves the machine."""
import json
import shutil
import subprocess
from datetime import datetime
from core.logger import get_logger
from core.narrator import narrate
from core.paths import DATA_DIR, PROJECT_ROOT
from security.safety_layer import SafetyLayer
from security.workspace_guard import WorkspaceGuard, WorkspaceError

log = get_logger()
AUDIT_FILE = DATA_DIR / "audit" / "code_agent.jsonl"
RULES = ("\n\nRules: work only inside the current directory. Never read or modify .env files, keys, tokens or "
         "credentials. Do not run shell commands or install packages. Write complete, working files.")


class CodeAgent:
    RISK_LEVELS = {"approve_workspace": "dangerous", "run_code_agent": "dangerous"}

    def __init__(self, settings, safety=None):
        self.settings = settings
        self.safety = safety or SafetyLayer(settings)
        self.safety.register_risks(self.RISK_LEVELS)
        self.guard = None

    def set_workspace(self, path):
        if not path:
            return {"status": "needs_clarification", "message": "Which folder?", "data": None}
        try:
            root = WorkspaceGuard.validate_root(path, PROJECT_ROOT)
        except WorkspaceError as e:
            narrate(str(e))
            return {"status": "blocked", "message": str(e), "data": None}
        check = self.safety.validate("approve_workspace", str(root))
        if check["status"] != "approved":
            return check
        self.guard = WorkspaceGuard(root, PROJECT_ROOT)
        narrate(f"Coding workspace set to {root}")
        return {"status": "success", "message": str(root), "data": str(root)}

    def _audit(self, record):
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def write_code(self, task):
        if self.guard is None:
            narrate("Set a coding workspace first.")
            return {"status": "needs_clarification", "message": "Say: set coding workspace to <folder>", "data": None}
        task = (task or "").strip()
        if not task or len(task) > 2000 or "\x00" in task:
            return {"status": "needs_clarification", "message": "Describe the coding task (under 2000 characters)", "data": None}
        exe = shutil.which(self.settings.claude_command)
        if not exe:
            return {"status": "error", "message": "Claude Code CLI not found. Install it and sign in, or fix claude_command in settings.", "data": None}

        narrate("Heads up: this sends your request to Claude Code over the internet.")
        check = self.safety.validate("run_code_agent", f"'{task[:60]}' in {self.guard.root}")
        if check["status"] != "approved":
            return check

        before = self.guard.snapshot()
        cmd = [exe, "-p", "--allowedTools", "Read", "Write", "Edit"] + list(self.settings.claude_extra_args)
        narrate("Claude Code is working. This can take a few minutes.")
        try:
            proc = subprocess.run(cmd, input=task + RULES, cwd=str(self.guard.root), capture_output=True,
                                  text=True, timeout=self.settings.code_agent_timeout)
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Claude Code timed out", "data": None}

        diff = self.guard.diff(before, self.guard.snapshot())
        flagged = self.guard.flag_sensitive(diff)
        self._audit({"ts": datetime.now().isoformat(timespec="seconds"), "task": task, "root": str(self.guard.root),
                     "returncode": proc.returncode, "diff": diff, "flagged": flagged,
                     "output_head": (proc.stdout or proc.stderr)[:500]})

        changed = len(diff["added"]) + len(diff["modified"]) + len(diff["deleted"])
        if flagged:
            narrate(f"Warning: secret-looking files were touched: {', '.join(flagged)}")
        if proc.returncode != 0 and not changed:
            return {"status": "error", "message": (proc.stderr or proc.stdout)[:300] or "Claude Code failed", "data": diff}
        narrate(f"Done. {len(diff['added'])} added, {len(diff['modified'])} changed, {len(diff['deleted'])} deleted.")
        return {"status": "success", "message": f"{changed} file change(s)", "data": {"diff": diff, "flagged": flagged}}

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action == "set_workspace":
            return self.set_workspace(name)
        if action == "write_code":
            return self.write_code(name)
        return {"status": "unhandled", "message": f"Code agent action '{action}' not implemented", "data": None}
