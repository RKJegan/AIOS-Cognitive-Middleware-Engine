"""Global keyboard shortcut trigger. Degrades to 'unavailable' (e.g. no admin rights) cleanly."""
from core.logger import get_logger

log = get_logger()
DEFAULT_HOTKEY = "ctrl+shift+space"


def start_hotkey_listener(on_trigger, hotkey=DEFAULT_HOTKEY):
    try:
        import keyboard
        keyboard.add_hotkey(hotkey, on_trigger)
        log.info(f"Hotkey listener active: {hotkey}")
        return True
    except Exception as e:
        log.warning(f"Hotkey listener unavailable ({e}); keyboard shortcut will not work")
        return False
