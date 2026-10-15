from core.logger import get_logger

log = get_logger()


class MiddlewareCore:
    """Routes one clean intent to the handler registered for its category. Never acts itself."""

    def __init__(self):
        self.registry = {}
        self.verifiers = {}

    def register(self, category, handler, verifier=None):
        self.registry[category] = handler
        if verifier:
            self.verifiers[category] = verifier
        log.debug(f"Registered handler for: {category}")

    def route(self, intent):
        category = intent.get("intent", "unknown")
        handler = self.registry.get(category)
        if handler is None:
            log.warning(f"No handler registered for intent: {category}")
            return {"status": "unhandled", "message": f"No module can handle '{category}' yet", "data": None}
        try:
            result = handler(intent)
            log.info(f"Routed '{category}' -> {result.get('status')}")
            return result
        except Exception as e:
            log.error(f"Handler for '{category}' raised: {e}")
            return {"status": "error", "message": str(e), "data": None}

    def verify(self, intent, result):
        """True = confirmed, False = could not confirm, None = no way to check."""
        verifier = self.verifiers.get(intent.get("intent"))
        if not verifier:
            return None
        try:
            return verifier(intent, result)
        except Exception as e:
            log.warning(f"Verifier error: {e}")
            return None
