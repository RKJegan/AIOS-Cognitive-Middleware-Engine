import re
from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate
from core import confirm
from core.paths import PROJECT_ROOT
from config.settings import Settings

log = get_logger()

BLOCKED_PATTERNS = [
    r"^[a-z]:\\windows($|\\)",
    r"\\windows\\system32",
    r"^[a-z]:\\?$",
    r"^[a-z]:\\users\\[^\\]+\\?$",
    r"format\s",
    r"del\s+/s\s+/q",
    r"rd\s+/s\s+/q",
]

SENSITIVE_PATHS = [
    r"^[a-z]:\\program files",
    r"^[a-z]:\\users\\public",
    r"^[a-z]:\\programdata",
    r"\\appdata\\",
]

# Action names that always need a typed YES. Controllers add theirs via register_risks().
DANGEROUS_ACTIONS = {
    "delete", "uninstall", "shutdown", "restart", "kill", "kill_process", "format",
    "close_all", "end_all", "send", "git_push", "install_package", "run_script",
    "web_risky_click", "approve_workspace", "run_code_agent",
}

# Never allowed inside saved workflows (they run unattended / on a schedule).
WORKFLOW_FORBIDDEN = DANGEROUS_ACTIONS | {"run_command", "write_code", "set_workspace"}


def is_workflow_safe(action):
    return action not in WORKFLOW_FORBIDDEN


class SafetyLayer:
    """Level 1 hard blocks, Level 2 typed confirmation, Level 3 sensitive-path warnings."""

    def __init__(self, settings=None):
        self.settings = settings or Settings.load()

    def register_risks(self, levels):
        for action, level in levels.items():
            if level == "dangerous":
                DANGEROUS_ACTIONS.add(action)
                WORKFLOW_FORBIDDEN.add(action)

    @staticmethod
    def _norm(target):
        return str(target).lower().replace("/", "\\").strip()

    def _is_blocked(self, target):
        if not target:
            return False
        t = self._norm(target)
        return any(re.search(p, t) for p in BLOCKED_PATTERNS)

    def _is_sensitive(self, target):
        if not target:
            return False
        t = self._norm(target)
        return any(re.search(p, t) for p in SENSITIVE_PATHS)

    @staticmethod
    def _covers_project(target):
        try:
            t = Path(target).expanduser().resolve()
            return t == PROJECT_ROOT or t in PROJECT_ROOT.parents
        except Exception:
            return False

    def validate(self, action_type, target=None):
        blocked = self._is_blocked(target)
        if not blocked and action_type in ("delete", "kill", "uninstall") and target:
            blocked = self._covers_project(target)

        if blocked:
            log.error(f"BLOCKED: action='{action_type}' target='{target}'")
            narrate(f"I can't do that. '{target}' is protected.")
            return {"status": "blocked", "message": "This action is never permitted.", "data": None}

        if self._is_sensitive(target):
            log.warning(f"Sensitive path: action='{action_type}' target='{target}'")
            narrate(f"Warning: '{target}' is a sensitive location.")

        if action_type in DANGEROUS_ACTIONS and self.settings.confirm_dangerous_actions:
            narrate(f"About to {action_type} '{target}'.")
            if not confirm.ask(f"Confirm {action_type} on '{target}'?"):
                log.info(f"User cancelled: action='{action_type}' target='{target}'")
                narrate("Cancelled.")
                return {"status": "cancelled", "message": "User did not confirm.", "data": None}
            log.info(f"User confirmed: action='{action_type}' target='{target}'")

        return {"status": "approved", "message": "Action approved.", "data": None}
