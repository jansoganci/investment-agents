# Transferred files

Files taken from the old project (`investment-intelligence`, tag `v1-arsiv`) or from temporary work.

| Date | Source | Target | Why |
|---|---|---|---|
| 2026-10-03 | `/tmp/sma_backtest/backtest.py` (temporary work) | `ajanlar/teknik/backtest/gunluk_5_8_13.py` | Daily 5-8-13 backtest; reference for Agent 4 (Technical) rules |
| 2026-10-03 | `/tmp/sma_backtest/weekly.py` (temporary work) | `ajanlar/teknik/backtest/haftalik.py` | Weekly rules plus the market-filter backtest |
| 2026-10-03 | scratchpad (temporary work) | `ajanlar/analiz/prototip/` (`karne_deneme.py`, `altin_set.py`, `etiket_kontrol.py`, `kapsam_olcum.py`, `indir.sh`, `yahoo_indir.py`) | Agent 3 rule trial (prototype, not production) |
| 2026-10-16 | idea only, no file: `investment-intelligence` `docs/WAVE2_SPEC_DECISIONS_A1_A4_v1.md` (SD-W2-A1, captive finance) | `settings.yaml` `finance_arm` + `agents/analysis/measures.py` warning | A maker's lending-arm debt must not be read as the business's own debt; the old rule "do not invent a split, say so" |

Run: `cd ajanlar/teknik/backtest && uv run --with yfinance --with pandas python haftalik.py`
