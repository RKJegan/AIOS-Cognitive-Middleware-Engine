"""One sentence -> ordered atomic steps. Rules split; retrieval-prompted LLM classifies each clause."""
import re
from core.logger import get_logger
from ai.llm_brain import LLMBrain
from ai.intent_parser import IntentParser
from ai.context_engine import ContextEngine

log = get_logger()

SPLIT_PATTERN = re.compile(r"\s*,\s*and\s+|\s*,\s*|\s+and\s+|\s+then\s+", re.IGNORECASE)
BROWSER_NAMES = ("chrome", "brave", "edge")
ACTION_VERBS = {
    "open", "close", "delete", "create", "copy", "move", "rename", "list", "run", "start",
    "stop", "uninstall", "kill", "restart", "set", "mute", "unmute", "lock", "take", "show",
    "click", "press", "scroll", "go", "turn", "install", "commit", "pull", "push", "end",
}
NO_SPLIT_PREFIXES = (
    "remind", "remember", "send", "email", "calculate", "commit", "type", "write", "summarize",
    "translate", "explain", "draft", "ask", "search", "find", "what", "how", "read", "schedule",
    "forget", "recall", "paste", "copy hello", "put the text",
)
MAX_CLAUSES = 6


class TaskPlanner:
    def __init__(self, brain=None, parser=None, context=None):
        self.brain = brain or LLMBrain()
        self.parser = parser or IntentParser()
        self.context = context or ContextEngine()

    def _split_clauses(self, text):
        low = text.strip().lower()
        if low.startswith(NO_SPLIT_PREFIXES):
            return [text]
        parts = [p.strip() for p in SPLIT_PATTERN.split(text) if p.strip()]
        deduped = []
        for p in parts:                       # "Gunsel, Gunsel, Gunsel" -> one clause
            if not deduped or p.lower().strip(".!? ") != deduped[-1].lower().strip(".!? "):
                deduped.append(p)
        parts = deduped
        if len(parts) <= 1:
            return [parts[0] if parts else text]

        result, last_verb = [], None
        for part in parts[:MAX_CLAUSES]:
            first = part.split()[0].lower()
            if first in ACTION_VERBS:
                last_verb = first
                result.append(part)
            elif last_verb:
                result.append(f"{last_verb} {part}")
            else:
                result.append(part)
        return result

    def _classify(self, clause, original, prior):
        clause = self.context.resolve(clause, prior)
        step = self.parser.parse(self.brain.ask(clause))
        step["raw_text"] = original
        return step

    def plan(self, user_text):
        low = user_text.lower()
        if "search" in low and any(b in low for b in BROWSER_NAMES):
            steps = [self._classify(user_text, user_text, None)]
        else:
            steps, prior = [], None
            for clause in self._split_clauses(user_text):
                step = self._classify(clause, user_text, prior)
                steps.append(step)
                if step.get("name"):
                    prior = (step["name"], step.get("location_ref"))

        known = [s for s in steps if s.get("intent") != "unknown"]
        steps = known if known else steps[:1]          # drop noise clauses, keep one 'unknown' if all noise
        log.info(f'Planned {len(steps)} step(s) for: "{user_text}"')
        return steps
