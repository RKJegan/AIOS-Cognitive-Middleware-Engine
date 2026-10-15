"""
Playwright on a SEPARATE, disposable automation profile - never the user's real browser.
Runs on one dedicated worker thread because sync Playwright objects are thread-bound.
Confirms before clicking/filling anything containing a risky word (pay, buy, delete, submit...).
"""
import queue
import threading
from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate
from core.confirm import ask as confirm_ask
from core.paths import DATA_DIR

log = get_logger()

PROFILE_DIR = DATA_DIR / "automation_profile"
RISKY_WORDS = {"pay", "buy", "purchase", "delete", "remove", "submit", "confirm", "checkout", "transfer"}


class _Worker(threading.Thread):
    """Owns the single Playwright/browser/page objects. All calls are marshalled through run()."""

    def __init__(self):
        super().__init__(daemon=True)
        self.jobs = queue.Queue()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.start()

    def run(self):
        while True:
            fn, result_box, done = self.jobs.get()
            try:
                result_box["value"] = fn(self)
            except Exception as e:
                result_box["error"] = str(e)
            done.set()

    def call(self, fn, timeout=30):
        box, done = {}, threading.Event()
        self.jobs.put((fn, box, done))
        if not done.wait(timeout):
            return {"status": "error", "message": "Automation timed out", "data": None}
        if "error" in box:
            return {"status": "error", "message": box["error"], "data": None}
        return box["value"]


class WebAutomation:
    def __init__(self):
        self._worker = None

    def _get_worker(self):
        if self._worker is None:
            self._worker = _Worker()
        return self._worker

    def _ensure_page(self, w):
        if w.page is not None:
            return
        from playwright.sync_api import sync_playwright
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        w.playwright = sync_playwright().start()
        w.context = w.playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        w.page = w.context.pages[0] if w.context.pages else w.context.new_page()
        log.info(f"Automation browser started on disposable profile: {PROFILE_DIR}")

    def goto(self, url):
        if not url.startswith("http"):
            url = "https://" + url

        def job(w):
            self._ensure_page(w)
            w.page.goto(url, wait_until="domcontentloaded")
            return {"status": "success", "message": f"Opened {url}", "data": None}

        narrate(f"Opening {url} in the automation browser")
        return self._get_worker().call(job)

    def read_page(self):
        def job(w):
            if w.page is None:
                return {"status": "error", "message": "No page open yet", "data": None}
            text = w.page.inner_text("body")[:3000]
            return {"status": "success", "message": "Read page text", "data": {"text": text}}
        return self._get_worker().call(job)

    def click(self, text):
        if any(risky in (text or "").lower() for risky in RISKY_WORDS):
            if not confirm_ask(f"The automation browser wants to click '{text}', which looks risky."):
                return {"status": "cancelled", "message": "User did not confirm", "data": None}

        def job(w):
            if w.page is None:
                return {"status": "error", "message": "No page open yet", "data": None}
            w.page.get_by_text(text, exact=False).first.click(timeout=5000)
            return {"status": "success", "message": f"Clicked '{text}'", "data": None}

        narrate(f"Clicking {text}")
        return self._get_worker().call(job)

    def fill(self, field_label, value):
        def job(w):
            if w.page is None:
                return {"status": "error", "message": "No page open yet", "data": None}
            locator = w.page.get_by_label(field_label, exact=False)
            if locator.count() == 0:
                locator = w.page.get_by_placeholder(field_label, exact=False)
            locator.first.fill(value, timeout=5000)
            return {"status": "success", "message": f"Typed into '{field_label}'", "data": None}

        narrate(f"Typing into {field_label}")
        return self._get_worker().call(job)

    def press(self, key):
        def job(w):
            if w.page is None:
                return {"status": "error", "message": "No page open yet", "data": None}
            w.page.keyboard.press(key.capitalize())
            return {"status": "success", "message": f"Pressed {key}", "data": None}
        return self._get_worker().call(job)

    def scroll(self, direction):
        dy = 600 if "down" in (direction or "").lower() else -600

        def job(w):
            if w.page is None:
                return {"status": "error", "message": "No page open yet", "data": None}
            w.page.mouse.wheel(0, dy)
            return {"status": "success", "message": f"Scrolled {direction}", "data": None}
        return self._get_worker().call(job)

    def screenshot(self):
        def job(w):
            if w.page is None:
                return {"status": "error", "message": "No page open yet", "data": None}
            out = DATA_DIR / "web_screenshot.png"
            w.page.screenshot(path=str(out))
            return {"status": "success", "message": f"Saved {out}", "data": {"path": str(out)}}

        narrate("Taking a screenshot of the page")
        return self._get_worker().call(job)

    def close(self):
        def job(w):
            if w.context:
                w.context.close()
            if w.playwright:
                w.playwright.stop()
            w.page = w.context = w.playwright = None
            return {"status": "success", "message": "Automation browser closed", "data": None}

        if self._worker is None:
            return {"status": "not_found", "message": "Automation browser was not open", "data": None}
        narrate("Closing the automation browser")
        return self._get_worker().call(job)

    def handle(self, intent):
        action, name, dest = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        if action == "goto":
            return self.goto(name)
        if action == "read_page":
            return self.read_page()
        if action == "click":
            return self.click(name)
        if action == "fill":
            return self.fill(name, dest or "")
        if action == "press":
            return self.press(name or "enter")
        if action == "scroll":
            return self.scroll(name or "down")
        if action == "screenshot":
            return self.screenshot()
        if action == "close":
            return self.close()
        return {"status": "unhandled", "message": f"Web automation action '{action}' not implemented yet", "data": None}
