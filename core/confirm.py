"""Pluggable yes/no confirmation. main.py installs a handler that cooperates with the input hub."""
_handler = None


def set_handler(fn):
    global _handler
    _handler = fn


def ask(prompt):
    if _handler is not None:
        return bool(_handler(prompt))
    return input(f"{prompt} Type YES to confirm: ").strip().upper() == "YES"
