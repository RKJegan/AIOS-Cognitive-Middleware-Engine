from pathlib import Path
from core.logger import get_logger
from core.narrator import narrate

log = get_logger()


class DocumentController:
    def _extract(self, path):
        p = Path(path)
        if p.suffix.lower() == ".pdf":
            import PyPDF2
            with open(p, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join((pg.extract_text() or "") for pg in reader.pages)
        if p.suffix.lower() in (".docx",):
            import docx
            return "\n".join(para.text for para in docx.Document(str(p)).paragraphs)
        return p.read_text(encoding="utf-8", errors="ignore")

    def read(self, path):
        try:
            text = self._extract(path)
            narrate(f"Read {Path(path).name}, {len(text.split())} words")
            return {"status": "success", "message": "Document read", "data": {"text": text[:5000]}}
        except Exception as e:
            return {"status": "error", "message": f"Couldn't read document: {e}", "data": None}

    def search_in(self, path, query):
        result = self.read(path)
        if result["status"] != "success":
            return result
        text = result["data"]["text"]
        found = query.lower() in text.lower()
        narrate(f"Found '{query}'" if found else f"'{query}' not found")
        return {"status": "success" if found else "not_found", "message": "Search complete", "data": {"found": found}}

    def handle(self, intent):
        action, name, loc, dest = intent.get("action"), intent.get("name"), intent.get("location_ref"), intent.get("destination_ref")
        aliases = {
            "desktop": r"C:\Users\%USERNAME%\Desktop",
            "documents": r"C:\Users\%USERNAME%\Documents",
            "downloads": r"C:\Users\%USERNAME%\Downloads",
        }
        import os
        base = os.path.expandvars(aliases.get((loc or "").lower(), loc or ""))
        path = str(Path(base) / name) if base and name else name
        if action == "read":
            return self.read(path)
        if action == "search_in":
            return self.search_in(path, dest or "")
        return {"status": "unhandled", "message": f"Document action '{action}' not implemented yet", "data": None}
