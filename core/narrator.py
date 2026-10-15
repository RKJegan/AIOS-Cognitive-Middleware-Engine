"""One narrate() for the whole project: console + (optionally) HUD overlay + speech."""
_sinks = []


def add_sink(fn):
    """fn(message, speak) is called for every narration."""
    _sinks.append(fn)


def clear_sinks():
    _sinks.clear()


def narrate(message, speak=True):
    print(message)
    for sink in list(_sinks):
        try:
            sink(message, speak)
        except Exception:
            pass
