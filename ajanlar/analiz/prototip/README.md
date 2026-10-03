# Agent 3 prototype (trial code)

**Not production code.** Written on 2026-10-03 to try agent 3's rules (10 measures, thresholds, Lynch type, grade, flags,
price line) on real US companies. Rules: `docs/YOL_HARITASI_v2.md` section 3 · results and lessons: `docs/BAGLAM.md`
section 9 · external reviews: `docs/reviews/`. The real agent 3 takes ideas from here; it is not copied as is.

| File | What it does |
|---|---|
| `indir.sh` | Downloads SEC data (companyfacts + submissions for the SIC code); `frames` downloads all-company data |
| `yahoo_indir.py` | Yahoo: price, market cap (USD), split history, FX → `yahoo.json` |
| `karne_deneme.py` | 10 measures, type, grade, flags, price line — `python3 karne_deneme.py KO NVDA ...` |
| `altin_set.py` | Golden set: reruns the 10 trial companies and reports any grade / type change |
| `etiket_kontrol.py` | Which XBRL name exists in which company, for how many years |
| `kapsam_olcum.py` | Measures the synonym lists' coverage over ~1,700 companies |

Run (in this folder):

```bash
export SEC_UA="Name Surname email@example.com"   # SEC asks for contact info
bash indir.sh
uv run --with yfinance python yahoo_indir.py KO NVDA NKE SBUX PFE INTC BA SNAP DOW RIVN NVO
python3 karne_deneme.py KO NVDA NKE SBUX PFE INTC BA SNAP DOW RIVN NVO
python3 altin_set.py
```

`NVO` (Novo Nordisk) is an IFRS / 20-F example; it is not in the golden set. The first version of the trial code (before the
external reviews) is in Appendix C of `docs/DIS_INCELEME_PROMPT.md`.
