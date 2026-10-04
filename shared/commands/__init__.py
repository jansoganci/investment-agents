"""The command list Hermes may run (roadmap section 10.2). Hermes calls:

    uv run python -m shared.commands <name> [args …]          information, or the preview of a change
    uv run python -m shared.commands <name> [args …] --yes    runs the change after my `yes`

Rules: (1) a command that changes something first prints exactly what will change and runs only with `--yes`;
(2) every change is written to `command_log` and gets a number, shown when it is done; (3) `/undo` marks rows
`void`, never deletes. Hermes never edits tables or files itself.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Callable

from shared import clock
from shared import db as dbmod


@dataclass
class Applied:
    text: str                       # what changed, one line, plain English
    target_table: str | None = None
    target_id: int | None = None


@dataclass
class Plan:
    preview: list[str]              # exactly what will change
    confirm_args: list[str]         # the exact command to run after `yes` (without --yes)
    apply: Callable[[sqlite3.Connection, int], Applied]


class Refused(Exception):
    """A command that cannot run; the message tells me why. Nothing changes."""


@dataclass
class Command:
    name: str
    description: str                # Telegram `/` menu (3–256 characters)
    usage: str
    changes: bool = False
    phase: int = 0                  # the phase that builds it (docs/IMPLEMENTATION_PLAN.md)
    info: Callable[[sqlite3.Connection, list[str]], str] | None = None
    plan: Callable[[sqlite3.Connection, list[str]], Plan] | None = None
    built: bool = field(init=False, default=False)

    def __post_init__(self):
        self.built = self.info is not None or self.plan is not None


REGISTRY: dict[str, Command] = {}

# The Telegram `/` menu, in the order of roadmap section 10.2.
MENU: list[str] = []


def register(cmd: Command, in_menu: bool = True) -> Command:
    REGISTRY[cmd.name] = cmd
    if in_menu and cmd.name not in MENU:
        MENU.append(cmd.name)
    return cmd


def setcommands_text() -> str:
    """The text for @BotFather → /setcommands."""
    return "\n".join(f"{name} - {REGISTRY[name].description}" for name in MENU)


def _confirm_text(cmd: Command, plan: Plan) -> str:
    lines = [f"CONFIRM · /{cmd.name}", "Will change:"]
    lines += [f"- {p}" for p in plan.preview]
    lines += [
        "Nothing changes until you say yes.",
        f"On yes, run: uv run python -m shared.commands {' '.join(plan.confirm_args)} --yes",
    ]
    return "\n".join(lines)


def _run_change(cmd: Command, args: list[str], yes: bool) -> tuple[int, str]:
    conn = dbmod.connect()
    try:
        if not yes:
            return 0, _confirm_text(cmd, cmd.plan(conn, args))
        conn.execute("BEGIN IMMEDIATE")  # one writer at a time; others wait (busy timeout)
        try:
            plan = cmd.plan(conn, args)  # checked again inside the transaction
            cur = conn.execute(
                "INSERT INTO command_log (command, args, created_at) VALUES (?, ?, ?)",
                (cmd.name, " ".join(args), clock.utc_iso()),
            )
            number = cur.lastrowid
            done = plan.apply(conn, number)
            conn.execute(
                "UPDATE command_log SET summary=?, target_table=?, target_id=? WHERE id=?",
                (done.text, done.target_table, done.target_id, number),
            )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        return 0, f"DONE · change #{number}\n{done.text}\nTo cancel it: /undo {number}"
    finally:
        conn.close()


def run(argv: list[str]) -> tuple[int, str]:
    """Returns (exit code, text to print). 0 = ok, 1 = refused, 2 = not on the list."""
    yes = "--yes" in argv
    args = [a for a in argv if a != "--yes"]
    if not args:
        return 2, "usage: python -m shared.commands <command> [args …] [--yes] · send /help for the list"
    name, args = args[0].lstrip("/").lower(), args[1:]
    cmd = REGISTRY.get(name)
    if cmd is None:
        return 2, f"Not on the command list: /{name}. Send /help for the list."
    if not cmd.built:
        return 1, f"/{name} is not built yet (phase {cmd.phase})."
    try:
        if cmd.changes:
            return _run_change(cmd, args, yes)
        conn = dbmod.connect_readonly()
        try:
            return 0, cmd.info(conn, args)
        finally:
            conn.close()
    except Refused as exc:
        return 1, str(exc)
    except dbmod.DatabaseMissing as exc:
        return 1, str(exc)


from shared.commands import builtin  # noqa: E402,F401 — registers the commands
