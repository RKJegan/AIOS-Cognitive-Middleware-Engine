"""Playwright automation on a SEPARATE disposable profile (data/automation_profile).
It never touches your real signed-in browser. Log into sites once inside this window and the
profile remembers you. All Playwright calls run on ONE worker thread (sync API is thread-bound)."""
import queue
import threading
from datetime import datetime
from core.logger import get_logger
from core.narrator import narrate
from core.paths import DATA_DIR
from priority1_core.browser_controller import to_url
from security.safety_layer import SafetyLayer

log = get_logger()

PROFILE_DIR = DATA_DIR / "automation_profile"
SHOT_DIR = DATA_DIR / "screenshots"
RISKY_WORDS = ("delete", "remove", "pay", "buy", "purchase", "checkout", "place order",
               "confirm", "transfer", "send", "submit", "unsubscribe", "cancel subscription")
KEY_MAP = {"enter": "Enter", "return": "Enter", "tab": "Tab", "escape": "Escape", "esc": "Escape",
           "space": "Space", "backspace": "Backspace", "down": "ArrowDown", "up": "ArrowUp"}


def is_risky_click(text):
    t = (text or "").lower()
    return any(w in t for w in RISKY_WORDS)


class _Worker:
    def __init__(self):
        self.q = queue.Queue()
        self.thread = None

    def _loop(self):
        while True:
            fn, box, done = self.q.get()
            try:
                box["value"] = fn()
            except Exception as e:
                box["error"] = e
            finally:
                done.set()

    def call(self, fn, timeout=90):
        if self.thread is None:
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
        box, done = {}, threading.Event()
        self.q.put((fn, box, done))
        if not done.wait(timeout):
            raise TimeoutError("browser action timed out")
        if "error" in box:
            raise box["error"]
        return box.get("value")


class PlaywrightBrowser:
    RISK_LEVELS = {"web_risky_click": "dangerous"}

    def __init__(self, safety=None):
        self.safety = safety or SafetyLayer()
        self.safety.register_risks(self.RISK_LEVELS)
        self._worker = _Worker()
        self._pw = self._ctx = None  # touched only on the worker thread

    # ----- everything below runs on the worker thread -----
    def _ensure(self):
        if self._ctx is not None:
            return
        from playwright.sync_api import sync_playwright
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=False, no_viewport=True,
            args=["--disable-blink-features=AutomationControlled"])

    def _page(self):
        self._ensure()
        pages = [p for p in self._ctx.pages if not p.is_closed()]
        return pages[-1] if pages else self._ctx.new_page()

    def _goto(self, target, new_tab=False):
        url = to_url(target)
        if url is None:
            from urllib.parse import quote_plus
            url = f"https://www.google.com/search?q={quote_plus(target)}"
        self._ensure()
        page = self._ctx.new_page() if new_tab else self._page()
        page.goto(url, wait_until="domcontentloaded")
        return page.title()

    def _read(self):
        page = self._page()
        text = page.inner_text("body")[:3000]
        return {"title": page.title(), "url": page.url, "text": text}

    def _locate_clickable(self, page, name):
        for loc in (page.get_by_role("button", name=name), page.get_by_role("link", name=name),
                    page.get_by_text(name, exact=False)):
            if loc.count() > 0:
                return loc.first
        return None

    def _click(self, name):
        page = self._page()
        target = self._locate_clickable(page, name)
        if target is None:
            return False
        target.click(timeout=8000)
        return True

    def _fill(self, field, value):
        page = self._page()
        candidates = [page.get_by_label(field), page.get_by_placeholder(field),
                      page.get_by_role("textbox", name=field)]
        if field.lower() in ("search", "search box", "search bar", "search field"):
            candidates.append(page.locator("input[type=search], input[name=q], [role=searchbox]"))
        for loc in candidates:
            if loc.count() > 0:
                el = loc.first
                if (el.get_attribute("type") or "").lower() == "password":
                    return "password"
                el.fill(value)
                return True
        return False

    def _screenshot(self):
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SHOT_DIR / f"web_{datetime.now():%Y%m%d_%H%M%S}.png"
        self._page().screenshot(path=str(path))
        return str(path)

    def _close(self):
        if self._ctx is not None:
            self._ctx.close()
            self._pw.stop()
            self._ctx = self._pw = None

    # ----- public router -----
    def close(self):
        try:
            self._worker.call(self._close, timeout=15)
        except Exception:
            pass

    def handle(self, intent):
        action, name, value = intent.get("action"), intent.get("name"), intent.get("destination_ref")
        call = self._worker.call
        try:
            if action in ("goto", "open", "open_url", "new_tab"):
                title = call(lambda: self._goto(name or "google.com", new_tab=(action == "new_tab")))
                narrate(f"Opened {title or name}")
                return {"status": "success", "message": f"Opened {title}", "data": None}

            if action == "read_page":
                data = call(self._read)
                narrate(f"Page: {data['title']}. " + data["text"][:180].replace("\n", " "))
                return {"status": "success", "message": data["title"], "data": data}

            if action == "click":
                if not name:
                    return {"status": "needs_clarification", "message": "What should I click?", "data": None}
                if is_risky_click(name):
                    check = self.safety.validate("web_risky_click", name)
                    if check["status"] != "approved":
                        return check
                ok = call(lambda: self._click(name))
                narrate(f"Clicked {name}" if ok else f"I couldn't find '{name}' on this page")
                return {"status": "success" if ok else "not_found", "message": f"click {name}", "data": None}

            if action in ("fill", "type"):
                if not name or value is None:
                    return {"status": "needs_clarification", "message": "Which field, and what text?", "data": None}
                res = call(lambda: self._fill(name, value))
                if res == "password":
                    narrate("I won't type into password fields. Log in yourself in the automation window.")
                    return {"status": "blocked", "message": "Password fields are off limits", "data": None}
                narrate(f"Typed into {name}" if res else f"I couldn't find a field called '{name}'")
                return {"status": "success" if res else "not_found", "message": f"fill {name}", "data": None}

            if action == "press":
                key = KEY_MAP.get((name or "").lower(), (name or "Enter").title())
                call(lambda: self._page().keyboard.press(key))
                narrate(f"Pressed {key}")
                return {"status": "success", "message": f"Pressed {key}", "data": None}

            if action == "scroll":
                delta = -700 if (name or "").lower() == "up" else 700
                call(lambda: self._page().mouse.wheel(0, delta))
                return {"status": "success", "message": f"Scrolled {name or 'down'}", "data": None}

            if action == "screenshot":
                path = call(self._screenshot)
                narrate("Saved a screenshot of the page")
                return {"status": "success", "message": path, "data": path}

            if action in ("close", "close_all"):
                call(self._close, timeout=15)
                narrate("Closed the automation browser")
                return {"status": "success", "message": "Closed", "data": None}

            return {"status": "unhandled", "message": f"Web action '{action}' not implemented", "data": None}
        except ImportError:
            return {"status": "error", "message": "Playwright not installed: pip install playwright && playwright install chromium", "data": None}
        except Exception as e:
            log.error(f"Web automation failed: {e}")
            return {"status": "error", "message": str(e).splitlines()[0][:200], "data": None}
