"""The command list of roadmap section 10.2. Phase 0 builds /help, /status and /undo; the others are listed in the
Telegram menu and answer "not built yet (phase N)" until their phase builds them."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

from shared import clock
from shared import db as dbmod
from shared.commands import Applied, Command, Plan, Refused, MENU, REGISTRY, register

# --- Information ------------------------------------------------------------------------------------------------


def _help(conn: sqlite3.Connection, args: list[str]) -> str:
    lines = ["COMMANDS"]
    for name in MENU:
        cmd = REGISTRY[name]
        later = "" if cmd.built else f" (from phase {cmd.phase})"
        lines.append(f"/{name} — {cmd.description}{later}")
    lines.append("You can also ask me anything; I read the database and the cards, read-only.")
    return "\n".join(lines)


def _status(conn: sqlite3.Connection, args: list[str]) -> str:
    lines = [f"STATUS · {clock.show(clock.now_utc())} (Turkey time)", f"Database version {dbmod.version(conn)}"]
    last = conn.execute(
        """
        SELECT job, status, started_at, ended_at, cost_usd, error FROM runs r
        WHERE id = (SELECT max(id) FROM runs WHERE job = r.job)
        ORDER BY job
        """
    ).fetchall()
    if not last:
        lines.append("No runs yet.")
    else:
        lines.append("Last run of each job:")
        for job, status, started, ended, cost, error in last:
            line = f"- {job}: {status} · {clock.show(started)}"
            if cost:
                line += f" · ${cost:.2f}"
            if status == "error" and error:
                line += f" · {error}"
            lines.append(line)
    since = clock.utc_iso(clock.now_utc() - timedelta(days=7))
    errors = conn.execute("SELECT count(*) FROM runs WHERE status='error' AND started_at >= ?", (since,)).fetchone()[0]
    lines.append(f"Errors in the last 7 days: {errors}")
    return "\n".join(lines)


# --- /undo ------------------------------------------------------------------------------------------------------


def _has_void_column(conn: sqlite3.Connection, table: str) -> bool:
    return any(r[1] == "void" for r in conn.execute(f'PRAGMA table_info("{table}")'))


def _undo(conn: sqlite3.Connection, args: list[str]) -> Plan:
    if len(args) > 1 or (args and not args[0].lstrip("#").isdigit()):
        raise Refused("usage: /undo  or  /undo <number>")
    if args:
        number = int(args[0].lstrip("#"))
        row = conn.execute(
            "SELECT id, command, args, summary, target_table, target_id, status, created_at FROM command_log WHERE id=?",
            (number,),
        ).fetchone()
        if row is None:
            raise Refused(f"There is no change #{number}.")
    else:
        row = conn.execute(
            "SELECT id, command, args, summary, target_table, target_id, status, created_at FROM command_log "
            "WHERE status='done' AND command != 'undo' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise Refused("Nothing to undo.")
    number, command, cargs, summary, table, target_id, status, created = row
    if status == "void":
        raise Refused(f"Change #{number} is already cancelled.")
    if command == "undo":
        raise Refused(f"Change #{number} is itself an undo; send the right command again instead.")
    if not (table and target_id and _has_void_column(conn, table)):
        raise Refused(f"Change #{number} (/{command}) cannot be undone by /undo yet.")

    def apply(conn: sqlite3.Connection, undo_id: int) -> Applied:
        conn.execute(f'UPDATE "{table}" SET void=1, voided_by=? WHERE id=?', (undo_id, target_id))
        conn.execute("UPDATE command_log SET status='void', voided_by=? WHERE id=?", (undo_id, number))
        return Applied(f"Cancelled change #{number} ({f'/{command} {cargs}'.rstrip()}).", "command_log", number)

    preview = [
        f"cancel change #{number}: /{command} {cargs} · {clock.show(created)} (Turkey time)".rstrip(),
        f"what it did: {summary}",
        "the row is marked void and kept; nothing is deleted",
    ]
    return Plan(preview, ["undo", str(number)], apply)


# --- The menu (roadmap section 10.2, in its order) ------------------------------------------------------------------

_MENU = [
    # A. Information
    Command("help", "Lists all commands with a short description", "/help", info=_help),
    Command("summary", "Shows the latest Sunday summary again", "/summary", phase=6),
    Command("green", "The green list: type, grade, price line", "/green", phase=1),
    Command("candidates", "This week's candidates with scores and reasons", "/candidates", phase=5),
    Command("card", "Summary of the latest card entry and its Drive link", "/card KO", phase=1),
    Command("portfolio", "Holdings, benchmark against SPY and gold, total wealth", "/portfolio", phase=3),
    Command("missing", "Missing figures waiting for me", "/missing", phase=1),
    Command("spend", "This month's AI spend by provider and what is left", "/spend", phase=2),
    Command("model", "Which job runs on which model; with arguments, changes it", "/model · /model strong gpt-6-sol",
            phase=2),
    Command("status", "System health: when each job last ran, any errors", "/status", info=_status),
    # B. Actions
    Command("watch", "Start watching a stock (agent 3 keeps its card)", "/watch KO", changes=True, phase=1),
    Command("archive", "Archive a stock: no new analysis or spend", "/archive KO", changes=True, phase=1),
    Command("unarchive", "Bring an archived stock back to watching", "/unarchive KO", changes=True, phase=1),
    Command("bought", "Record a buy: quantity, ticker, price", "/bought 10 KO 85.65", changes=True, phase=3),
    Command("sold", "Record a sale: quantity, ticker, price", "/sold 5 KO 92.10", changes=True, phase=3),
    Command("gold", "Record a gold purchase: grams and TL price per gram", "/gold 1 4689", changes=True, phase=3),
    Command("bes", "Record this month's BES payment and the BES total (TL)", "/bes 8670 245000", changes=True,
            phase=3),
    Command("analyze", "Run agent 3 now (shows the estimated cost first)", "/analyze KO", changes=True, phase=1),
    Command("closewarning", "Close a warning on a card, with the reason", "/closewarning KO U1 <reason>",
            changes=True, phase=2),
    Command("thesis", "Add my correction of the thesis as a note", "/thesis KO <point>", changes=True, phase=2),
    Command("note", "Add my free note to a card", "/note KO <text>", changes=True, phase=2),
    Command("data", "Enter a missing figure I was asked for", "/data NKE 2026 interest 0.25bn", changes=True,
            phase=1),
    Command("tag", "Fix a wrong tag mapping", "/tag rio-tinto RIO", changes=True, phase=4),
    Command("subsector", "Approve a new subsector", "/subsector add Uranium Energy", changes=True, phase=4),
    Command("undo", "Cancel my last change, or change #N; nothing is deleted", "/undo · /undo 42", changes=True,
            plan=_undo),
]

for _cmd in _MENU:
    register(_cmd)
