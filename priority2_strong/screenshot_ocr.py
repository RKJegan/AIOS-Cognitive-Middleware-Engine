from pathlib import Path
from datetime import datetime
from core.logger import get_logger
from core.narrator import narrate
from config.settings import Settings

log = get_logger()


class ScreenshotOCR:
    def __init__(self, settings=None):
        self.settings = settings or Settings.load()
        if self.settings.tesseract_cmd:
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd
            except Exception:
                pass

    def screenshot(self):
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            out = Path.home() / "Pictures" / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out)
            narrate(f"Screenshot saved to {out.name}")
            return {"status": "success", "message": f"Saved {out}", "data": {"path": str(out)}}
        except Exception as e:
            return {"status": "error", "message": str(e), "data": None}

    def ocr_image(self, path):
        try:
            import pytesseract
            from PIL import Image
            text = pytesseract.image_to_string(Image.open(path))
            narrate(f"Found {len(text.split())} words of text")
            return {"status": "success", "message": "OCR complete", "data": {"text": text}}
        except Exception as e:
            return {"status": "error", "message": f"OCR failed (install pytesseract + Tesseract-OCR): {e}", "data": None}

    def read_screen(self):
        shot = self.screenshot()
        if shot["status"] != "success":
            return shot
        return self.ocr_image(shot["data"]["path"])

    def handle(self, intent):
        action, name, loc = intent.get("action"), intent.get("name"), intent.get("location_ref")
        if action == "screenshot":
            return self.screenshot()
        if action == "read_screen":
            return self.read_screen()
        if action == "ocr_file":
            path = str(Path(loc) / name) if loc and name else name
            return self.ocr_image(path)
        return {"status": "unhandled", "message": f"Screenshot/OCR action '{action}' not implemented yet", "data": None}
