"""shared/ai: the provider order, overrides, costs, the monthly limit, the real backends against stand-in SDK clients."""

import types

import pytest

from shared import ai, config
from shared import db as dbmod
from shared.ai import AIError, ProviderError, backends
from shared.ai.fake import FakeAI


def test_default_chain_is_my_credits_then_openrouter(db):
    assert [(e["provider"], e["model"]) for e in ai.chain("strong", db)][:2] == [
        ("anthropic", "claude-sonnet-5-5"), ("openrouter", "anthropic/claude-sonnet-5.5")]
    assert ai.chain("auditor", db)[0]["provider"] == "deepseek"  # a different family from the writer


def test_a_stored_override_goes_first_and_default_clears_it(db):
    db.execute("INSERT INTO settings (key, value, created_at) VALUES ('model.strong', 'gpt-6-sol', 'x')")
    db.commit()
    first = ai.chain("strong", db)[0]
    assert (first["provider"], first["model"]) == ("openai", "gpt-6-sol")
    assert ("anthropic", "claude-sonnet-5-5") in [(e["provider"], e["model"]) for e in ai.chain("strong", db)]  # still a fallback
    db.execute("INSERT INTO settings (key, value, created_at) VALUES ('model.strong', NULL, 'y')")
    db.commit()
    assert ai.chain("strong", db)[0]["provider"] == "anthropic"


def test_a_one_off_alias_and_an_unknown_model(db):
    assert ai.chain("strong", db, model="opus-5.5")[0]["model"] == "claude-opus-5-5"
    with pytest.raises(AIError, match="unknown model"):
        ai.chain("strong", db, model="nonsense-9")


def test_call_uses_the_first_provider_and_prices_it(db, monkeypatch):
    fake = FakeAI(lambda job, system, prompt: "hello", input_tokens=1000, output_tokens=500).install(monkeypatch)
    reply = ai.call("strong", "say hi", system="be brief", conn=db)
    assert reply.text == "hello" and fake.models == ["anthropic:claude-sonnet-5-5"]
    assert reply.cost_usd == pytest.approx(0.002 + 0.005)  # 1000 in at $2/M + 500 out at $10/M
    row = db.execute("SELECT job, provider, model, input_tokens, cost_usd FROM ai_calls").fetchone()
    assert row == ("strong", "anthropic", "claude-sonnet-5-5", 1000, pytest.approx(0.007))


def test_the_cost_goes_to_the_runs_row(db, monkeypatch):
    from shared import runlog
    FakeAI(lambda *a: "x").install(monkeypatch)
    with runlog.run("analysis") as r:
        ai.call("strong", "p", run=r)
    assert db.execute("SELECT cost_usd FROM runs WHERE job='analysis'").fetchone()[0] == pytest.approx(0.007)
    assert db.execute("SELECT run_id FROM ai_calls").fetchone()[0] == r.id


def test_the_prices_are_the_ones_i_gave(db):
    assert ai.price_of("deepseek-v4-flash") == (0.14, 0.28, False)
    assert ai.price_of("deepseek-v4-pro") == (0.435, 0.87, False)
    assert ai.price_of("gpt-6-sol") == (2.0, 10.0, False)
    assert ai.price_of("openai/gpt-6-sol")[2] is False  # an OpenRouter name finds its model's price
    assert ai.price_of("anthropic/claude-sonnet-5.5") == (2.0, 10.0, False)  # OpenRouter's dotted version name too


def test_a_model_without_a_price_is_counted_at_the_cautious_default_and_marked_estimated(db, monkeypatch):
    assert ai.cost_of("some-new-model", 1000, 500) == (pytest.approx((1000 * 5 + 500 * 25) / 1e6), True)
    settings = config.settings()
    settings["model_aliases"] = dict(settings["model_aliases"], fresh={"provider": "deepseek", "model": "deepseek-v9"})
    monkeypatch.setattr(config, "settings", lambda: settings)
    FakeAI(lambda *a: "x").install(monkeypatch)
    reply = ai.call("auditor", "p", conn=db, model="fresh")
    assert reply.estimated and reply.cost_usd == pytest.approx(0.0175)
    assert db.execute("SELECT estimated, cost_usd FROM ai_calls").fetchone() == (1, pytest.approx(0.0175))
    assert ai.spend_by_provider(db) == [{"provider": "deepseek", "calls": 1, "usd": pytest.approx(0.0175), "estimated": 1, "rejected": 0}]


def test_a_call_keeps_its_stock(db, monkeypatch):
    db.execute("INSERT INTO stocks (cik, ticker, company, status, created_at) VALUES ('1', 'NVDA', 'Nvidia', 'candidate', 'x')")
    FakeAI(lambda *a: "x").install(monkeypatch)
    ai.call("strong", "p", conn=db, stock_id=1)
    assert db.execute("SELECT stock_id FROM ai_calls").fetchone()[0] == 1


