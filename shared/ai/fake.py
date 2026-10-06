"""A stand-in for every provider, for tests (roadmap section 3 of the plan: "AI in tests is fake — fixed answers").

    fake = FakeAI(lambda job, system, prompt: {"answer": "..."})   # a dict becomes JSON text
    fake.install(monkeypatch)
    ... code that calls shared.ai ...
    fake.calls        # [(job, system, prompt)]
"""

from __future__ import annotations

import json
from typing import Callable

from shared import ai
from shared.ai import ProviderError, Reply


class FakeAI:
    def __init__(self, handler: Callable[[str, str, str], object], input_tokens: int = 1000, output_tokens: int = 500):
        self.handler = handler
        self.calls: list[tuple[str, str, str]] = []
        self.models: list[str] = []
        self.input_tokens, self.output_tokens = input_tokens, output_tokens
        self.fail: set[str] = set()  # providers that fail with a ProviderError

    def _backend(self, provider: str):
        def backend(entry, system, prompt, max_tokens):
            if provider in self.fail:
                raise ProviderError("fake failure")
            self.calls.append((entry["job"], system, prompt))
            self.models.append(f"{provider}:{entry['model']}")
            out = self.handler(entry["job"], system, prompt)
            text = out if isinstance(out, str) else json.dumps(out)
            return Reply(text, provider, entry["model"], self.input_tokens, self.output_tokens)
        return backend

    def install(self, monkeypatch) -> "FakeAI":
        monkeypatch.setattr(ai, "BACKENDS", {p: self._backend(p) for p in ("anthropic", "deepseek", "openai", "openrouter")})
        return self
