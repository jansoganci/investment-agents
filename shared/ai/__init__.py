"""The one AI client (roadmap section 10.1 and "Agent 3's AI parts — how phase 2 builds them").

    reply = ai.call("strong", prompt, system=system, run=run, stock_id=3)
    reply.text

A job (`cheap`, `strong`, `auditor`) has an ordered provider list in `settings.yaml` (my credits first, then OpenRouter).
A call tries the list in order; one provider's error or refusal moves it to the next. A Telegram override (`/model`) puts
one model first. Every call is a row in `ai_calls`, its dollars go to the job's `runs` row, and a call is refused when
the month's spend has reached the limit. The providers are in `shared/ai/backends.py`; tests use `shared/ai/fake.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from shared import clock, config
from shared import db as dbmod


class AIError(RuntimeError):
    """The call could not be made (every provider failed, or the monthly limit is reached). The message has no secrets."""


class ProviderError(Exception):
    """One provider failed (no key, empty credit, rate limit, server error, a safety refusal): the next one is tried.
    `usage` = (input tokens, output tokens, cost or None) when the call was billed although it was rejected (a refusal, an
    answer cut at the token limit): it is still logged and counted."""

    def __init__(self, message: str, *, usage: tuple | None = None, outcome: str = "refused"):
        super().__init__(message)
        self.usage, self.outcome = usage, outcome


@dataclass
class Reply:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None      # None = the tokens are unknown
    job: str = ""
    estimated: bool = False            # counted at the default price (the model has none in settings.yaml)


# provider → backend(entry, system, prompt, max_tokens) -> Reply. Filled by `shared.ai.backends`; tests replace it.
BACKENDS: dict[str, Callable[[dict, str, str, int], Reply]] = {}


# --- which models, in which order -----------------------------------------------------------------------------------------

def _override(conn, job: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ? AND void = 0 ORDER BY id DESC LIMIT 1",
                       (f"model.{job}",)).fetchone()
    return row[0] if row and row[0] else None


def resolve(name: str) -> dict | None:
    """A model name or alias (`opus-5.5`, `gpt-6-sol`) → a provider entry; None if it is unknown."""
    s = config.settings()
    alias = (s.get("model_aliases") or {}).get(name)
    if alias:
        return dict(alias)
    for entries in (s.get("models") or {}).values():
        for e in entries:
            if e["model"] == name:
                return dict(e)
    for entries in (s.get("models") or {}).values():
        for e in entries:
            if e["model"].endswith("/" + name):
                return dict(e)
    return None


def chain(job: str, conn=None, model: str | None = None) -> list[dict]:
    """The provider entries a call of `job` tries, in order. A one-off `model`, or my stored override, goes first."""
    s = config.settings()
    base = [dict(e) for e in (s.get("models") or {}).get(job, [])]
    if not base:
        raise AIError(f"no models are set for the job '{job}' in settings.yaml")
    name = model
    if name is None and conn is not None:
        name = _override(conn, job)
    if name:
        first = resolve(name)
        if first is None:
            raise AIError(f"unknown model '{name}' (known: {', '.join(sorted(model_names()))})")
        return [first] + [e for e in base if e != first]
    return base


def family(provider: str, model: str) -> str:
    """Who made the model: `anthropic`, `deepseek`, `openai` (an OpenRouter model counts as its maker's).
    The auditor must never be of the writer's family (roadmap, "Changes after the phase 2 audit")."""
    name = model.lower()
    if provider == "openrouter" and "/" in name:
        name = name.split("/")[0]
    if provider == "anthropic" or name.startswith(("anthropic", "claude")):
        return "anthropic"
    if provider == "deepseek" or name.startswith("deepseek"):
        return "deepseek"
    if provider == "openai" or name.startswith(("openai", "gpt", "o1", "o3")):
        return "openai"
    return provider


def entry_family(entry: dict) -> str:
    return family(entry["provider"], entry["model"])


def model_names() -> list[str]:
    s = config.settings()
    names = set((s.get("model_aliases") or {}))
    for entries in (s.get("models") or {}).values():
        names |= {e["model"] for e in entries}
    return sorted(names)


# --- money ----------------------------------------------------------------------------------------------------------------

def price_of(model: str) -> tuple[float, float, bool]:
    """(dollars per million input tokens, per million output tokens, estimated?) from settings.yaml. A model without a price gets
    `pricing.default` (cautious) and is marked estimated."""
    table = config.settings().get("pricing") or {}
    for key in (model, model.split("/")[-1]):
        p = table.get(key)
        if p and p.get("input") is not None and p.get("output") is not None:
            return float(p["input"]), float(p["output"]), False
    d = table.get("default") or {"input": 5.0, "output": 25.0}
    return float(d["input"]), float(d["output"]), True


def cost_of(model: str, input_tokens: int | None, output_tokens: int | None) -> tuple[float | None, bool]:
    """(dollars, estimated?); (None, False) when the tokens are unknown."""
    if input_tokens is None or output_tokens is None:
        return None, False
    i, o, est = price_of(model)
    return (input_tokens * i + output_tokens * o) / 1_000_000, est


def estimate(job: str, input_chars: int, output_tokens: int = 1500, model: str | None = None, conn=None) -> float:
    """A rough cost before a call (about 4 characters a token), at the first model's price (the default price if it has none)."""
    first = chain(job, conn, model)[0]
    return cost_of(first["model"], input_chars // 4, output_tokens)[0]


def month_start() -> str:
    """The first day of this month, UTC (the same clock the `created_at` stamps use)."""
    return clock.now_utc().strftime("%Y-%m-01")


def month_spend(conn) -> float:
    return conn.execute("SELECT coalesce(sum(cost_usd), 0) FROM ai_calls WHERE created_at >= ?",
                        (month_start(),)).fetchone()[0]


def spend_by_provider(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT provider, count(*), coalesce(sum(cost_usd), 0), coalesce(sum(estimated), 0), "
        "coalesce(sum(outcome != 'ok'), 0) FROM ai_calls WHERE created_at >= ? GROUP BY provider ORDER BY provider",
        (month_start(),)).fetchall()
    return [{"provider": p, "calls": n, "usd": usd, "estimated": e, "rejected": r} for p, n, usd, e, r in rows]


# --- the call -------------------------------------------------------------------------------------------------------------

def call(job: str, prompt: str, *, system: str = "", max_tokens: int | None = None, run=None, stock_id=None,
         model: str | None = None, conn=None, exclude_families: set | None = None, only_first: bool = False) -> Reply:
    """`exclude_families`: models of these makers are skipped (the auditor never uses the writer's family).
    `only_first`: no fallback to the next provider (the strong-model test must know which model answered)."""
    s = config.settings()
    own = conn is None
    conn = conn or dbmod.connect()
    try:
        limit = (s.get("budget") or {}).get("ai_monthly_max_usd")
        spent = month_spend(conn)
        if limit is not None and spent >= limit:
            raise AIError(f"the monthly AI limit is reached (${spent:.2f} of ${limit}); nothing was sent")
        tokens = max_tokens or (s.get("ai") or {}).get("max_tokens", 6000)
        errors = []
        entries = chain(job, conn, model)
        if exclude_families:
            entries = [e for e in entries if entry_family(e) not in exclude_families]
            if not entries:
                raise AIError(f"every model of the job '{job}' is of the writer's family ({', '.join(sorted(exclude_families))}): "
                              "the check cannot be independent")
        if only_first:
            entries = entries[:1]
        for entry in entries:
            backend = BACKENDS.get(entry["provider"])
            if backend is None:
                errors.append(f"{entry['provider']}: unknown provider")
                continue
            try:
                reply = backend(dict(entry, job=job), system, prompt, tokens)
            except ProviderError as exc:
                errors.append(f"{entry['provider']} {entry['model']}: {exc}")
                if exc.usage:  # billed although rejected: still counted
                    n_in, n_out, given = exc.usage
                    cost, est = (given, False) if given is not None else cost_of(entry["model"], n_in, n_out)
                    _log(conn, run, Reply("", entry["provider"], entry["model"], n_in, n_out, cost, job, est), stock_id,
                         exc.outcome)
                continue
            if reply.cost_usd is None:
                cost, est = cost_of(reply.model, reply.input_tokens, reply.output_tokens)
                reply = replace(reply, cost_usd=cost, estimated=est)
            reply = replace(reply, job=job)
            _log(conn, run, reply, stock_id)
            return reply
        raise AIError(f"no model answered the job '{job}': " + " | ".join(errors))
    finally:
        if own:
            conn.close()


def log_reply(conn, run, reply: Reply, stock_id=None, outcome: str = "ok") -> None:
    """One row in `ai_calls`, and the dollars on the job's `runs` row."""
    conn.execute("INSERT INTO ai_calls (run_id, stock_id, job, provider, model, input_tokens, output_tokens, cost_usd, estimated, "
                 "outcome, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (getattr(run, "id", None), stock_id, reply.job, reply.provider, reply.model, reply.input_tokens,
                  reply.output_tokens, reply.cost_usd, 1 if reply.estimated else 0, outcome, clock.utc_iso()))
    conn.commit()
    if run is not None and reply.cost_usd:
        run.add_cost(reply.cost_usd)


_log = log_reply


from shared.ai import backends  # noqa: E402,F401 — registers the real providers in BACKENDS
