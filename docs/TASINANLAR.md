# Taşınanlar

Eski projeden (`investment-intelligence`, etiket `v1-arsiv`) veya geçici çalışmalardan alınan dosyalar.

| Tarih | Kaynak | Hedef | Neden |
|---|---|---|---|
| 2026-10-03 | `/tmp/sma_backtest/backtest.py` (geçici çalışma) | `ajanlar/teknik/backtest/gunluk_5_8_13.py` | Günlük 5-8-13 backtest; 4. ajan kuralları için referans |
| 2026-10-03 | `/tmp/sma_backtest/weekly.py` (geçici çalışma) | `ajanlar/teknik/backtest/haftalik.py` | Haftalık kurallar + piyasa filtresi backtest'i |

Çalıştırma: `cd ajanlar/teknik/backtest && uv run --with yfinance --with pandas python haftalik.py`
