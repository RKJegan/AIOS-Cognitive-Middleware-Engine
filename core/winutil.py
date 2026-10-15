"""Window helpers that degrade gracefully when pygetwindow is unavailable."""


def all_windows():
    try:
        import pygetwindow as gw
        return [w for w in gw.getAllWindows() if w.title and w.title.strip()]
    except Exception:
        return []


def find_matching(predicate):
    return [w for w in all_windows() if predicate(w.title.strip().lower())]


def close_matching(predicate):
    closed = 0
    for w in find_matching(predicate):
        try:
            w.close()
            closed += 1
        except Exception:
            continue
    return closed
