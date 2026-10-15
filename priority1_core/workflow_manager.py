import json
from collections import defaultdict
from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate
from core.paths import DATA_DIR
from core.step_executor import StepExecutor
from security.safety_layer import is_workflow_safe

log = get_logger()
WORKFLOWS_PATH = DATA_DIR / "workflows.json"


class WorkflowManager:
    def __init__(self, middleware_core, storage_path=WORKFLOWS_PATH):
        self.middleware_core = middleware_core
        self.executor = StepExecutor(middleware_core)
        self.storage_path = Path(storage_path)
        self.workflows = self._load()
        self.recording = False
        self.recording_name = None
        self.recording_buffer = []
        self.pair_counts = defaultdict(int)
        self.suggested = set()
        self.last_step = None

    def _load(self):
        if not self.storage_path.exists():
            return {}
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.error(f"Failed to load workflows: {e}")
            return {}

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(self.workflows, indent=2), encoding="utf-8")

    def save_workflow(self, name, steps):
        if not name or not steps:
            return {"status": "error", "message": "Workflow needs a name and at least one step", "data": None}
        for i, step in enumerate(steps):
            if not is_workflow_safe(step.get("action")):
                narrate(f"I can't save this, step {i+1} ({step.get('action')}) needs manual confirmation each time.")
                return {"status": "rejected", "message": f"Step {i+1} uses an action too risky to automate", "data": None}
        key = name.lower().strip()
        self.workflows[key] = steps
        self._save()
        narrate(f"Saved workflow {name} with {len(steps)} steps")
        return {"status": "success", "message": f"Saved workflow '{name}'", "data": None}

    def list_workflows(self):
        names = list(self.workflows.keys())
        narrate(f"You have {len(names)} saved workflow(s)" if names else "No workflows saved yet")
        return {"status": "success", "message": f"{len(names)} workflow(s)", "data": names}

    def delete_workflow(self, name):
        key = name.lower().strip()
        if key not in self.workflows:
            return {"status": "not_found", "message": f"No workflow named '{name}'", "data": None}
        del self.workflows[key]
        self._save()
        narrate(f"Deleted workflow {name}")
        return {"status": "success", "message": f"Deleted workflow '{name}'", "data": None}

    def run_workflow(self, name):
        key = name.lower().strip()
        steps = self.workflows.get(key)
        if not steps:
            narrate(f"I don't have a workflow called {name}")
            return {"status": "not_found", "message": f"No workflow named '{name}'", "data": None}
        narrate(f"Starting workflow {name}")
        result = self.executor.execute(steps, policy="stop_on_failure")
        if result["status"] == "success":
            narrate(f"Workflow {name} complete")
        return result

    def start_recording(self, name):
        if not name:
            return {"status": "error", "message": "Give the workflow a name to start recording", "data": None}
        self.recording, self.recording_name, self.recording_buffer = True, name, []
        narrate(f"Recording started. Do your steps, then say stop recording to save as {name}")
        return {"status": "success", "message": f"Recording '{name}'", "data": None}

    def stop_recording(self):
        if not self.recording:
            return {"status": "error", "message": "Not currently recording", "data": None}
        name, steps = self.recording_name, self.recording_buffer
        self.recording, self.recording_name, self.recording_buffer = False, None, []
        if not steps:
            narrate("Nothing was recorded, no steps to save")
            return {"status": "error", "message": "No steps recorded", "data": None}
        return self.save_workflow(name, steps)

    def track_step(self, intent):
        if self.recording:
            self.recording_buffer.append(intent)
        step_key = (intent.get("action"), intent.get("name"))
        if self.last_step is not None:
            pair_key = (self.last_step, step_key)
            self.pair_counts[pair_key] += 1
            if self.pair_counts[pair_key] == 3 and pair_key not in self.suggested:
                self.suggested.add(pair_key)
                narrate(f"You've done '{self.last_step[0]} {self.last_step[1]}' then "
                        f"'{step_key[0]} {step_key[1]}' three times. Say 'start recording' to save it as a workflow.")
        self.last_step = step_key

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action == "run":
            return self.run_workflow(name)
        if action == "list":
            return self.list_workflows()
        if action == "delete":
            return self.delete_workflow(name)
        if action == "record_start":
            return self.start_recording(name)
        if action == "record_stop":
            return self.stop_recording()
        return {"status": "unhandled", "message": f"Workflow action '{action}' not implemented yet", "data": None}
