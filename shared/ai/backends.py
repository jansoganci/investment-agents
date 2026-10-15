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


WEB_SEARCH_TOOL = "web_search_20260209"      # Sonnet 5.5 / Opus 5.x: dynamic filtering (claude-api skill, 2026-10)
MAX_CONTINUES = 4                            # a long search turn can end in `pause_turn`: ask again, at most this many times


def _web_sources(content) -> tuple[list[dict], bool]:
    """The pages a web-search answer rests on (search results and the citations in the text), and whether a search failed."""
    found: dict[str, dict] = {}
    failed = False
    for block in content:
        kind = getattr(block, "type", "")
        if kind == "web_search_tool_result":
            results = getattr(block, "content", None)
            if isinstance(results, list):
                for item in results:
                    url = getattr(item, "url", None)
                    if url:
                        found.setdefault(url, {"url": url, "title": getattr(item, "title", None), "cited_text": None})
            else:
                failed = True                # an error object, not a list (HTTP 200: the tool reports it in the block)
        elif kind == "text":
            for cite in getattr(block, "citations", None) or []:
                url = getattr(cite, "url", None)
                if url:
                    entry = found.setdefault(url, {"url": url, "title": getattr(cite, "title", None), "cited_text": None})
                    entry["cited_text"] = entry["cited_text"] or getattr(cite, "cited_text", None)
    return list(found.values()), failed


def anthropic_backend(entry: dict, system: str, prompt: str, max_tokens: int) -> Reply:
    client = make_anthropic(_key("anthropic"), _timeout())
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": entry["model"], "max_tokens": max_tokens}
    if system:
        kwargs["system"] = system
    if entry.get("effort"):
        kwargs["output_config"] = {"effort": entry["effort"]}  # thinking stays on its default (adaptive)
    if entry.get("web_search"):
        kwargs["tools"] = [{"type": WEB_SEARCH_TOOL, "name": "web_search", "max_uses": int(entry["web_search"])}]
    n_in = n_out = searches = 0
    sources: dict[str, dict] = {}
    text = ""
    for _ in range(MAX_CONTINUES + 1):
        try:
            msg = client.messages.create(messages=messages, **kwargs)
        except anthropic.APIStatusError as exc:
            raise ProviderError(f"HTTP {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderError("could not be reached") from exc
        n_in += msg.usage.input_tokens
        n_out += msg.usage.output_tokens
        used = getattr(getattr(msg.usage, "server_tool_use", None), "web_search_requests", None)
        searches += int(used or 0)
        usage = (n_in, n_out, None)  # billed even when the answer is rejected below
        if msg.stop_reason == "refusal":
            raise ProviderError("the model refused (safety classifier)", usage=usage, outcome="refused")
        if msg.stop_reason == "max_tokens":
            raise ProviderError("the answer was cut at max_tokens (thinking counts too); raise `ai.max_tokens`", usage=usage,
                                outcome="cut")
        found, _failed = _web_sources(msg.content)
        for item in found:
            sources.setdefault(item["url"], item)
        text += "".join(b.text for b in msg.content if b.type == "text")
        if msg.stop_reason == "pause_turn":
            messages = messages + [{"role": "assistant", "content": msg.content}]
            continue
        break
    else:
        raise ProviderError("the search turn did not finish", usage=(n_in, n_out, None), outcome="cut")
    return Reply(text, "anthropic", entry["model"], n_in, n_out, sources=tuple(sources.values()), searches=searches)


def openai_style_backend(provider: str):
    def backend(entry: dict, system: str, prompt: str, max_tokens: int) -> Reply:
        if entry.get("web_search"):
            raise ProviderError(f"{provider} cannot run a web search here")      # only Anthropic's tool is wired
        client = make_openai(_key(provider), BASE_URLS[provider], _timeout())
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        kwargs = {"model": entry["model"], "messages": messages}
        kwargs["max_completion_tokens" if provider == "openai" else "max_tokens"] = max_tokens
        if provider == "openrouter":
            kwargs["extra_body"] = {"usage": {"include": True}}  # OpenRouter then reports its own cost
            if entry.get("effort"):
                kwargs["extra_body"]["reasoning"] = {"effort": entry["effort"]}
        elif provider == "openai" and entry.get("effort"):
            kwargs["reasoning_effort"] = entry["effort"]
        try:
            resp = client.chat.completions.create(**kwargs)
        except openai.APIStatusError as exc:
            raise ProviderError(f"HTTP {exc.status_code}") from exc
        except openai.APIConnectionError as exc:
            raise ProviderError("could not be reached") from exc
        if not getattr(resp, "choices", None):
            # some providers answer HTTP 200 with an error body or no choices (overload, a provider hiccup): try the next model
            raise ProviderError("the answer had no choices (empty reply)")
        choice = resp.choices[0]
        usage = resp.usage
        cost = getattr(usage, "cost", None) if usage is not None else None
        if cost is None and usage is not None:
            cost = (getattr(usage, "model_extra", None) or {}).get("cost")
        n_in, n_out = getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None)
        billed = (n_in, n_out, float(cost) if cost is not None else None) if n_in is not None and n_out is not None else None
        if choice.finish_reason == "content_filter" or getattr(choice.message, "refusal", None):
            raise ProviderError("the model refused (content filter)", usage=billed, outcome="refused")
        if choice.finish_reason == "length":
            raise ProviderError("the answer was cut at the token limit; raise `ai.max_tokens`", usage=billed, outcome="cut")
        return Reply(choice.message.content or "", provider, entry["model"], n_in, n_out,
                     float(cost) if cost is not None else None)
    return backend


BACKENDS["anthropic"] = anthropic_backend
for _p in ("deepseek", "openai", "openrouter"):
    BACKENDS[_p] = openai_style_backend(_p)
