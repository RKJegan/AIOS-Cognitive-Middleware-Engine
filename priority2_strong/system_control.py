"""Volume, brightness, lock, shutdown, dark mode. Degrades to a clear error if a lib is missing."""
import subprocess
from core.logger import get_logger
from core.narrator import narrate
from security.safety_layer import SafetyLayer
from priority2_strong.volume_backend import get_volume_scalar, set_volume_scalar, set_mute

log = get_logger()


class SystemControl:
    def __init__(self, safety=None):
        self.safety = safety or SafetyLayer()

    def set_volume(self, value):
        try:
            pct = max(0, min(100, int(str(value).strip().rstrip("%"))))
            set_volume_scalar(pct / 100)
            narrate(f"Volume set to {pct}%")
            return {"status": "success", "message": f"Volume set to {pct}%", "data": {"volume": pct}}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't set volume: {e}", "data": None}

    def volume_step(self, delta):
        try:
            new = max(0.0, min(1.0, get_volume_scalar() + delta))
            set_volume_scalar(new)
            narrate(f"Volume {'up' if delta > 0 else 'down'}")
            return {"status": "success", "message": f"Volume now {round(new*100)}%", "data": {"volume": round(new*100)}}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't change volume: {e}", "data": None}

    def mute(self, muted=True):
        try:
            set_mute(muted)
            narrate("Muted" if muted else "Unmuted")
            return {"status": "success", "message": "Muted" if muted else "Unmuted", "data": None}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't mute: {e}", "data": None}

    def set_brightness(self, value):
        try:
            import screen_brightness_control as sbc
            pct = max(0, min(100, int(str(value).strip().rstrip("%"))))
            sbc.set_brightness(pct)
            narrate(f"Brightness set to {pct}%")
            return {"status": "success", "message": f"Brightness set to {pct}%", "data": {"brightness": pct}}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't set brightness (install screen_brightness_control): {e}", "data": None}

    def lock(self):
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            narrate("Locking screen")
            return {"status": "success", "message": "Screen locked", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def shutdown(self):
        check = self.safety.validate("shutdown", "this computer")
        if check["status"] != "approved":
            return check
        try:
            subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
            narrate("Shutting down in 30 seconds. Say cancel shutdown to stop it.")
            return {"status": "success", "message": "Shutdown scheduled in 30s", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def cancel_shutdown(self):
        try:
            subprocess.run(["shutdown", "/a"], check=True)
            narrate("Shutdown cancelled")
            return {"status": "success", "message": "Shutdown cancelled", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def dark_mode(self, on=True):
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0 if on else 1)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0 if on else 1)
            narrate("Dark mode on" if on else "Dark mode off")
            return {"status": "success", "message": "Dark mode toggled", "data": {"dark": on}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def handle(self, intent):
        action, name = intent.get("action"), intent.get("name")
        if action == "set_volume":
            return self.set_volume(name)
        if action == "volume_up":
            return self.volume_step(0.1)
        if action == "volume_down":
            return self.volume_step(-0.1)
        if action == "mute":
            return self.mute(True)
        if action == "unmute":
            return self.mute(False)
        if action == "set_brightness":
            return self.set_brightness(name)
        if action == "lock":
            return self.lock()
        if action == "shutdown":
            return self.shutdown()
        if action == "cancel_shutdown":
            return self.cancel_shutdown()
        if action == "dark_mode":
            return self.dark_mode((name or "on").lower() != "off")
        return {"status": "unhandled", "message": f"System control action '{action}' not implemented yet", "data": None}
