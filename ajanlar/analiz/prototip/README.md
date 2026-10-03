# Agent 3 prototype (trial code)

**Not production code.** Written on 2026-10-03 to try agent 3's rules (10 measures, thresholds, type, grade, price line) on 10 real US
companies. Rules: `docs/YOL_HARITASI_v2.md` section 3 · results and lessons:
`docs/BAGLAM.md` section 9 · external review: `docs/DIS_INCELEME_PROMPT.md`. When the real agent 3 is written, take ideas from here.
Do not copy it as it is.

| File | What it does |
|---|---|
| `indir.sh` | Downloads SEC data (10 trial companies + 5 examples; `frames` for all companies) |
| `karne_deneme.py` | 10 measures, type, grade — `python3 karne_deneme.py KO NVDA NKE ...` |
| `fiyat.py` | Price from Yahoo; PEG and free-cash-flow yield |
| `ek_uret.py` | Builds Appendix A / Appendix B of the external-review prompt + the Yahoo split check |
| `etiket_kontrol.py` | Shows which XBRL name was found for which company, and for how many years |
| `kapsam_olcum.py` | Measures how far the synonym list covers ~1,700 companies |

Run (from this folder):

```bash
export SEC_UA="Name Surname email@example.com"   # SEC requires a contact
bash indir.sh
python3 karne_deneme.py KO NVDA NKE SBUX PFE INTC BA SNAP DOW RIVN
uv run --with yfinance python fiyat.py
python3 etiket_kontrol.py AAPL AMZN NET V KO NVO
bash indir.sh frames && python3 kapsam_olcum.py
```

Known limitations: the "Known limitations and open questions" list in the external-review prompt.
