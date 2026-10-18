"""The LIVE model order in settings.yaml (the AI unit tests use their own fixed order, see conftest `sonnet_first_models`)."""

from shared import config


def test_the_live_order_is_deepseek_then_gpt_then_sonnet_last():
    # the Anthropic credit ended 2026-10-19 and is not topped up this month (decision 2026-10-18); Sonnet is a fallback again later
    for job in ("strong", "auditor"):
        order = [(e["provider"], e["model"], e.get("effort")) for e in config.settings()["models"][job]]
        assert order[:3] == [("deepseek", "deepseek-v4-pro", None), ("openai", "gpt-6-sol", "high"),
                             ("anthropic", "claude-sonnet-5-5", "high")]
        assert [e[0] for e in order[3:]] == ["openrouter"] * 3
