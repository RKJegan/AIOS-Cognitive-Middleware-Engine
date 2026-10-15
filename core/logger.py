import sys
from pathlib import Path
from loguru import logger as _logger
from config.settings import Settings
from core.paths import PROJECT_ROOT

_configured = False


def get_logger(settings=None):
    global _configured
    if _configured:
        return _logger

    settings = settings or Settings.load()
    log_dir = Path(settings.log_dir)
    if not log_dir.is_absolute():
        log_dir = PROJECT_ROOT / log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    _logger.remove()
    _logger.add(sys.stderr, level=settings.log_level,
                format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    _logger.add(log_dir / "system_{time:YYYY-MM-DD}.log", level=settings.log_level,
                rotation="00:00", retention="14 days", encoding="utf-8")
    _logger.add(log_dir / "errors_{time:YYYY-MM-DD}.log", level="ERROR",
                rotation="00:00", retention="30 days", encoding="utf-8")
    _logger.add(log_dir / "commands_{time:YYYY-MM-DD}.log", level="INFO",
                rotation="00:00", retention="30 days", encoding="utf-8",
                filter=lambda record: record["extra"].get("command", False))
    _configured = True
    return _logger
