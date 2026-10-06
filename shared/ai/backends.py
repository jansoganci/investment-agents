"""The providers behind `shared.ai.call`: Anthropic (its own SDK) and the OpenAI-style ones (DeepSeek, OpenAI,
OpenRouter). A backend gets (entry, system, prompt, max_tokens) and returns a `Reply`, or raises `ProviderError`
(no key, empty credit, rate limit, server error, a safety refusal) so the next provider is tried. Keys come from `.env`
and are never printed."""

from __future__ import annotations

import os

import anthropic
import openai

from shared import config
from shared.ai import BACKENDS, ProviderError, Reply

KEYS = {"anthropic": "ANTHROPIC_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY"}
BASE_URLS = {"deepseek": "https://api.deepseek.com", "openai": None, "openrouter": "https://openrouter.ai/api/v1"}


def _key(provider: str) -> str:
    key = os.environ.get(KEYS[provider], "").strip()
    if not key:
        raise ProviderError(f"{KEYS[provider]} is not set")
    return key


def _timeout() -> float:
    return float((config.settings().get("ai") or {}).get("timeout_s", 180))


# Replaced in tests by stand-ins; the real ones build the SDK clients.
def make_anthropic(key: str, timeout: float):
    return anthropic.Anthropic(api_key=key, timeout=timeout)


def make_openai(key: str, base_url: str | None, timeout: float):
    return openai.OpenAI(api_key=key, base_url=base_url, timeout=timeout)


def anthropic_backend(entry: dict, system: str, prompt: str, max_tokens: int) -> Reply:
    client = make_anthropic(_key("anthropic"), _timeout())
    kwargs = {"model": entry["model"], "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    if entry.get("effort"):
        kwargs["output_config"] = {"effort": entry["effort"]}  # thinking stays on its default (adaptive)
    try:
        msg = client.messages.create(**kwargs)
    except anthropic.APIStatusError as exc:
        raise ProviderError(f"HTTP {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ProviderError("could not be reached") from exc
    if msg.stop_reason == "refusal":
        raise ProviderError("the model refused (safety classifier)")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return Reply(text, "anthropic", entry["model"], msg.usage.input_tokens, msg.usage.output_tokens)


def openai_style_backend(provider: str):
    def backend(entry: dict, system: str, prompt: str, max_tokens: int) -> Reply:
        client = make_openai(_key(provider), BASE_URLS[provider], _timeout())
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        kwargs = {"model": entry["model"], "messages": messages}
        kwargs["max_completion_tokens" if provider == "openai" else "max_tokens"] = max_tokens
        if provider == "openrouter":
            kwargs["extra_body"] = {"usage": {"include": True}}  # OpenRouter then reports its own cost
        try:
            resp = client.chat.completions.create(**kwargs)
        except openai.APIStatusError as exc:
            raise ProviderError(f"HTTP {exc.status_code}") from exc
        except openai.APIConnectionError as exc:
            raise ProviderError("could not be reached") from exc
        choice = resp.choices[0]
        if choice.finish_reason == "content_filter":
            raise ProviderError("the model refused (content filter)")
        usage = resp.usage
        cost = getattr(usage, "cost", None) if usage is not None else None
        if cost is None and usage is not None:
            cost = (getattr(usage, "model_extra", None) or {}).get("cost")
        return Reply(choice.message.content or "", provider, entry["model"],
                     getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None),
                     float(cost) if cost is not None else None)
    return backend


BACKENDS["anthropic"] = anthropic_backend
for _p in ("deepseek", "openai", "openrouter"):
    BACKENDS[_p] = openai_style_backend(_p)
