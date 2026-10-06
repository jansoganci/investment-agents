"""Phase 2 commands: my words on a card (roadmap section 10.2, "Card").

    /note KO <text>                       my free note on the card
    /thesis KO <corrected point>          my correction of the AI's thesis, as a note; the old thesis stays
    /closewarning KO U1 <reason>          closes a warning; it stays closed while its condition is the same

All three append a dated note to `card.md` (append-only) and a row to `card_entries`. /undo adds a dated "withdrawn"
note; nothing is deleted (a withdrawn /closewarning reopens the warning).
"""

from __future__ import annotations

import re

from shared import clock, drive
from shared.commands import UNDO, Applied, Command, Plan, Refused, register
from shared.commands.stocks import _stock


def _card_path(conn, ticker: str):
    stock = _stock(conn, ticker)
    if stock is None:
        raise Refused(f"{ticker} is not in the system.")
    path = drive.find_card(ticker)
    if path is None or not path.exists():
        raise Refused(f"{ticker} has no card yet (it opens with the first analysis: /analyze {ticker}).")
    return stock, path


def _split(args: list[str], usage: str, words_after: int) -> tuple[str, list[str], str]:
    if len(args) < 1 + words_after + 1 or not re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", args[0]):
        raise Refused(f"usage: {usage}")
    return args[0].upper(), args[1:1 + words_after], " ".join(args[1 + words_after:]).strip()


def _open_warnings(path) -> list[str]:
    from agents.analysis import card

    text = path.read_text(encoding="utf-8")
    last = [e for e in card.entries(text) if e["record"] == "fundamental"]
    if not last:
        return []
    warnings = card._yaml_of(last[-1]["body"]).get("warnings") or []
    closed = card.closed_warnings(text)
    return [w["code"] for w in warnings if w["code"] not in closed]


def _note_plan(command: str, ticker: str, stock: dict, path, body: str, preview: str, confirm_args: list[str],
               before: dict | None = None) -> Plan:
    def apply(conn, number):
        from agents.analysis import card

        day = clock.today_local()
        cur = conn.execute("INSERT INTO card_entries (stock_id, date, record, who, source, command_id, created_at) "
                           "VALUES (?, ?, 'note', 'user', ?, ?, ?)", (stock["id"], day, f"/{command}", number, clock.utc_iso()))
        card.append(path, card.note_entry(day, body), {"last_entry": day})  # the card last
        conn.execute("UPDATE stocks SET last_entry = ? WHERE id = ?", (day, stock["id"]))
        return Applied(f"{ticker}: {preview}", "card_entries", cur.lastrowid, before=before or {"ticker": ticker, "body": body})

    return Plan([f"a dated note on the card of {ticker}: {preview}"], confirm_args, apply)


def _note(conn, args):
    ticker, _, text = _split(args, "/note KO <text>", 0)
    stock, path = _card_path(conn, ticker)
    return _note_plan("note", ticker, stock, path, text, text, ["note", ticker, *text.split()])


def _thesis(conn, args):
    ticker, _, text = _split(args, "/thesis KO <corrected point>", 0)
    stock, path = _card_path(conn, ticker)
    body = f"Thesis correction: {text} (the thesis written before stays; the next check reads this note)"
    return _note_plan("thesis", ticker, stock, path, body, body, ["thesis", ticker, *text.split()])


def _closewarning(conn, args):
    ticker, (code,), reason = _split(args, "/closewarning KO U1 <reason>", 1)
    code = code.upper()
    stock, path = _card_path(conn, ticker)
    open_now = _open_warnings(path)
    if code not in open_now:
        raise Refused(f"{ticker} has no open warning {code}." + (f" Open: {', '.join(open_now)}." if open_now else " None are open."))
    body = f"Warning {code} closed: {reason}"
    return _note_plan("closewarning", ticker, stock, path, body, body + " (it is not reopened unless the condition changes)",
                      ["closewarning", ticker, code, *reason.split()], before={"ticker": ticker, "code": code})


def _undo_note(conn, log: dict):
    before = log["before"] or {}
    ticker = before.get("ticker")
    path = drive.find_card(ticker) if ticker else None
    if path is None or not path.exists():
        raise Refused(f"Change #{log['id']}: the card of {ticker} is gone.")
    code = before.get("code")
    text = (f"Warning {code} reopened — change #{log['id']} withdrawn (/undo)" if code
            else f"Change #{log['id']} withdrawn (/undo): the note above no longer stands")
    stock = _stock(conn, ticker)

    def do(conn, undo_id):
        from agents.analysis import card

        day = clock.today_local()
        conn.execute("INSERT INTO card_entries (stock_id, date, record, who, source, command_id, created_at) "
                     "VALUES (?, ?, 'note', 'user', '/undo', ?, ?)", (stock["id"], day, undo_id, clock.utc_iso()))
        card.append(path, card.note_entry(day, text + f" (change #{undo_id})"), {"last_entry": day})
        return ""

    return [f"a dated note on the card of {ticker}: {text}; nothing is deleted"], do


for _name in ("note", "thesis", "closewarning"):
    UNDO[_name] = _undo_note

register(Command("note", "Add my free note to a card", "/note KO <text>", changes=True, phase=2, plan=_note))
register(Command("thesis", "Add my correction of the thesis as a note", "/thesis KO <point>", changes=True, phase=2, plan=_thesis))
register(Command("closewarning", "Close a warning on a card, with the reason", "/closewarning KO U1 <reason>", changes=True,
                 phase=2, plan=_closewarning))
