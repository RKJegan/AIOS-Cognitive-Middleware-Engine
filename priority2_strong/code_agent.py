"""Claude Code, folder-scoped only. Workflow: set_workspace -> write_code -> snapshot/diff reported.
Never runs with elevated scope, never touches anything outside WorkspaceGuard.root,
never modifies its own security/permission files (those live outside the workspace by construction).
"""
import subprocess
from core.logger import get_logger
from core.narrator import narrate
from core.paths import PROJECT_ROOT
from config.settings import Settings
from security.workspace_guard import WorkspaceGuard, WorkspaceError
from security.safety_layer import SafetyLayer

log = get_logger()


class CodeAgent:
    def __init__(self, settings=None, safety=None):
        self.settings = settings or Settings.load()
        self.safety = safety or SafetyLayer()
        self.guard = None

    def set_workspace(self, path):
        try:
            self.guard = WorkspaceGuard(path, project_root=PROJECT_ROOT)
        except WorkspaceError as e:
            narrate(f"I can't use that folder: {e}")
            return {"status": "error", "message": str(e), "data": None}
        narrate(f"Coding workspace set to {self.guard.root}")
        return {"status": "success", "message": f"Workspace: {self.guard.root}", "data": {"root": str(self.guard.root)}}

    def write_code(self, task_description):
        if not self.guard:
            narrate("Set a coding workspace first, e.g. 'set coding workspace to S:\\Projects\\demo'.")
            return {"status": "needs_clarification", "message": "No workspace set", "data": None}
        if not task_description:
            return {"status": "error", "message": "Need a task description", "data": None}

        check = self.safety.validate("run_code_agent", str(self.guard.root))
        if check["status"] != "approved":
            return check

        before = self.guard.snapshot()
        narrate("Asking Claude Code to work on this, this can take a while.")

        cmd = [self.settings.claude_command, "-p", task_description] + list(self.settings.claude_extra_args)
        try:
            result = subprocess.run(cmd, cwd=self.guard.root, capture_output=True, text=True,
                                     timeout=self.settings.code_agent_timeout)
            ok = result.returncode == 0
            output = (result.stdout + result.stderr)[-2000:]
        except FileNotFoundError:
            return {"status": "error", "message": "Claude Code CLI not found. Install it and/or set claude_command in settings.", "data": None}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Claude Code timed out", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

        after = self.guard.snapshot()
        diff = self.guard.diff(before, after)
        flagged = self.guard.flag_sensitive(diff)

        if diff["escaped_links"]:
            log.error(f"Symlink escape attempt detected: {diff['escaped_links']}")
            narrate("Something tried to write outside the workspace through a symlink. Blocked and reported.")
            return {"status": "blocked", "message": "Symlink escape attempt detected", "data": {"escaped": diff["escaped_links"]}}

        if flagged:
            narrate("The agent touched a file that looks like a secret. I'm flagging it, not auto-approving.")
            return {"status": "needs_review", "message": "Sensitive files were touched", "data": {"diff": diff, "flagged": flagged, "output": output}}

        summary = f"{len(diff['added'])} added, {len(diff['modified'])} modified, {len(diff['deleted'])} deleted"
        narrate(f"Done. {summary}" if ok else "The agent reported an error.")
        return {"status": "success" if ok else "error", "message": summary, "data": {"diff": diff, "output": output}}

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action == "set_workspace":
            return self.set_workspace(name)
        if action == "write_code":
            return self.write_code(name or intent.get("raw_text"))
        return {"status": "unhandled", "message": f"Code agent action '{action}' not implemented yet", "data": None}