def test_the_month_starts_on_the_utc_clock(monkeypatch):
    from datetime import datetime, timezone
    from shared import clock
    # 22:30 UTC on 31 October is 01:30 on 1 November in Turkey: the stamps are UTC, so the month is still October
    monkeypatch.setattr(clock, "now_utc", lambda: datetime(2026, 10, 31, 22, 30, tzinfo=timezone.utc))
    assert ai.month_start() == "2026-10-01"


def test_one_providers_error_moves_to_the_next(db, monkeypatch):
    fake = FakeAI(lambda *a: "ok").install(monkeypatch)
    fake.fail = {"anthropic"}
    reply = ai.call("strong", "p", conn=db)
    assert reply.provider == "openrouter" and fake.models == ["openrouter:anthropic/claude-sonnet-5.5"]


def test_all_providers_failing_says_why_without_secrets(db, monkeypatch):
    fake = FakeAI(lambda *a: "ok").install(monkeypatch)
    fake.fail = {"anthropic", "openrouter", "openai"}
    with pytest.raises(AIError) as exc:
        ai.call("strong", "p", conn=db)
    assert "anthropic claude-sonnet-5-5: fake failure" in str(exc.value) and "sk-" not in str(exc.value)


def test_the_monthly_limit_stops_a_call_before_it_is_sent(db, monkeypatch):
    fake = FakeAI(lambda *a: "ok").install(monkeypatch)
    db.execute("INSERT INTO ai_calls (job, provider, model, cost_usd, created_at) VALUES ('strong', 'anthropic', 'm', 30.5, ?)",
               (ai.month_start() + "T01:00:00Z",))
    db.commit()
    with pytest.raises(AIError, match="monthly AI limit"):
        ai.call("strong", "p", conn=db)
    assert fake.calls == []


def test_ai_calls_is_append_only(db, monkeypatch):
    FakeAI(lambda *a: "x").install(monkeypatch)
    ai.call("strong", "p", conn=db)
    with pytest.raises(Exception, match="append-only"):
        db.execute("DELETE FROM ai_calls")
    with pytest.raises(Exception, match="append-only"):
        db.execute("UPDATE ai_calls SET cost_usd = 0")


def test_estimate(db):
    assert ai.estimate("strong", 40000, 1500, conn=db) == pytest.approx(10000 * 2e-6 + 1500 * 10e-6)
    assert ai.estimate("auditor", 40000, conn=db) == pytest.approx(10000 * 0.435e-6 + 1500 * 0.87e-6)


# --- the real backends, against stand-in SDK clients ----------------------------------------------------------------------

class _Anthropic:
    def __init__(self, stop="end_turn"):
        self.seen, self.stop = {}, stop
        self.messages = self

    def create(self, **kw):
        self.seen = kw
        blocks = [types.SimpleNamespace(type="thinking", thinking=""), types.SimpleNamespace(type="text", text="the answer")]
        return types.SimpleNamespace(content=blocks, stop_reason=self.stop,
                                     usage=types.SimpleNamespace(input_tokens=120, output_tokens=40))


def test_anthropic_backend_sends_effort_and_keeps_only_text(monkeypatch):
    stub = _Anthropic()
    monkeypatch.setattr(backends, "make_anthropic", lambda key, timeout: stub)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    reply = backends.anthropic_backend({"model": "claude-sonnet-5-5", "effort": "high"}, "sys", "ask", 500)
    assert reply.text == "the answer" and (reply.input_tokens, reply.output_tokens) == (120, 40)
    assert stub.seen["output_config"] == {"effort": "high"} and stub.seen["system"] == "sys"
    assert "thinking" not in stub.seen and "temperature" not in stub.seen  # the model's own defaults


def test_anthropic_backend_refusal_and_missing_key(monkeypatch):
    monkeypatch.setattr(backends, "make_anthropic", lambda key, timeout: _Anthropic(stop="refusal"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(ProviderError, match="refused"):
        backends.anthropic_backend({"model": "m"}, "", "p", 10)
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY is not set"):
        backends.anthropic_backend({"model": "m"}, "", "p", 10)


class _OpenAI:
    def __init__(self, cost=None, finish="stop"):
        self.seen, self.cost, self.finish = {}, cost, finish
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, **kw):
        self.seen = kw
        usage = types.SimpleNamespace(prompt_tokens=200, completion_tokens=50, cost=self.cost)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(finish_reason=self.finish, message=types.SimpleNamespace(content="ok"))],
            usage=usage)


