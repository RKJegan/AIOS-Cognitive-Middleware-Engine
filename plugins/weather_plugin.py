"""Example plugin — stub (no API key configured). Shows the plugin contract."""
def weather(name, loc, dest):
    return f"Weather lookup for '{name or 'here'}' needs an API key — not configured."

PLUGIN = {"weather": weather}
