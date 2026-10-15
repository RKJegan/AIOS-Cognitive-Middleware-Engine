from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


class MultiMonitor:
    def list_monitors(self):
        try:
            import screeninfo
            mons = screeninfo.get_monitors()
            data = [{"index": i, "width": m.width, "height": m.height, "primary": m.is_primary}
                    for i, m in enumerate(mons)]
            narrate(f"{len(data)} monitor(s) detected")
            return {"status": "success", "message": f"{len(data)} monitor(s)", "data": data}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't list monitors (install screeninfo): {e}", "data": None}

    def move_window(self, app_name, target_desc):
        try:
            import pygetwindow as gw
            import screeninfo
            mons = screeninfo.get_monitors()
            idx = 1 if "second" in (target_desc or "").lower() else 0
            if idx >= len(mons):
                return {"status": "error", "message": "That monitor doesn't exist", "data": None}
            mon = mons[idx]
            matches = [w for w in gw.getAllWindows() if app_name.lower() in w.title.lower()]
            if not matches:
                return {"status": "not_found", "message": f"No window matching '{app_name}'", "data": None}
            matches[0].moveTo(mon.x + 50, mon.y + 50)
            narrate(f"Moved {app_name} to monitor {idx+1}")
            return {"status": "success", "message": f"Moved to monitor {idx+1}", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def handle(self, intent):
        action, name, dest = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        if action == "list":
            return self.list_monitors()
        if action == "move_window":
            return self.move_window(name, dest)
        return {"status": "unhandled", "message": f"Multi-monitor action '{action}' not implemented yet", "data": None}
