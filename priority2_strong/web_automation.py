"""Page-level automation (click/fill/read/screenshot) via Playwright, on a SEPARATE
disposable profile at data/automation_profile/ — never your real signed-in browser.
Use priority1_core/browser_controller.py instead when you just want to open a page
in your normal, logged-in browser.
"""
from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate
from core.paths import DATA_DIR

log = get_logger()
PROFILE_DIR = DATA_DIR / "automation_profile"


class WebAutomation:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None

    def _ensure_started(self):
        if self.context is not None:
            return
        from playwright.sync_api import sync_playwright
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        log.info(f"Automation browser started at {PROFILE_DIR}")

    def goto(self, url):
        try:
            self._ensure_started()
            if not url.startswith("http"):
                url = "https://" + url
            self.page.goto(url, timeout=20000)
            narrate(f"Opened {url} in the automation browser")
            return {"status": "success", "message": f"Opened {url}", "data": {"url": url}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def click(self, text):
        try:
            self._ensure_started()
            self.page.get_by_text(text, exact=False).first.click(timeout=8000)
            narrate(f"Clicked {text}")
            return {"status": "success", "message": f"Clicked '{text}'", "data": None}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't find/click '{text}': {e}", "data": None}

    def fill(self, target, value):
        try:
            self._ensure_started()
            locator = self.page.get_by_placeholder(target, exact=False)
            if locator.count() == 0:
                locator = self.page.get_by_label(target, exact=False)
            locator.first.fill(value, timeout=8000)
            narrate(f"Typed into {target}")
            return {"status": "success", "message": f"Filled '{target}'", "data": None}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't find field '{target}': {e}", "data": None}

    def press(self, key):
        try:
            self._ensure_started()
            self.page.keyboard.press(key.capitalize() if len(key) > 1 else key)
            narrate(f"Pressed {key}")
            return {"status": "success", "message": f"Pressed '{key}'", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def scroll(self, direction):
        try:
            self._ensure_started()
            dy = 600 if (direction or "down").lower() == "down" else -600
            self.page.mouse.wheel(0, dy)
            narrate(f"Scrolled {direction}")
            return {"status": "success", "message": f"Scrolled {direction}", "data": None}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def read_page(self):
        try:
            self._ensure_started()
            text = self.page.inner_text("body")[:3000]
            narrate("Read the page")
            return {"status": "success", "message": "Read page text", "data": {"text": text}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def screenshot(self):
        try:
            self._ensure_started()
            out = DATA_DIR / "page_screenshot.png"
            self.page.screenshot(path=str(out))
            narrate("Screenshot saved")
            return {"status": "success", "message": f"Saved {out}", "data": {"path": str(out)}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def close(self):
        if self.context:
            try:
                self.context.close()
                self.playwright.stop()
            except Exception:
                pass
            self.context = None
            self.playwright = None

    def handle(self, intent):
        action = intent.get("action")
        name, dest = intent.get("name"), intent.get("destination_ref")
        if action == "goto":
            return self.goto(name)
        if action == "click":
            return self.click(name)
        if action == "fill":
            return self.fill(name, dest or "")
        if action == "press":
            return self.press(name or "Enter")
        if action == "scroll":
            return self.scroll(name)
        if action == "read_page":
            return self.read_page()
        if action == "screenshot":
            return self.screenshot()
        if action == "close":
            self.close()
            return {"status": "success", "message": "Automation browser closed", "data": None}
        return {"status": "unhandled", "message": f"Web automation action '{action}' not implemented yet", "data": None}
