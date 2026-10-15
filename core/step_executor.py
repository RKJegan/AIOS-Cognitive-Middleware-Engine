from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


def _label(step):
    return f"{step.get('action')} {step.get('name') or ''}".strip()


class StepExecutor:
    """Plan -> Execute -> Verify -> Report for a list of atomic intents."""

    def __init__(self, middleware_core):
        self.core = middleware_core

    def execute(self, steps, policy="continue_on_failure"):
        if not steps:
            return {"status": "error", "message": "No steps to execute", "data": None}

        if len(steps) > 1:
            narrate(f"Doing {len(steps)} things: " + ", ".join(_label(s) for s in steps))

        results = []
        for i, step in enumerate(steps):
            result = self.core.route(step)

            if result.get("status") == "success":
                if self.core.verify(step, result) is False:
                    result = {
                        "status": "unverified",
                        "message": f"{result.get('message')} (could not confirm it took effect)",
                        "data": result.get("data"),
                    }
                    narrate(f"I ran that, but couldn't confirm it worked: {_label(step)}")

            results.append(result)
            log.info(f"Step {i+1}/{len(steps)} [{_label(step)}] -> {result.get('status')}")

            if policy == "stop_on_failure" and result.get("status") != "success":
                narrate(f"Stopped at step {i+1}: {result.get('message')}")
                return {
                    "status": "error",
                    "message": f"Stopped at step {i+1}/{len(steps)}: {result.get('message')}",
                    "data": {"completed": i, "total": len(steps), "results": results},
                }

        ok = sum(1 for r in results if r.get("status") == "success")
        status = "success" if ok == len(steps) else "partial" if ok > 0 else "error"
        if len(steps) > 1:
            narrate(f"Finished {ok} of {len(steps)} steps")
        return {"status": status, "message": f"{ok}/{len(steps)} step(s) succeeded",
                "data": {"completed": ok, "total": len(steps), "results": results}}
