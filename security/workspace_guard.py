"""Folder jail for the Code Agent: canonical paths, no traversal, no symlink escape, no secrets."""
import hashlib
import os
import re
from pathlib import Path

SENSITIVE_NAME_PATTERNS = [
    r"^\.env(\..*)?$", r"^id_(rsa|ed25519|ecdsa|dsa)(\.pub)?$", r".*\.(pem|key|pfx|p12|ppk|kdbx)$",
    r"^credentials(\..*)?$", r"^secrets?(\..*)?$", r".*token.*", r"^\.netrc$", r"^\.npmrc$", r"^\.pypirc$",
]
SENSITIVE_DIRS = {".ssh", ".aws", ".gnupg", ".azure", ".kube"}
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__"}
FORBIDDEN_ROOTS = [r"c:\windows", r"c:\program files", r"c:\program files (x86)", r"c:\programdata"]


class WorkspaceError(Exception):
    pass


def _is_within(child, parent):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


class WorkspaceGuard:
    def __init__(self, root, project_root=None):
        self.root = self.validate_root(root, project_root)

    @staticmethod
    def validate_root(root, project_root=None):
        p = Path(root).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            raise WorkspaceError(f"'{root}' is not an existing folder")
        if p == Path(p.anchor):
            raise WorkspaceError("A drive root can't be a workspace")
        if p == Path.home().resolve():
            raise WorkspaceError("Your whole home folder can't be a workspace")
        low = str(p).lower().replace("/", "\\")
        for f in FORBIDDEN_ROOTS:
            if low == f or low.startswith(f + "\\"):
                raise WorkspaceError("System folders can't be a workspace")
        if project_root:
            pr = Path(project_root).resolve()
            if pr == p or _is_within(pr, p):
                raise WorkspaceError("Workspace may not contain the assistant's own code")
        return p

    @staticmethod
    def is_sensitive(path):
        p = Path(path)
        if any(part.lower() in SENSITIVE_DIRS for part in p.parts):
            return True
        return any(re.match(pat, p.name, re.IGNORECASE) for pat in SENSITIVE_NAME_PATTERNS)

    def resolve(self, candidate):
        p = Path(candidate)
        if not p.is_absolute():
            p = self.root / p
        resolved = p.resolve()
        if not _is_within(resolved, self.root):
            raise WorkspaceError(f"'{candidate}' is outside the approved workspace")
        if self.is_sensitive(resolved):
            raise WorkspaceError(f"'{resolved.name}' looks like a secret file and is blocked")
        return resolved

    def snapshot(self):
        snap, escaped = {}, []
        for dirpath, dirnames, filenames in os.walk(self.root, followlinks=False):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                full = Path(dirpath) / name
                rel = str(full.relative_to(self.root))
                try:
                    if not _is_within(full.resolve(), self.root):
                        escaped.append(rel)
                        continue
                    st = full.stat()
                    digest = ""
                    if st.st_size <= 2_000_000:
                        digest = hashlib.sha256(full.read_bytes()).hexdigest()
                    snap[rel] = (st.st_size, digest)
                except OSError:
                    continue
        snap["__escaped__"] = escaped
        return snap

    @staticmethod
    def diff(before, after):
        b = {k: v for k, v in before.items() if k != "__escaped__"}
        a = {k: v for k, v in after.items() if k != "__escaped__"}
        return {
            "added": sorted(set(a) - set(b)),
            "deleted": sorted(set(b) - set(a)),
            "modified": sorted(k for k in a if k in b and a[k] != b[k]),
            "escaped_links": sorted(after.get("__escaped__", [])),
        }

    def flag_sensitive(self, diff):
        touched = diff["added"] + diff["modified"] + diff["deleted"]
        return [f for f in touched if self.is_sensitive(f)]
