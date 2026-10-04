# Transferred files

Files taken from the old project (`investment-intelligence`, tag `v1-arsiv`) or from temporary work.

| Date | Source | Target | Why |
|---|---|---|---|
| 2026-10-03 | `/tmp/sma_backtest/backtest.py` (temporary work) | `ajanlar/teknik/backtest/gunluk_5_8_13.py` | Daily 5-8-13 backtest; reference for Agent 4 (Technical) rules |
| 2026-10-03 | `/tmp/sma_backtest/weekly.py` (temporary work) | `ajanlar/teknik/backtest/haftalik.py` | Weekly rules plus the market-filter backtest |
| 2026-10-03 | scratchpad (temporary work) | `ajanlar/analiz/prototip/` (`karne_deneme.py`, `altin_set.py`, `etiket_kontrol.py`, `kapsam_olcum.py`, `indir.sh`, `yahoo_indir.py`) | Agent 3 rule trial (prototype, not production) |

Run: `cd ajanlar/teknik/backtest && uv run --with yfinance --with pandas python haftalik.py`
