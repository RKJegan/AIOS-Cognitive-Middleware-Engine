import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate
from core.winutil import find_matching, close_matching
from security.safety_layer import SafetyLayer

log = get_logger()
DEFAULT_LOCATION = "desktop"


class FileController:
    LOCATION_ALIASES = {
        "desktop": Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "downloads": Path.home() / "Downloads",
        "pictures": Path.home() / "Pictures",
        "s drive": Path("S:/"),
    }

    def __init__(self, safety=None):
        self.safety = safety or SafetyLayer()
        self.open_processes = {}

    def _looks_like_path(self, text):
        return Path(text).is_absolute() or "/" in text or "\\" in text

    def _needs_location(self, location_ref):
        narrate(f"I don't know where '{location_ref}' is. Give me a full path or a known location like Desktop.")
        return {"status": "needs_clarification", "message": f"Unresolved location: {location_ref}", "data": None}

    def resolve_location(self, location_ref, name):
        if not location_ref:
            return {"resolved": True, "path": name}
        key = location_ref.strip().lower()
        if key in self.LOCATION_ALIASES:
            return {"resolved": True, "path": str(self.LOCATION_ALIASES[key] / name)}
        if Path(location_ref).is_absolute():
            return {"resolved": True, "path": str(Path(location_ref) / name)}
        return {"resolved": False, "path": None}

    GENERIC_WORDS = {"files", "file", "folder", "folders", "things", "stuff", "everything", "it", "them"}

    @classmethod
    def _strip_generic_suffix(cls, text):
        words = text.split()
        while len(words) > 1 and words[-1].lower() in cls.GENERIC_WORDS:
            words = words[:-1]
        return " ".join(words)

    def resolve_target(self, name, location_ref):
        """
        Figures out the real filesystem path for an EXISTING file/folder the
        LLM described. Handles three shapes:
          1. name is purely generic ("files") + a known location  -> the location itself
          2. name has a real subfolder plus a generic word ("cli_test folder") + a
             known location -> <location>/cli_test
          3. everything else -> the original alias/absolute-path/default logic
        """
        if location_ref:
            loc_key = location_ref.strip().lower()
            base = self.LOCATION_ALIASES.get(loc_key)
            if base and name:
                bare = name.strip().lower()
                if bare in self.GENERIC_WORDS:
                    return True, str(base)
                cleaned = self._strip_generic_suffix(name)
                if cleaned and cleaned.lower() != bare:
                    return True, str(base / cleaned)
            if name:
                r = self.resolve_location(location_ref, name)
                return r["resolved"], r["path"]

        ref = (name or location_ref or "").strip()
        if not ref:
            return False, None
        ref = self._strip_generic_suffix(ref)
        alias = self.LOCATION_ALIASES.get(ref.lower())
        if alias:
            return True, str(alias)
        if self._looks_like_path(ref):
            return True, ref
        return True, str(self.LOCATION_ALIASES[DEFAULT_LOCATION] / ref)

    def resolve_destination(self, dest_ref):
        if not dest_ref:
            return None
        alias = self.LOCATION_ALIASES.get(dest_ref.strip().lower())
        if alias:
            return str(alias)
        if Path(dest_ref).is_absolute():
            return dest_ref
        return None

    def _new_item_path(self, name, location_ref):
        name = self._strip_generic_suffix(name) if name else name
        if not location_ref and self._looks_like_path(name):
            return True, name
        loc = self.resolve_location(location_ref or DEFAULT_LOCATION, name)
        return loc["resolved"], loc["path"]

    def create_folder(self, path):
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            narrate(f"Created folder {path}")
            return {"status": "success", "message": f"Created {path}", "data": {"path": path}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def create_folder_from_intent(self, name, location_ref):
        if not name:
            narrate("What should I name the folder?")
            return {"status": "needs_clarification", "message": "Missing name", "data": None}
        ok, path = self._new_item_path(name, location_ref)
        if not ok:
            return self._needs_location(location_ref)
        check = self.safety.validate("create", path)
        if check["status"] != "approved":
            return check
        return self.create_folder(path)

    def create_file(self, path):
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).touch(exist_ok=True)
            narrate(f"Created file {path}")
            return {"status": "success", "message": f"Created {path}", "data": {"path": path}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def create_file_from_intent(self, name, location_ref):
        if not name:
            narrate("What should I name the file?")
            return {"status": "needs_clarification", "message": "Missing name", "data": None}
        ok, path = self._new_item_path(name, location_ref)
        if not ok:
            return self._needs_location(location_ref)
        check = self.safety.validate("create", path)
        if check["status"] != "approved":
            return check
        return self.create_file(path)

    def delete(self, path):
        check = self.safety.validate("delete", path)
        if check["status"] != "approved":
            return check
        try:
            p = Path(path)
            if not p.exists():
                narrate(f"I couldn't find {path}")
                return {"status": "error", "message": "File or folder not found", "data": None}
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            narrate(f"Deleted {path}")
            return {"status": "success", "message": f"Deleted {path}", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def copy(self, source, destination):
        try:
            shutil.copytree(source, destination) if Path(source).is_dir() else shutil.copy2(source, destination)
            narrate(f"Copied to {destination}")
            return {"status": "success", "message": f"Copied to {destination}", "data": {"path": destination}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def move(self, source, destination):
        try:
            shutil.move(source, destination)
            narrate(f"Moved to {destination}")
            return {"status": "success", "message": f"Moved to {destination}", "data": {"path": destination}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def rename(self, path, new_name):
        try:
            p = Path(path)
            target = p.parent / new_name
            p.rename(target)
            narrate(f"Renamed to {new_name}")
            return {"status": "success", "message": f"Renamed to {new_name}", "data": {"path": str(target)}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def compress(self, path):
        try:
            p = Path(path)
            out = p.with_suffix(".zip")
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                if p.is_dir():
                    for f in p.rglob("*"):
                        if f.is_file():
                            zf.write(f, f.relative_to(p.parent))
                else:
                    zf.write(p, p.name)
            narrate(f"Compressed to {out.name}")
            return {"status": "success", "message": f"Compressed to {out}", "data": {"path": str(out)}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def search(self, name, location_ref):
        root = self.LOCATION_ALIASES.get((location_ref or "").lower(), Path.home())
        try:
            matches = [str(p) for p in Path(root).rglob(f"*{name}*")][:25]
            narrate(f"Found {len(matches)} match(es)")
            return {"status": "success" if matches else "not_found", "message": f"{len(matches)} match(es)", "data": matches}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def list_folder(self, path):
        try:
            items = os.listdir(path)
            narrate(f"Found {len(items)} items")
            return {"status": "success", "message": f"{len(items)} items", "data": items}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def open_path(self, path):
        try:
            proc = subprocess.Popen(["explorer", path])
            time.sleep(1)
            self.open_processes[path.lower()] = proc
            narrate(f"Opening {path}")
            return {"status": "success", "message": f"Opened {path}", "data": {"path": path}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def close_path(self, path):
        check = self.safety.validate("close", path)
        if check["status"] == "blocked":
            return check
        key = path.lower()
        proc = self.open_processes.get(key)
        if proc and proc.poll() is None:
            proc.terminate()
            del self.open_processes[key]
            narrate(f"Closing {path}")
            return {"status": "success", "message": f"Closed {path}", "data": None}
        term = Path(path).name.lower()
        closed = close_matching(lambda t: t.startswith(term))
        self.open_processes.pop(key, None)
        if closed:
            narrate(f"Closing {term}")
            return {"status": "success", "message": f"Closed {closed} window(s)", "data": None}
        return {"status": "not_found", "message": f"'{path}' doesn't appear to be open", "data": None}

    def close_all_windows(self):
        if not self.open_processes:
            return {"status": "not_found", "message": "No folders/files opened this session", "data": None}
        check = self.safety.validate("close_all", "all open folders and files")
        if check["status"] != "approved":
            return check
        closed = sum(1 for path in list(self.open_processes) if self.close_path(path)["status"] == "success")
        narrate(f"Closed {closed} window(s)")
        return {"status": "success", "message": f"Closed {closed} window(s)", "data": None}

    def handle(self, intent):
        action = intent.get("action")
        name = intent.get("name")
        location_ref = intent.get("location_ref")
        dest_ref = intent.get("destination_ref")

        if action == "close_all":
            return self.close_all_windows()
        if action == "create_folder":
            return self.create_folder_from_intent(name, location_ref)
        if action == "create_file":
            return self.create_file_from_intent(name, location_ref)
        if action == "search":
            return self.search(name, location_ref)

        ok, path = self.resolve_target(name, location_ref)
        if not ok:
            return self._needs_location(location_ref) if (name and location_ref) else \
                {"status": "needs_clarification", "message": "Missing target", "data": None}

        if action == "delete":
            return self.delete(path)
        if action == "list_folder":
            return self.list_folder(path)
        if action == "open":
            return self.open_path(path)
        if action == "close":
            return self.close_path(path)
        if action == "compress":
            return self.compress(path)
        if action == "rename":
            if not dest_ref:
                narrate("What should the new name be?")
                return {"status": "needs_clarification", "message": "Missing new name", "data": None}
            return self.rename(path, dest_ref)
        if action in ("copy", "move"):
            dest_dir = self.resolve_destination(dest_ref)
            if not dest_dir:
                narrate("Where should I put it? Give a full path or a known location.")
                return {"status": "needs_clarification", "message": "Missing or unknown destination", "data": None}
            target = str(Path(dest_dir) / Path(path).name)
            return self.copy(path, target) if action == "copy" else self.move(path, target)
        return {"status": "unhandled", "message": f"File action '{action}' not implemented yet", "data": None}

    def verify_exists(self, intent, result):
        if result.get("status") != "success":
            return None
        path = (result.get("data") or {}).get("path")
        return Path(path).exists() if path else None
