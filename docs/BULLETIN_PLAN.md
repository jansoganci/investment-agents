---
doc: Morning bulletin — implementation plan
date: 2026-10-28
status: draft, waiting for my check
publish: no
---

# Morning bulletin — implementation plan

The rules are in the roadmap, "Morning bulletin" (section 3, decision 2026-10-28). This file says **what is built, where, in which
order, and how each piece is checked**. Names follow `docs/GLOSSARY.md` (the new names are added in slice 0). "I" = the user;
"Claude" = the builder (the cloud session); "H" = Hermes on the Air.

## 1. What it is, in one paragraph

On weekdays at 08:15, Telegram receives a Turkish bulletin that can be read in 5 minutes, written to a fixed template. Its sources are what
the system already collects (the Eye's posts from both sites, the cards, SEC, the nightly prices) plus a few DeepSeek web searches. All
work and all stored text is in English; only the final text is translated into Turkish. The bulletin is **information only**: it never
writes to a card, a score, a signal or a stock's state, and it never comments. I can also ask for a web search at any time.

## 2. The template (approved 2026-10-28)

Sections, in this order. Each item is one fact in at most 2 lines, with a comparison when one exists (expected / previous) and a source
tag `[ED]` Emtia Defteri · `[DR]` Dragonomi · `[W]` web. Links are at the end.

1. `📊 RAKAMLAR (son kapanış)` — level · **1-month change** · day change. Yields in basis points. Rows: S&P 500, Nasdaq, US 10Y,
   Japan 10Y, Gold, Brent, DXY, USDJPY, EURJPY, CHFJPY. **Code only** (no model touches these numbers).
2. `⚡ BUGÜNÜN 3 MADDESİ` — the three most important items of the sections below (order of importance: touches one of my stocks →
   a big market move → reported by several sources).
3. `🗓 TAKVİM` — today / tomorrow / this week / later: earnings, central banks, data. My stocks' earnings dates (from Yahoo) are marked 📌.
   New SEC filings of my stocks since the last bulletin, one line each (code only): "KO filed a 10-Q. Agent 3 reads it on Sunday."
4. `🌍 MAKRO` — rates and central banks, inflation, oil and energy, currencies, geopolitics.
5. `💼 HİSSELERİM` — held and watching stocks: one line each; a news item that touches one of the card's 3 "things that would break
   the thesis" gets `↳ Tez bozucu N ile ilgili: "<the card's own sentence>"`. Stocks with nothing new: one line "Haber yok: …".
6. `🔭 İLGİ KONULARI` — AI and its infrastructure (semiconductors, memory / HBM, optical parts, data centres, power), then the rest.
7. `🔗 Kaynaklar` — numbered links.

**Writing rules:** neutral; no adjectives of judgement ("excellent", "important"); no advice; an opinion only with its owner
("According to Macquarie …"); no price targets, analyst ratings or intraday moves; "no news" is allowed, filler is not; one fact appears
once.

## 3. How a run works

```
08:00  gather (code)   posts since the last bulletin · my stocks + their thesis breaks · SEC filings · earnings dates
                        · market figures from `prices` · web searches (my stocks, interests, the week's calendar)
       write (strong)   one DeepSeek V4 Pro call → English items as JSON, each with its source ids
       check (code)     every number in an item must appear in its sources (else ⚠)
       translate (cheap) DeepSeek V4 Flash → Turkish, item by item, ids kept
       check (code)     every number in a Turkish item must equal one in its English item (else ⚠)
       render (code)    the template; the market table, SEC lines and thesis sentences come from code, never from a model
       save             English + Turkish into the database; the Turkish file to Drive `Bulletin/YYYY-MM-DD.md`
08:15  deliver          printed for Hermes (section 6, T1 decides how)
```

**The window:** posts and news since the previous bulletin (Monday therefore covers the weekend). The first run looks back 24 hours.

## 4. Slices (build order)

Each slice: tests first, then code, one commit; all tests pass before the next one. Fakes in tests; no real network in tests.

### Slice 0 — names and settings (docs only)

- `GLOSSARY.md`: `bulletin` (Bülten), `Bulletin/` (Drive), table `bulletins`, `shared/bulletin`, `shared/search`, setting block
  `bulletin:`, the `search` and `bulletin` commands.
- `settings.yaml` `bulletin:` — `hour: "08:15"`, `days: weekdays`, the market rows (name → source symbol), `interests` (topic → search
  query; first draft below), `max_searches: 25`, `post_chars: 3000` (how much of one post's text goes to the model).
- `docs/SCHEDULE.md`: job 6. `docs/telegram_setcommands.txt` / roadmap 10.2: the `search` command.

**First draft of `interests` (I correct it):**

| Topic | Query (English) |
|---|---|
| Markets and direction | `stock market outlook week` |
| Oil | `Brent crude oil supply OPEC Iran` |
| Dollar and rates | `Fed Treasury yields dollar index` |
| Japan | `Bank of Japan JGB yield yen` |
| AI infrastructure | `AI data center capex semiconductors` |
| Memory / HBM | `HBM DRAM memory prices supply` |
| Optical parts | `optical transceiver data center market` |
| Calendar | `earnings calendar central bank meetings this week` |

### Slice 1 — DeepSeek web search: `shared/search.py`

- `search(query, count=5, after=None) -> list[Hit]` — `POST https://api.deepseek.com/v1/tools/search`, `DEEPSEEK_API_KEY`
  (already in the Air's `.env`). `after` uses the query operator `after:YYYY-MM-DD`. A hit keeps `title`, `url`, `site_name`, `date`,
  `summary`, `snippet`, `rerank_score`.
- Every call is a row in `ai_calls` (`job = search`, `provider = deepseek`, `model = search`, cost from
  `settings.yaml` `pricing.deepseek_search_per_call: 0.00075`), so `/spend` and the monthly limit count it. No new table.
- An error (no key, HTTP error, timeout) raises `SearchError`; the bulletin then goes on without that search and says so in one line.
- **Not here:** agent 2's news step still uses Anthropic's tool. Moving it to this search is a separate decision.
- **Check (H):** `uv run python -m shared.search "Brent crude oil"` prints 5 titles, dates and the cost.

### Slice 2 — market figures

- The nightly price job (`shared/prices`) also fetches the bulletin's rows. Yahoo symbols: `^GSPC`, `^IXIC`, `^TNX`, `GC=F` (already),
  `BZ=F`, `DX-Y.NYB`, `JPY=X`, `EURJPY=X`, `CHFJPY=X`. A symbol with no history gets 3 months the first time, then 5 days as now.
- **Japan 10Y:** Yahoo has no reliable symbol. First choice: the Japanese Ministry of Finance's daily JGB yield file (free, previous
  day). Stored in `prices` as `JP10Y` with `source = mof`. If it cannot be read: the row shows `—` and the reason, nothing else stops.
- `shared/bulletin/market.py`: the last close, the close 1 month earlier (the last close on or before the same date a month ago) and the
  day before; percent for prices, basis points for yields.
- **Check (H):** `uv run python -m shared.prices` once, then `uv run python -m shared.bulletin --market` prints the table.

### Slice 3 — gather: `shared/bulletin/gather.py` (code only)

- Posts: `articles` published inside the window, both sites; title, tags, the one sentence, the first `post_chars` of the text.
- My stocks: `in_portfolio = 'yes'` or `status = 'watching'`; for each, the card's 3 thesis breaks (`card.last_thesis`), its tagged posts.
- SEC: each of my stocks' new 10-K / 10-Q / 20-F / 8-K since the last bulletin (the submissions list; 8-K items as plain words, e.g.
  5.02 = "a director or officer left or joined", 4.01 = "the auditor changed").
- Earnings dates of my stocks from Yahoo.
- Web searches: one per stock (`"<company> news"`, after the window start) + one per interest; at most `max_searches`.
- Every piece gets an id (`P12` post, `W3` web, `C2` card) so the model can cite it and the code can check it.

### Slice 4 — write, check, translate: `shared/bulletin/write.py`, `check.py`

- One `strong` call (DeepSeek V4 Pro first, the usual order after it) with the writing rules of section 2 and all gathered pieces.
  Answer: JSON `{"top3": [...], "calendar": [...], "macro": [...], "stocks": {"KO": [...]}, "interests": [...]}`, every item
  `{"text": "...", "sources": ["W3", "P12"], "thesis_point": 1|2|3|null}`. A broken JSON answer is asked again once.
- Number check (code): every number in an item (`104.6`, `7%`, `25 bp`, `3.6`, `$115`, `2030` …) must appear in the text of its cited
  sources, after normalising (thousand separators, `bn` / `trn`, `%`). An item that fails keeps its place with `⚠ rakam doğrulanamadı`.
- Translation: one `cheap` call (DeepSeek V4 Flash), items as JSON in, the same ids out. Section titles and fixed lines are not
  translated by the model; they are written in Turkish in the code.
- Translation number check (code): the numbers of each Turkish item must be the numbers of its English item (`104.6` = `104,6`).
  On a mismatch the English item is shown with `⚠ çeviri kontrolü`.

### Slice 5 — render, save, deliver: `shared/bulletin/__init__.py`, `__main__.py`

- `uv run python -m shared.bulletin` — build, save, print. `--dry` builds and prints but saves nothing. `--show` prints the last
  saved bulletin. `--market` prints only the table.
- Database **version 11**: table `bulletins` (`day` unique, `window_start`, `english` JSON, `turkish` text, `sources` JSON,
  `cost_usd`, `created_at`). The run is a `runs` row (`job = bulletin`) as for every job.
- Drive: `Bulletin/YYYY-MM-DD.md` (Turkish, with the links).
- A second run on the same day prints the saved bulletin again and spends nothing (`--force` builds a new one).
- No posts and no web results at all → a short bulletin with the numbers and the line "Kaynaklardan yeni bir şey gelmedi."

### Slice 6 — the on-demand search: command `search`

- `uv run python -m shared.commands search "why did Pop Mart fall"` — an information command (no confirmation, nothing changes):
  DeepSeek search (5 hits) → one `cheap` call writes a short, neutral answer with numbered sources. Cost about 0.01 $.
- In Telegram in plain words ("ara: Pop Mart neden düştü"), like the other commands since 2026-10-19.
- If I ask for an opinion in the question, the answer may give one, marked as the model's view.

### Slice 7 — Dragonomi by the login link: `agents/eye/magic_link.py`

- `uv run python -m agents.eye.magic_link dragonomi '<link from the e-mail>'` — checks that the link is the site's own sign-in link
  (`https://<dragonomi host>/members/?token=…`), opens it **once** without following the redirect, takes the `ghost-members-ssr` and
  `ghost-members-ssr.sig` cookies from the answer and writes `DRAGONOMI_COOKIE` into `.env` with `set_cookie`'s writer. It never prints
  the cookie or the token. A used or expired link → "the link was already used or is too old; ask for a new one".
- Why it is safe enough (my decision, 2026-10-28, "Yol B"): what passes through Telegram is a **one-time** link, worthless once the Air
  has used it; the long-lived cookie never leaves the Air.
- Then: `session_check dragonomi` (H) → if the body is not found, Claude fixes the selector in `sites.py` → Claude removes `dragonomi`
  from `eye.skip_sites` → the next pass finds about 1,000+ waiting addresses → `uv run python -m agents.eye --accept-many` once (reads the
  newest, marks the older ones as seen).
- **Not known until tried:** whether this Ghost site still signs in with a plain link (some newer Ghost versions use a 6-digit code). If
  it does not work: back to "Yol A" (the cookie by hand at home).

## 5. Cost (estimate, DeepSeek prices in `settings.yaml`)

| Part | Per bulletin | Per month (22 weekdays) |
|---|---|---|
| Write (V4 Pro, ~40k tokens in, ~4k out) | ~0.07 $ | ~1.5 $ |
| Translate (V4 Flash) | ~0.01 $ | ~0.2 $ |
| Searches (~20 × 0.00075 $) | ~0.015 $ | ~0.35 $ |
| **Total** | **~0.10 $** | **~2–2.5 $** |

On-demand searches: about 0.01 $ each. The monthly AI limit (`budget.ai_monthly_max_usd: 30`) counts all of it.

## 6. Air steps (H, in this order)

| # | Step | Pass |
|---|---|---|
| T1 | **Delivery test, before the job is registered:** a script that prints ~9,000 characters in 6 parts. Does Hermes send it whole, split, or cut? | We know how a long output arrives. If it is cut: `--part N` prints one section, and job 6 becomes 6 short jobs 08:15–08:20 (decided after T1). |
| T2 | `git pull` · `uv run python -m shared.db upgrade` (10 → 11) · `uv run pytest -q` | all pass |
| T3 | `uv run python -m shared.search "Brent crude oil"` | 5 hits, a cost line |
| T4 | `uv run python -m shared.prices` · `uv run python -m shared.bulletin --market` | 10 rows; Japan 10Y has a value or a reason |
| T5 | `uv run python -m shared.bulletin --dry` | the bulletin; **I read it** |
| T6 | Register job 6: weekdays 08:15, `uv run python -m shared.bulletin` | the next morning's bulletin arrives |
| T7 | Dragonomi (slice 7): I ask Dragonomi for a login link, send it to Hermes; H runs `magic_link`, then `session_check dragonomi` | "not gated", text found |

**Two weeks after T6:** a 10-minute look together: which section helps, which does not (the template may change then).

## 7. Done when

- All tests pass (the 677 existing ones and the new ones); T1–T6 passed; three bulletins in a row arrived on time and I read them.
- The audit: one separate session after the first week, with the usual prompt (`IMPLEMENTATION_PLAN.md` section 4).
- `AGENTS.md` status and the project map updated.

## 8. Open questions (answer before or during the build)

1. Number check fails → the item stays with `⚠` (my proposal) or is left out?
2. The on-demand `search` answer: Turkish like the bulletin (my proposal) or English like the rest of the system?
3. The `interests` table above: correct or add topics.

## 9. Not in this plan, on purpose

- Agent 2's news step on DeepSeek search (a separate decision; the bulletin does not touch scores).
- A like / dislike button on items (the two-week look replaces it for now).
- China / HK stocks in agents 2 and 3 (Dragonomi's company names only appear in the bulletin as information).
- Weekend bulletins.
