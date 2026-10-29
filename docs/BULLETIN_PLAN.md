---
doc: Morning bulletin — implementation plan
date: 2026-10-28
status: approved (2026-10-28)
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
   Japan 10Y, Gold, Brent, DXY, USDJPY, EURJPY, CHFJPY. **Code only** (no model touches these numbers). One row per line with
   `·` between the parts (`S&P 500 · 7.743,98 · 1 ay ▲ %0,8 · gün ▲ %0,3`): Telegram's font is not monospaced, so aligned columns
   would not line up. A figure whose last close is older than the others' shows its date.
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
- `settings.yaml` `hours.bulletin: "08:15"` (weekdays) and `bulletin:` — the market rows (name → source symbol), `interests` (topic → search
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
  (already in the Air's `.env`). The query gets `lang:en` (English sources only) and, with `after`, `after:YYYY-MM-DD`; with its operators it is at most 128 characters. **Built 2026-10-28** (15 tests). A hit keeps `title`, `url`, `site_name`, `date`,
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
- **Built 2026-10-28** (`shared/prices/mof.py`, `shared/bulletin/market.py`, 22 tests). Checked live from the cloud session with a
  throwaway database: all 9 Yahoo symbols answer with 3 months of closes; **`^TNX` is already in percent** (5.045, no scaling);
  the table printed from real data. **Not checked:** the Ministry of Finance file (the cloud session cannot reach `mof.go.jp`; the
  parser follows the file's known layout) — the Air check T4 is its first real read; if the layout differs, only `mof.parse` changes.
  **T4, first real read (2026-10-28, Hermes):** the layout was right (the parser read the file back to 1974) but the plausibility check
  refused Japan's negative yield of 2016 (−0.02). Fixed the same day: negative yields are real (range −5 … 30 %), and the check applies
  only to the days we keep (the last 120), so an odd row from 1974 cannot stop the read. **Second T4 finding (same day):** the
  history file ends on 09-30 (the Ministry updates it only now and then), so the first read now takes the small current file too;
  the figures table's date marker (`(30.09)`) made the gap visible at once.
- **Check (H):** `uv run python -m shared.prices` once, then `uv run python -m shared.bulletin --market` prints the table.

### Slice 3 — gather: `shared/bulletin/gather.py` (code only) — **built 2026-10-28** (17 tests)

- **Window:** the bulletin time (08:15) of the last weekday before today's Turkey date (Wednesday → Tuesday, Monday → Friday). Slice 5
  replaces it with "since the last saved bulletin".
- **Posts** (`P<articles.id>`): `articles` published since the window start, both sites. The first `full_posts` (40) — those about my
  stocks first, then the newest — come with title, tags, the one English sentence and up to `post_chars` (3,000) of the text; the
  rest with title, tags and the sentence only (a day has 60–150 posts; this keeps the model call at about 40k tokens). A post is "about"
  a stock of mine when one of its tags is a **confirmed** company tag mapped to it. A post the site cut for non-members says so.
  **For slice 4:** the post text is Turkish (numbers like `104,6`); the sentence is English.
- **My stocks:** `in_portfolio = yes` or `status = watching`, held first; each with the 3 "things that would break the thesis"
  parsed from its card's newest thesis (`breaks`; empty when the card has none yet).
- **SEC filings** (`F<n>`): 10-K / 10-Q / 20-F and 8-K of my stocks **accepted** since the window start (by acceptance time, so a
  filing is never listed twice); 8-K items in plain words (`EIGHT_K`; an 8-K with only the exhibits item 9.01 is skipped).
- **Earnings dates** (`E<n>`): Yahoo's next date for each of my stocks, if within `earnings_days` (45).
- **Web hits** (`W<n>`): the searches go held stocks → the 8 interest topics → watched stocks, at most `max_searches` (25); `after:` is
  the day before the window starts; a URL appears once; a hit dated before that day is dropped. A failed search is a note
  (`pack.notes`); a dead key / empty balance / monthly limit skips the rest.
- **Check (H):** `uv run python -m shared.bulletin --gather` prints counts and the first items (`--no-search` skips the searches).

### Slice 4 — write, check, translate: `shared/bulletin/write.py`, `check.py`, `translate.py` — **built 2026-10-28** (46 tests, fake model)

- **Writer** (`write.py`): one `strong` call (DeepSeek V4 Pro first, the usual order after it). It sees the window, my stocks with their
  3 thesis breaks, and the posts and web hits (not the figures table, not the SEC lines, not my stocks' earnings dates: those are
  code). It answers JSON: `calendar` (with `when`: today / tomorrow / week / later), `macro`, `stocks` (per ticker, with
  `thesis_point` 1–3 or null), `interests` (group `ai_infrastructure` or `other`); every item has `sources` (piece ids) and the three
  most important items carry `rank` 1–3 (the "today's 3 items" digest: **the digest repeats those items**, the rule "a fact once"
  is for the sections themselves). A bad JSON answer is asked once more.
- **What code does with the answer:** an item with no source that exists is dropped; so is one with advice, an analyst rating, an
  upgrade / downgrade or a price target (`check.STYLE`), one over 600 characters, one for a stock that is not mine; a thesis point
  the card does not have becomes null; a section over its limit (calendar 8, macro 8, interests 10, 3 a stock) keeps the ranked
  items and the order. Every drop is a line in `draft.notes`.
- **Number check** (`check.py`, code): every number of an item must be in the pieces it cites, read both ways (`104.6` = `104,6`;
  `1.000` may be a thousand or a decimal one; years, signs, units and ordinals are ignored). An item that fails stays and carries a
  flag (`⚠ rakam doğrulanamadı` in the render, slice 5).
- **Translation** (`translate.py`): one `cheap` call (DeepSeek V4 Flash) for all items as JSON; the Turkish numbers must be exactly
  the English item's (`Q3` ↔ `3. çeyrek` is fine: ordinals are words). A translation that fails the comparison, a missing one or a
  failed call leaves the English item with a note (`çeviri kontrolü` / `çeviri eksik` / `çeviri yapılamadı`); the bulletin goes on.
- **Not here (slice 5):** the Turkish section titles and fixed lines, the figures table, the SEC and earnings lines (`📌`), "Haber yok:
  …" for stocks with no item, the source tags `[ED]` `[DR]` `[W]` with numbered links (each item shows its tag and link number),
  saving and delivery.
- **Check (H):** `uv run python -m shared.bulletin --draft` runs gather → write → check → translate and prints every item with its
  sources, flags and Turkish text (about 0.1 $; saves and sends nothing). **The first real model run: read it and tell me what to tune.**

### Slice 5 — render, save, deliver: `shared/bulletin/render.py`, `run.py` — **built 2026-10-29** (16 tests)

- **Render** (`render.py`, code only): the approved template in Turkish — header with the date, the figures table, "Bugünün 3 maddesi"
  (the ranked items, repeated), calendar (Bugün / Yarın / Bu hafta / İleride, then "Yeni başvurular"), macro, my stocks, interests
  (AI altyapısı / Diğer), sources. Empty sections are left out, except my stocks ("İzleme listesi boş…" when I hold or watch none).
  The earnings dates of my stocks and their new SEC filings are code lines in Turkish with `📌` (a 10-K / 10-Q says "3. ajan Pazar günü
  okuyacak"; an 8-K says what it reports, from SEC's item numbers). A stock with no item is named in "Haber yok: …". A thesis point puts
  the card's own sentence under the item (`↳ Tez bozucu 2 ile ilgili: "…"`, in the card's language, English).
- **Source tags:** each item ends with `[ED1, W2]`: ED / DR = a post of Emtia Defteri / Dragonomi, W = the web; the number is the
  position in the list "🔗 KAYNAKLAR" at the end (numbered by first use; title and link; at most 40).
- **Warnings in the text:** `⚠ rakam doğrulanamadı` (a number no cited piece has) · `⚠ çeviri kontrolü: rakamlar uyuşmuyor` (the English item
  is shown) · a footer `ℹ️ N kaynak ya da adım alınamadı` when searches, SEC, Yahoo or the translation failed (details in `bulletins.notes`).
- **Job** (`run.py`, `python -m shared.bulletin`): gather → write → check → translate → render → save → print. Database **version 11**:
  table `bulletins` (a row per bulletin: day, window, the English items, the Turkish text, sources, notes, cost; `--force` marks the old
  row void, nothing is deleted). Drive: `Bulletin/YYYY-MM-DD.md` (Turkish, `publish: no`). A second run the same day prints the saved
  text and spends nothing. **The window** of a bulletin starts where the previous saved one ended (at most 4 days back; the very first:
  the last weekday's 08:15). **A failed writer** still sends the figures and the code lines with a warning, and is **not saved**, so the
  next run covers that window again. `--dry` builds and prints without saving; `--show` prints the last saved one.
- **Check (H):** `--dry` on the copy of the production database (the text I would receive), then job 6 is registered (T6). **T5c (2026-10-29) read:** the first real bulletin; the figures table was empty on the copy because production had not run the new price job; DeepSeek shortens some result addresses with "..." (shown without a link); Hermes' terminal tool stops a command at 300 s, so long checks run one per call or in the background (a scheduled job has no such limit).

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
| T1 | **Delivery test, before the job is registered:** a throwaway script-only Hermes job (manual run, no schedule) that prints ~8,500 characters in 6 parts (`PART 1` … `PART 6`); I count the messages that arrive **in Telegram** (Hermes cannot see this: run from its terminal tool the output never reaches Telegram, learned 2026-10-28). Does it arrive whole, split, or cut? Then the job is removed. | We know how a long output arrives. If it is cut: `--part N` prints one section, and job 6 becomes 6 short jobs 08:15–08:20 (decided after T1). **Result (2026-10-28): passed.** 8,453 characters arrived as **3 messages** labelled (1/3) (2/3) (3/3), in order, nothing lost; the scheduler splits at about 4,000 characters (possibly mid-section) and adds a header line `Cronjob Response: <job> (job_id: …)` and a footer ("To stop or manage this job…"). So job 6 stays **one job** and `--part` is not needed. Learned on the way: Hermes' cron requires a schedule (a paused job cannot be run by hand), so job 6 gets its weekday schedule at once; the test job had to be given a far date and deleted afterwards. |
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

## 8. Answered (my decisions, 2026-10-28)

1. Number check fails → the item **stays**, marked `⚠`.
2. The on-demand `search` answer is **Turkish**, like the bulletin, asked from Telegram in plain words.
3. The 8 `interests` topics above are right for now.
4. Before slice 1, I ask DeepSeek itself for its Search API details (the docs could not be read from the cloud session); its answer
   fixes the request and response fields of `shared/search.py`.

## 9. Not in this plan, on purpose

- Agent 2's news step on DeepSeek search (a separate decision; the bulletin does not touch scores).
- A like / dislike button on items (the two-week look replaces it for now).
- China / HK stocks in agents 2 and 3 (Dragonomi's company names only appear in the bulletin as information).
- Weekend bulletins.
