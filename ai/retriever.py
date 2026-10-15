"""Retrieval over the example bank (BM25, pure python, no model, no VRAM).
This is the 'RAG' for the intent parser: instead of stuffing every example into every prompt,
fetch only the few examples most similar to what the user just said."""
import math
import re
from collections import Counter
from pathlib import Path

from core.paths import DATA_DIR

STOP = {"the", "a", "an", "to", "my", "me", "please", "can", "you", "i", "on", "in", "of", "for", "is",
        "it", "and", "do", "does", "have", "with", "that", "this", "now", "up", "so"}


def _stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokenize(text):
    words = re.findall(r"[a-z0-9_.]+", text.lower().replace("_", " "))
    return [_stem(w) for w in words if w not in STOP]


class Example:
    __slots__ = ("text", "intent", "action", "name", "loc", "dest")

    def __init__(self, text, intent, action, name=None, loc=None, dest=None):
        self.text, self.intent, self.action, self.name, self.loc, self.dest = text, intent, action, name, loc, dest

    def as_json_line(self):
        import json
        obj = {"intent": self.intent, "action": self.action}
        for key, val in (("name", self.name), ("location_ref", self.loc), ("destination_ref", self.dest)):
            if val is not None:
                obj[key] = val
        return f'"{self.text}" -> {json.dumps(obj)}'


def parse_examples(text):
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(" | ")]
        if len(parts) != 6:
            continue
        t, intent, action, name, loc, dest = parts
        none = lambda v: None if v == "-" else v
        out.append(Example(t, intent, action, none(name), none(loc), none(dest)))
    return out


def load_examples(extra_paths=None):
    paths = [Path(__file__).parent / "examples.txt", DATA_DIR / "user_examples.txt"] + list(extra_paths or [])
    examples = []
    for p in paths:
        if Path(p).exists():
            examples.extend(parse_examples(Path(p).read_text(encoding="utf-8")))
    return examples


class ExampleRetriever:
    def __init__(self, examples=None, k1=1.4, b=0.7):
        self.examples = examples if examples is not None else load_examples()
        self.k1, self.b = k1, b
        self.docs = [tokenize(f"{e.text} {e.intent} {e.action}") for e in self.examples]
        self.doc_len = [len(d) for d in self.docs]
        self.avg_len = (sum(self.doc_len) / len(self.docs)) if self.docs else 1.0
        df = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def _score(self, q_tokens, i):
        s, tf, dl = 0.0, self.tf[i], self.doc_len[i]
        for t in q_tokens:
            f = tf.get(t, 0)
            if f:
                s += self.idf.get(t, 0) * (f * (self.k1 + 1)) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg_len))
        return s

    def top(self, query, k=8, per_action=2):
        q = tokenize(query)
        scored = sorted(((self._score(q, i), i) for i in range(len(self.examples))), reverse=True)
        chosen, seen = [], Counter()
        for score, i in scored:
            if score <= 0 and len(chosen) >= 3:
                break
            e = self.examples[i]
            key = (e.intent, e.action)
            if seen[key] >= per_action:
                continue
            seen[key] += 1
            chosen.append(e)
            if len(chosen) >= k:
                break
        return list(reversed(chosen))  # most similar last, right next to the user's text
