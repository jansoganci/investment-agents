import pytest


@pytest.fixture(autouse=True)
def no_real_ai_keys(monkeypatch):
    """A test never reaches a real AI provider, whatever keys the developer's .env holds."""
    for name in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_real_mof(monkeypatch):
    """A test never reads the Ministry of Finance's real file: an empty one (header only) stands in unless the test brings its own."""
    from shared.prices import mof

    monkeypatch.setattr(mof, "_get_text", lambda url, timeout=30: "Interest Rate\nDate,10Y\n")


@pytest.fixture(autouse=True)
def no_company_step(monkeypatch):
    """The production setting `eye.extract_companies` must not change what an Eye test asks the model; a test that wants the step sets it itself."""
    from shared import config

    real = config.settings
    monkeypatch.setattr(config, "settings", lambda: {**real(), "eye": {**(real().get("eye") or {}), "extract_companies": False}})


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A clean data folder and Drive folder for each test; the real .env and database are never touched."""
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    return {"data": data, "drive": drive}


@pytest.fixture
def db(env):
    """An initialized database; yields a write connection."""
    from shared import db as dbmod

    dbmod.init()
    conn = dbmod.connect()
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def no_research_on_watch(monkeypatch):
    """/watch for a new stock runs agent 2 and agent 3 afterwards (needs the web); the older tests check the state change only."""
    from shared.commands import stocks

    monkeypatch.setattr(stocks, "RESEARCH_ON_WATCH", False)


@pytest.fixture
def sonnet_first_models(monkeypatch):
    """The AI unit tests describe how the chain WORKS with a fixed order (Sonnet, DeepSeek, GPT, then OpenRouter), so a change of the
    live order in settings.yaml (2026-10-18) does not break them. The live order has its own test: tests/test_models_order.py."""
    from shared import config
    real = config.settings
    order = [{"provider": "anthropic", "model": "claude-sonnet-5-5", "effort": "high"},
             {"provider": "deepseek", "model": "deepseek-v4-pro"},
             {"provider": "openai", "model": "gpt-6-sol", "effort": "high"},
             {"provider": "openrouter", "model": "anthropic/claude-sonnet-5.5", "effort": "high"},
             {"provider": "openrouter", "model": "deepseek/deepseek-v4-pro"},
             {"provider": "openrouter", "model": "openai/gpt-6-sol", "effort": "high"}]

    def patched():
        data = real()
        data["models"] = dict(data["models"], strong=[dict(e) for e in order], auditor=[dict(e) for e in order])
        return data
    monkeypatch.setattr(config, "settings", patched)