@pytest.mark.parametrize("provider,url,limit", [("deepseek", "https://api.deepseek.com", "max_tokens"),
                                                 ("openai", None, "max_completion_tokens"),
                                                 ("openrouter", "https://openrouter.ai/api/v1", "max_tokens")])
def test_openai_style_backends(monkeypatch, provider, url, limit):
    stub, seen_url = _OpenAI(cost=0.0123 if provider == "openrouter" else None), {}

    def make(key, base_url, timeout):
        seen_url["url"] = base_url
        return stub
    monkeypatch.setattr(backends, "make_openai", make)
    monkeypatch.setenv(backends.KEYS[provider], "key")
    reply = backends.openai_style_backend(provider)({"model": "m"}, "sys", "ask", 300)
    assert seen_url["url"] == url and stub.seen[limit] == 300
    assert stub.seen["messages"][0] == {"role": "system", "content": "sys"}
    assert (reply.text, reply.input_tokens, reply.output_tokens) == ("ok", 200, 50)
    assert reply.cost_usd == (0.0123 if provider == "openrouter" else None)  # OpenRouter's own figure is used


def test_a_content_filter_is_a_provider_error(monkeypatch):
    monkeypatch.setattr(backends, "make_openai", lambda *a: _OpenAI(finish="content_filter"))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    with pytest.raises(ProviderError, match="content filter"):
        backends.openai_style_backend("deepseek")({"model": "m"}, "", "p", 10)


def test_an_answer_cut_at_max_tokens_is_a_provider_error(monkeypatch):
    stub = _Anthropic(stop="max_tokens")
    monkeypatch.setattr(backends, "make_anthropic", lambda key, timeout: stub)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(ProviderError, match="cut at max_tokens"):
        backends.anthropic_backend({"model": "m"}, "", "p", 10)


@pytest.mark.parametrize("provider,model,maker", [
    ("anthropic", "claude-sonnet-5-5", "anthropic"), ("openrouter", "anthropic/claude-sonnet-5.5", "anthropic"),
    ("deepseek", "deepseek-v4-pro", "deepseek"), ("openrouter", "deepseek/deepseek-v4-pro", "deepseek"),
    ("openai", "gpt-6-sol", "openai"), ("openrouter", "openai/gpt-6-sol", "openai")])
def test_a_model_belongs_to_its_maker_even_through_openrouter(provider, model, maker):
    assert ai.family(provider, model) == maker


def test_call_skips_the_models_of_an_excluded_family(db, monkeypatch):
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    fake.fail = {"deepseek", "openrouter"}  # the auditor's own family is down: the next maker is used
    reply = ai.call("auditor", "p", conn=db, exclude_families={"anthropic"})
    assert (reply.provider, reply.model) == ("openai", "gpt-6-sol")
    fake.fail = set()
    with pytest.raises(AIError, match="writer's family"):
        ai.call("auditor", "p", conn=db, exclude_families={"deepseek", "openai"})  # nothing independent is left


def test_only_first_does_not_fall_back(db, monkeypatch):
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    fake.fail = {"anthropic"}
    with pytest.raises(AIError, match="anthropic claude-sonnet-5-5"):
        ai.call("strong", "p", conn=db, only_first=True)
    assert fake.calls == []


def test_a_billed_but_rejected_call_is_logged_and_counted(db, monkeypatch):
    monkeypatch.setattr(backends, "make_anthropic", lambda key, timeout: _Anthropic(stop="max_tokens"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with pytest.raises(AIError, match="cut at max_tokens"):  # the next providers have no key
        ai.call("strong", "p", conn=db)
    row = db.execute("SELECT provider, outcome, input_tokens, output_tokens, cost_usd, estimated FROM ai_calls").fetchone()
    assert row == ("anthropic", "cut", 120, 40, pytest.approx(120 * 2e-6 + 40 * 10e-6), 0)
    assert ai.month_spend(db) > 0 and ai.spend_by_provider(db)[0]["rejected"] == 1


@pytest.mark.parametrize("finish,refusal,outcome", [("length", None, "cut"), ("stop", "I cannot help", "refused"),
                                                    ("content_filter", None, "refused")])
def test_openai_style_cut_and_refused_answers_are_provider_errors_with_their_usage(monkeypatch, finish, refusal, outcome):
    stub = _OpenAI(finish=finish)
    stub.refusal = refusal
    orig = stub.create

    def create(**kw):
        resp = orig(**kw)
        resp.choices[0].message.refusal = refusal
        return resp
    stub.create = create
    monkeypatch.setattr(backends, "make_openai", lambda *a: stub)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "key")
    with pytest.raises(ProviderError) as exc:
        backends.openai_style_backend("deepseek")({"model": "m"}, "", "p", 10)
    assert exc.value.outcome == outcome and exc.value.usage == (200, 50, None)
