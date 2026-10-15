"""Auto-discovers plugin_*.py files in this folder; each exposes PLUGIN_ACTIONS = {action: fn}."""
import importlib
import pkgutil
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


class PluginSystem:
    def __init__(self):
        self.actions = {}
        self._load()

    def _load(self):
        import plugins
        for _, name, _ in pkgutil.iter_modules(plugins.__path__):
            if not name.startswith("plugin_"):
                continue
            try:
                mod = importlib.import_module(f"plugins.{name}")
                self.actions.update(getattr(mod, "PLUGIN_ACTIONS", {}))
                log.info(f"Loaded plugin: {name}")
            except Exception as e:
                log.error(f"Failed to load plugin {name}: {e}")

    def handle(self, intent):
        action = intent.get("action")
        fn = self.actions.get(action)
        if not fn:
            return {"status": "unhandled", "message": f"No plugin handles '{action}'", "data": None}
        try:
            return fn(intent)
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}
