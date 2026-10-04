---
doc: Air setup (step 0)
date: 2026-10-04
status: checklist
publish: no
---

# Step 0 — MacBook Air setup checklist

Roadmap section 10.3. The Air (M2, 16 GB, 256 GB) runs the system 7/24; no code is written on it (it only `git pull`s).
**Done when** (roadmap section 8): I can message Hermes on Telegram, a scheduled test job writes a file to Drive, and a
scheduled job's message arrives on Telegram.
Estimated time: 1.5–2 hours. "Me" = the user; "Claude" = prepared in the development session.

## Phase 1 — The Mac itself (~20 min) · me

- [ ] Update macOS, restart.
- [ ] **A separate macOS user** (e.g. `agents`) so the agents cannot see my personal files.
- [ ] **FileVault on** (disk encryption). Side effect: after a power cut the Mac does nothing until I enter the password —
      log in over Screen Sharing after an outage.
- [ ] Firewall on (System Settings → Network → Firewall).
- [ ] **No sleep:** System Settings → Battery → Options → "Prevent automatic sleeping on power adapter when the display is off";
      "Wake for network access" if offered.
- [ ] Charger always connected, lid open; "Optimized battery charging" stays on.
- [ ] **Automatic updates:** download only, do not install (otherwise the Mac restarts by itself at night).
- [ ] **Remote access:** System Settings → General → Sharing → **Screen Sharing** and **Remote Login (SSH)** on, so I can reach
      the Air from the main Mac.

## Phase 2 — Tools and the project (~20 min) · me (commands from Claude)

- [ ] Developer tools: `xcode-select --install` (brings git).
- [ ] `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] **GitHub, read-only:** add a read-only **deploy key** for the repo (the Air only pulls; if it were compromised nobody could
      write to the code).
- [ ] `git clone … ~/investment-agents`
- [ ] **`.env`** (secrets): Anthropic, DeepSeek, OpenAI, OpenRouter keys + the SEC contact (`SEC_UA`). `chmod 600 .env`.
      **Never committed.** Template: `.env.example` (Claude).
- [ ] Database folder `~/investment-agents-data/` — **outside Drive** (rule: SQLite never goes in the Drive folder).
- [ ] In `~/investment-agents`: `uv sync`, then `uv run python -m shared.db init` (creates the database in that folder) and
      `uv run python -m shared.db info` (version 1, every table with 0 rows).

## Phase 3 — Google Drive (~15 min) · me

- [ ] Install "Google Drive for desktop", sign in.
- [ ] Setting: **Mirror files** (files also on disk; no trouble when the internet drops; our files are small).
- [ ] Folders: `Investing/` with `Inbox/`, `Weekly/`, `Backup/`, `Stocks/` (the test script below also creates any that are missing).
- [ ] Put the full path of `Investing/` into `.env` as `DRIVE_DIR` (e.g.
      `/Users/agents/Library/CloudStorage/GoogleDrive-<account>/My Drive/Investing`).

## Phase 4 — Telegram bot (~15 min) · me (menu text from Claude)

- [ ] **@BotFather** → `/newbot` → a name → copy the **bot token**. It is a password: never paste it into any chat; it goes
      straight into `.env` on the Air.
- [ ] My Telegram **user ID** (e.g. via @userinfobot): the bot talks **only to me**.
- [ ] `/` menu: @BotFather → `/setcommands` → choose the bot → paste the whole of `docs/telegram_setcommands.txt`
      (also printed by `uv run python -m shared.commands --setcommands`).

## Phase 5 — Hermes (~30 min) · me, checked together

- [ ] Install: `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`,
      then `hermes --version`.
- [ ] **Log in with the ChatGPT subscription:** `hermes auth add openai-codex` → open the link, sign in to ChatGPT, paste the
      code back. Hermes never sees the password. If it fails: fallback DeepSeek V4 Pro with its API key (section 10.1).
- [ ] **Connect Telegram:** `hermes gateway setup` → the bot token and **only my user ID**.
- [ ] **Run as a service:** `hermes gateway install`, `hermes gateway start` (a launchd service; starts again after a restart).
- [ ] ⚠️ **Limit Hermes's powers.** By default Hermes is an agent that can run terminal commands; our rule is "the command list
      only" (section 10.2). Turn on its approval mode and restrict terminal use to our command scripts plus one read-only way to look at the
      database and the cards (for my free questions) — done together, from its docs.
- [ ] **Command clashes:** compare Hermes's built-in commands with ours (`/help`, `/model`, `/status` may clash); rename ours if so.
- [ ] Agents run as **script-only cron jobs (no LLM)** — scheduling costs no tokens.

## Phase 6 — OpenRouter (~5 min) · me

- [ ] Account + an API key with a **monthly limit of 15 $**; key into `.env`.
- [ ] No credit needed yet (my API credits come first); optionally 5 $ as a fallback.

## Phase 7 — Done? Tests (~15 min) · together

| # | Test | Passes if… |
|---|---|---|
| 1 | Write "hello" to Hermes on Telegram | an answer comes (from the ChatGPT subscription) |
| 2 | Write to the bot from another Telegram account | **no answer** (the bot is mine only) |
| 3 | Scheduled test script (no AI, hourly): `cd ~/investment-agents && uv run python -m shared.drive test` | a dated test file `drive-test-….md` appears in `Investing/Inbox/` and **shows up in Drive on my phone** |
| 4 | Restart the Air | after my password, Hermes starts by itself and Telegram works |
| 5 | Screen Sharing from the main Mac | it connects |
| 6 | The same scheduled script prints a short message ("DRIVE TEST …") | the message arrives on Telegram — the path every agent's messages will use (roadmap section 3, "How messages travel") |

## Prepared by Claude before the setup

Built in phase 0 (2026-10-04):

1. `.env.example` (repo root) — which keys go where (empty template). Copy it to `.env` and fill it in.
2. The Telegram `/setcommands` text: `docs/telegram_setcommands.txt` (copy-paste).
3. The test script that writes a file to Drive and prints a message: `uv run python -m shared.drive test` (code in
   `shared/drive/__main__.py`). It also writes a `runs` row, so `/status` shows it (needs `shared.db init` first).

Other step-0 helpers in the code: `/help`, `/status`, `/undo` work (`uv run python -m shared.commands status`); the read-only
path for free questions is `uv run python -m shared.ask tables | sql "SELECT …" | card KO` — this is what Hermes's terminal
is limited to, together with `shared.commands`.

## Later (not step 0)

- Playwright + the one-time logins to Emtia Defteri and Dragonomi (with agent 1).
- The nightly SQLite backup to `Investing/Backup/` is built (`uv run python -m shared.backup`); it is scheduled with the other
  jobs in phase 6.

## Sources

- [Hermes Agent — Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)
- [Hermes Agent — CLI commands](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)
- [Hermes Agent — Messaging gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/)
- [Hermes Agent — Script-only cron jobs (no LLM)](https://hermes-agent.nousresearch.com/docs/guides/cron-script-only)
- [Hermes Agent — Model providers](https://hermes-agent.nousresearch.com/docs/integrations/providers)
