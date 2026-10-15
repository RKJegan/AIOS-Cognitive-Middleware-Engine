"""OS-level browser control: launches your REAL browser (real profile, real logins).
Chrome 136+ blocks automation tools from attaching to a real signed-in profile, so this
deliberately does NOT use Playwright. For page automation (click/fill/read) see
priority2_strong/web_automation.py, which uses Playwright on a SEPARATE disposable profile.
"""
import subprocess
import time
from pathlib import Path
from urllib.parse import quote_plus
import psutil
from core.logger import get_logger
from core.narrator import narrate
from core.winutil import close_matching
from security.safety_layer import SafetyLayer

log = get_logger()

BROWSER_EXES = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
}
WINDOW_TITLE_SUFFIX = {"chrome": "google chrome", "edge": "edge", "brave": "brave"}
GENERIC_BROWSER_WORDS = {"browser", "web browser", "the browser", "internet", "web"}
KNOWN_SITES = {
    "youtube": "youtube.com", "github": "github.com", "gmail": "mail.google.com",
    "whatsapp web": "web.whatsapp.com", "linkedin": "linkedin.com",
    "chatgpt": "chatgpt.com", "claude": "claude.ai",
}


class BrowserController:
    def __init__(self, settings=None, browser_name=None, safety=None):
        self.settings = settings
        self.safety = safety or SafetyLayer()
        self.browser_name = (browser_name or (settings.default_browser if settings else "chrome")).lower()

    def _exe(self):
        return BROWSER_EXES.get(self.browser_name, BROWSER_EXES["chrome"])

    def _is_running(self):
        exe = Path(self._exe()).name.lower()
        return any((p.info.get("name") or "").lower() == exe for p in psutil.process_iter(["name"]))

    def _launch(self, url=None):
        exe = self._exe()
        if not Path(exe).exists():
            raise FileNotFoundError(f"{self.browser_name} not found at {exe}")
        subprocess.Popen([exe] + ([url] if url else []))

    def _to_url(self, text):
        t = (text or "").strip()
        key = t.lower()
        if key in KNOWN_SITES:
            return "https://" + KNOWN_SITES[key]
        if t.startswith("http"):
            return t
        if "." in t and " " not in t:
            return "https://" + t
        return None

    def open_browser(self):
        try:
            if self._is_running():
                narrate(f"{self.browser_name} is already open")
            else:
                self._launch()
                narrate(f"Opening {self.browser_name}")
            return {"status": "success", "message": f"{self.browser_name} ready", "data": {"browser": self.browser_name}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def _open(self, url):
        try:
            if not self._is_running():
                self._launch()
                time.sleep(2)
            self._launch(url)
            narrate(f"Opening {url}")
            return {"status": "success", "message": f"Opened {url}", "data": {"browser": self.browser_name, "url": url}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def open_url(self, text):
        url = self._to_url(text)
        return self.search_google(text) if url is None else self._open(url)

    def search_google(self, query):
        return self._open(f"https://www.google.com/search?q={quote_plus(query or '')}")

    def close_windows(self):
        suffix = WINDOW_TITLE_SUFFIX.get(self.browser_name, self.browser_name)
        check = self.safety.validate("close_all", f"all {self.browser_name} windows")
        if check["status"] != "approved":
            return check
        closed = close_matching(lambda t: t.endswith(suffix))
        if not closed:
            return {"status": "not_found", "message": f"No {self.browser_name} windows open", "data": None}
        narrate(f"Closed {closed} {self.browser_name} window(s)")
        return {"status": "success", "message": f"Closed {closed} window(s)", "data": None}

    def close(self):
        """No-op: a real browser window shouldn't vanish just because the assistant exits."""
        return None

    def handle(self, intent):
        action = intent.get("action")
        name = intent.get("name")
        location_ref = intent.get("location_ref")

        if location_ref:
            wanted = location_ref.lower().strip()
            if wanted in BROWSER_EXES and wanted != self.browser_name:
                self.browser_name = wanted
                log.info(f"Switched browser to: {wanted}")

        if action == "open" and (not name or name.lower().strip() in BROWSER_EXES or name.lower().strip() in GENERIC_BROWSER_WORDS):
            return self.open_browser()
        if action in ("open", "open_url"):
            return self.open_url(name)
        if action == "search":
            return self.search_google(name)
        if action in ("close", "close_all"):
            return self.close_windows()
        return {"status": "unhandled", "message": f"Browser action '{action}' not implemented yet", "data": None}
