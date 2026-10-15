"""The single source of truth for which (category, action) pairs exist, plus the safety nets
that turn a model's near-miss into the exact string our handlers check for."""
import difflib

ACTION_VOCAB = {
    "app_control": ["open", "close", "close_all", "uninstall"],
    "file_operation": ["create_folder", "create_file", "delete", "copy", "move", "rename", "compress",
                       "search", "list_folder", "open", "close", "close_all"],
    "browser_action": ["open", "open_url", "search", "close", "close_all"],
    "web_automation": ["goto", "click", "fill", "press", "scroll", "read_page", "screenshot", "close"],
    "system_monitor": ["status", "top_processes"],
    "system_control": ["set_volume", "volume_up", "volume_down", "mute", "unmute", "set_brightness",
                       "lock", "shutdown", "cancel_shutdown", "dark_mode"],
    "process_management": ["list", "find", "kill", "restart", "end_all"],
    "workflow": ["run", "list", "delete", "record_start", "record_stop"],
    "scheduling": ["schedule", "list", "cancel"],
    "notification": ["notify", "remind"],
    "clipboard": ["copy", "paste", "history", "select", "clear"],
    "screenshot": ["screenshot", "read_screen", "ocr_file"],
    "developer_operation": ["git_status", "git_commit", "git_push", "git_pull", "create_venv",
                            "install_package", "run_command"],
    "email": ["send", "read"],
    "document": ["read", "search_in"],
    "text_assistant": ["summarize", "translate", "draft", "explain"],
    "memory": ["remember", "recall", "forget", "history", "set_pref"],
    "plugin": ["calculate", "time"],
    "multi_monitor": ["list", "move_window"],
    "code_agent": ["set_workspace", "write_code"],
}

# Never reached by fuzzy/prefix guessing - only by an exact match or an explicit alias.
NO_GUESS = {"delete", "uninstall", "shutdown", "kill", "close_all", "end_all", "send", "git_push",
            "install_package", "restart"}

# action the model might say -> [(only_if_model_category_is | None, category, action)]
ALIASES = {
    "mute_sound": [(None, "system_control", "mute")],
    "set_theme": [(None, "system_control", "dark_mode")],
    "retrieve": [(None, "memory", "recall")],
    "show_history": [(None, "clipboard", "history")],
    "show": [("memory", "memory", "history"), ("notification", "notification", "notify"),
             ("clipboard", "clipboard", "history")],
    "display": [(None, "notification", "notify")],
    "status": [("clipboard", "clipboard", "paste")],
    "read_text": [(None, "screenshot", "read_screen")],
    "create_virtual_environment": [(None, "developer_operation", "create_venv")],
    "install": [(None, "developer_operation", "install_package")],
    "list": [("file_operation", "file_operation", "list_folder")],
    "kill_process": [(None, "process_management", "kill")],
    "compose": [(None, "text_assistant", "draft")],
    "get": [("system_monitor", "system_monitor", "status")],
    "stop_recording": [(None, "workflow", "record_stop")],
    "start_recording": [(None, "workflow", "record_start")],
    "new_folder": [(None, "file_operation", "create_folder")],
    "new_file": [(None, "file_operation", "create_file")],
    "browse": [(None, "browser_action", "open_url")],
    "launch": [("app_control", "app_control", "open")],
    "quit": [("app_control", "app_control", "close")],
    "exit": [("app_control", "app_control", "close")],
    "end": [("process_management", "process_management", "kill")],
    "set_volume_level": [(None, "system_control", "set_volume")],
    "increase_volume": [(None, "system_control", "volume_up")],
    "decrease_volume": [(None, "system_control", "volume_down")],
}

# Risky actions need the user's own words to actually mention them (guards against noisy audio).
REQUIRES_WORDS = {
    "shutdown": ("shut", "power off", "turn off"),
    "cancel_shutdown": ("shut", "cancel", "abort"),
    "restart": ("restart", "reboot"),
    "lock": ("lock",),
    "uninstall": ("uninstall", "remove"),
    "delete": ("delete", "remove", "erase", "trash", "get rid"),
    "send": ("send", "email", "mail"),
    "git_push": ("push",),
    "install_package": ("install",),
    "kill": ("kill", "end", "terminate", "stop", "close"),
}

FILE_HINT = (".pdf", ".docx", ".txt", ".md", ".doc")


def _all_actions():
    return {a for acts in ACTION_VOCAB.values() for a in acts}


def _tiebreak(action, intent, candidates):
    name = (intent.get("name") or "").lower()
    if action == "read":
        if any(h in name for h in FILE_HINT) or intent.get("location_ref"):
            return "document"
        return "email"
    if action == "search":
        if any(h in name for h in FILE_HINT) or intent.get("location_ref") in ("documents", "desktop", "downloads"):
            return "file_operation"
        return "browser_action"
    if action in ("close", "open"):
        return None
    return None


def normalize(intent, spoken_text=None):
    """Return (intent, note). note is '' if untouched, else a short description of the correction."""
    out = dict(intent)
    cat = (out.get("intent") or "unknown")
    act = out.get("action")
    text = (spoken_text or out.get("raw_text") or "").lower()

    def unknown(why):
        out.update({"intent": "unknown", "action": None})
        return out, why

    if not act or act == "unknown":
        return unknown("no action")
    act = str(act).strip().lower().replace(" ", "_")
    out["action"] = act

    # words guard for risky actions (checked after possible correction below as well)
    def guarded(final_action):
        words = REQUIRES_WORDS.get(final_action)
        return bool(words) and text and not any(w in text for w in words)

    if act in ACTION_VOCAB.get(cat, []):
        if guarded(act):
            return unknown(f"'{act}' not mentioned in what was said")
        return out, ""

    for hint, tcat, tact in ALIASES.get(act, []):
        if hint is None or hint == cat:
            out.update({"intent": tcat, "action": tact})
            if guarded(tact):
                return unknown(f"'{tact}' not mentioned in what was said")
            return out, f"alias {cat}/{act} -> {tcat}/{tact}"

    cands = [c for c, acts in ACTION_VOCAB.items() if act in acts]
    if len(cands) == 1:
        out["intent"] = cands[0]
    elif len(cands) > 1:
        pick = _tiebreak(act, out, cands)
        if pick in cands:
            out["intent"] = pick
        else:
            return unknown(f"'{act}' is ambiguous")
    if cands:
        if guarded(act):
            return unknown(f"'{act}' not mentioned in what was said")
        return out, f"category {cat} -> {out['intent']} for '{act}'"

    # prefix / fuzzy guessing (never for risky actions)
    pool = ACTION_VOCAB.get(cat, [])
    pref = [a for a in pool if (a.startswith(act) or act.startswith(a)) and a not in NO_GUESS]
    if len(pref) == 1:
        out["action"] = pref[0]
        return out, f"prefix {act} -> {pref[0]}"
    pref_all = [(c, a) for c, acts in ACTION_VOCAB.items() for a in acts
                if (a.startswith(act) or act.startswith(a)) and a not in NO_GUESS and len(act) >= 4]
    if len({a for _, a in pref_all}) == 1 and pref_all:
        out.update({"intent": pref_all[0][0], "action": pref_all[0][1]})
        return out, f"prefix {act} -> {pref_all[0][0]}/{pref_all[0][1]}"
    close = difflib.get_close_matches(act, [a for a in pool if a not in NO_GUESS], n=1, cutoff=0.85)
    if close:
        out["action"] = close[0]
        return out, f"fuzzy {act} -> {close[0]}"

    return unknown(f"'{act}' is not a known action")
