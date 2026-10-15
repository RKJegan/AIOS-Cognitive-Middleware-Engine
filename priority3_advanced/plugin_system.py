"""Drop a *_plugin.py file into /plugins. It needs PLUGIN_NAME, ACTIONS (a set) and handle(intent)."""
import importlib.util
from core.logger import get_logger
from core.paths import PROJECT_ROOT

log = get_logger()


class PluginSystem:
    def __init__(self, plugin_dir=None):
        self.plugin_dir = plugin_dir or PROJECT_ROOT / "plugins"
        self.plugins = []

    def load(self):
        self.plugins = []
        if not self.plugin_dir.is_dir():
            return self.plugins
        for f in sorted(self.plugin_dir.glob("*_plugin.py")):
            try:
                spec = importlib.util.spec_from_file_location(f.stem, f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if all(hasattr(mod, a) for a in ("PLUGIN_NAME", "ACTIONS", "handle")):
                    self.plugins.append(mod)
                    log.info(f"Loaded plugin: {mod.PLUGIN_NAME}")
                else:
                    log.warning(f"Plugin {f.name} is missing PLUGIN_NAME / ACTIONS / handle")
            except Exception as e:
                log.error(f"Plugin {f.name} failed to load: {e}")
        return self.plugins

    def handle(self, intent):
        action = intent.get("action")
        if action == "list_plugins":
            return {"status": "success", "message": "Plugins", "data": [p.PLUGIN_NAME for p in self.plugins]}
        for plugin in self.plugins:
            if action in plugin.ACTIONS:
                try:
                    return plugin.handle(intent)
                except Exception as e:
                    log.error(f"Plugin {plugin.PLUGIN_NAME} crashed: {e}")
                    return {"status": "error", "message": f"{plugin.PLUGIN_NAME} failed: {e}", "data": None}
        return {"status": "unhandled", "message": f"No plugin handles '{action}'", "data": None}
