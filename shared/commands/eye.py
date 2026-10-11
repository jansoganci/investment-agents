"""/tag and /subsector (roadmap section 10.2; phase 4).

    /tag                                      the tags that wait for me (a US-looking company the SEC check did not confirm)
    /tag Cummins company CMI                  a US-listed company: SEC must know the ticker
    /tag Zhongkuang Resources company non-us  a company not listed in the US: no SEC check
    /tag Petrol commodity crude oil           /tag Yazılım ve İnternet sector Information Technology
    /tag Japonya region                       /tag Rapor Özetleri other
    /subsector                                the approved subsector list
    /subsector add Energy Uranium             a new subsector under a GICS sector

The tag's name is everything before the kind word; no quotes are needed. Only a tag the Eye has already met can be fixed."""

from __future__ import annotations

from agents.eye.extract import norm_tag
from shared import clock, sec
from shared.commands import UNDO, Applied, Command, Plan, Refused, register
from shared.sectors import GICS

KIND_WORDS = ("company", "commodity", "sector", "region", "other")
FIELDS = ("kind", "maps_to", "exchange", "country", "sector", "subsector", "source", "status", "us_listed", "note")
TAG_USAGE = ("usage: /tag <tag name> company <TICKER | non-us> · commodity <name> · sector <GICS sector> · region · other   "
             "(/tag alone lists the tags that wait for me)")


def _row(conn, name: str) -> dict:
    wanted = norm_tag(name)
    rows = conn.execute("SELECT id, tag, " + ", ".join(FIELDS) + " FROM tags WHERE tag = ? OR lower(tag) = lower(?)",
                        (wanted, wanted)).fetchall()
    exact = [r for r in rows if r[1] == wanted]
    rows = exact or rows
    if not rows:
        raise Refused(f"No post has the tag '{wanted}' yet (the Eye meets a tag when it reads a post that carries it).")
    if len(rows) > 1:
        raise Refused(f"'{wanted}' matches {len(rows)} tags ({', '.join(r[1] for r in rows)}); write the exact name.")
    return dict(zip(("id", "tag") + FIELDS, rows[0]))


def _describe(r: dict) -> str:
    bits = [r["kind"] or "unclassified"]
    if r["maps_to"]:
        bits.append(r["maps_to"])
    if r["exchange"]:
        bits.append(f"({r['exchange']})")
    if r["kind"] == "company" and r["us_listed"] == 0:
        bits.append("not US-listed")
    if r["status"] == "waiting":
        bits.append("— waiting for me")
    return " ".join(bits)


def _tag_info(conn, args):
    waiting = conn.execute("SELECT tag, note FROM tags WHERE status = 'waiting' ORDER BY id").fetchall()
    total = conn.execute("SELECT count(*) FROM tags").fetchone()[0]
    if not waiting:
        return f"No tag waits for me. {total} tags are mapped.\n{TAG_USAGE}"
    lines = [f"TAGS · {len(waiting)} wait for me ({total} mapped)"]
    lines += [f"- {tag}: {note}" for tag, note in waiting[:30]]
    if len(waiting) > 30:
        lines.append(f"… and {len(waiting) - 30} more")
    lines.append(TAG_USAGE)
    return "\n".join(lines)


def _tag_plan(conn, args):
    at = next((i for i, a in enumerate(args) if i >= 1 and a.lower() in KIND_WORDS), None)
    if at is None:
        raise Refused(TAG_USAGE)
    name, kind, value = " ".join(args[:at]), args[at].lower(), " ".join(args[at + 1:]).strip()
    old = _row(conn, name)
    new = {f: old[f] for f in FIELDS}
    new.update(kind=kind, maps_to=None, exchange=None, us_listed=None, source="user", status="confirmed", note=None)
    if kind == "company":
        if not value:
            raise Refused("A company needs a ticker (US-listed) or `non-us`:  /tag Cummins company CMI")
        if value.lower().replace(" ", "-") in ("non-us", "nonus"):
            new["us_listed"] = 0
        else:
            ticker = value.split()[0]
            try:
                found = sec.lookup(ticker)
            except Exception as error:        # noqa: BLE001 — SEC, the network or a missing SEC_UA: nothing changes
                raise Refused(f"SEC could not be asked ({error}). Nothing changed.") from None
            if found is None:
                raise Refused(f"SEC does not know the ticker {ticker.upper()}. If the company is not listed in the US: "
                              f"/tag {old['tag']} company non-us")
            new.update(maps_to=found["ticker"], exchange=found["exchange"], us_listed=1)
    elif kind == "commodity":
        if not value:
            raise Refused("A commodity needs its name:  /tag Petrol commodity crude oil")
        new["maps_to"] = value.lower()
    elif kind == "sector":
        match = next((s for s in GICS if s.lower() == value.lower()), None)
        if match is None:
            raise Refused("The sector must be one of: " + ", ".join(GICS))
        new.update(maps_to=match, sector=match)
    elif value:
        raise Refused(f"`{kind}` takes no value. {TAG_USAGE}")
    snapshot = {f: old[f] for f in FIELDS}
    preview = [f"{old['tag']}: {_describe(old)}  →  {_describe(new)}"]

    def recheck(conn):
        if {f: _row(conn, old["tag"])[f] for f in FIELDS} != snapshot:
            raise Refused("The tag changed in the meantime. Send the command again.")

    def apply(conn, number):
        recheck(conn)
        conn.execute("UPDATE tags SET " + ", ".join(f"{f} = ?" for f in FIELDS) + " WHERE id = ?",
                     [new[f] for f in FIELDS] + [old["id"]])
        return Applied(f"{old['tag']}: {_describe(old)} → {_describe(new)}.", "tags", old["id"], before=snapshot)

    return Plan(preview, ["tag", *args], apply, recheck=recheck)


def _undo_tag(conn, log):
    before, tag_id = log["before"], log["target_id"]
    if not before or not tag_id:
        raise Refused("This change has no saved earlier state; fix the tag with /tag instead.")

    def do(conn, undo_id):
        conn.execute("UPDATE tags SET " + ", ".join(f"{f} = ?" for f in FIELDS) + " WHERE id = ?",
                     [before[f] for f in FIELDS] + [tag_id])
        return "The tag is back as it was."

    return ["the tag's earlier mapping is put back (nothing is deleted)"], do


def _sub_info(conn, args):
    rows = conn.execute("SELECT sector, name FROM subsectors WHERE void = 0 ORDER BY sector, name").fetchall()
    other = conn.execute("SELECT count(*) FROM tags WHERE subsector = 'other'").fetchone()[0]
    if not rows:
        lines = ["SUBSECTORS · the approved list is empty."]
    else:
        lines = [f"SUBSECTORS · {len(rows)} approved"]
        for sector in dict.fromkeys(r[0] for r in rows):
            lines.append(f"- {sector}: " + ", ".join(n for s, n in rows if s == sector))
    if other:
        lines.append(f"{other} tag(s) were marked `other`: no approved subsector fits them yet.")
    lines.append("Add: /subsector add <GICS sector> <name>   e.g. /subsector add Energy Uranium")
    return "\n".join(lines)


def _sub_plan(conn, args):
    if len(args) < 3 or args[0].lower() != "add":
        raise Refused("usage: /subsector add <GICS sector> <name>   e.g. /subsector add Energy Uranium · sectors: " + ", ".join(GICS))
    rest = args[1:]
    sector = next((s for s in GICS if " ".join(rest[:len(s.split())]).lower() == s.lower()), None)
    name = " ".join(rest[len(sector.split()):]).strip() if sector else ""
    if not sector or not name:
        raise Refused("Start with a GICS sector, then the subsector's name. Sectors: " + ", ".join(GICS))
    existing = conn.execute("SELECT id, sector, void, voided_by FROM subsectors WHERE lower(name) = lower(?)", (name,)).fetchone()
    if existing and not existing[2]:
        raise Refused(f"'{name}' is already on the list (under {existing[1]}).")

    def apply(conn, number):
        if existing:        # a cancelled one comes back
            conn.execute("UPDATE subsectors SET void = 0, voided_by = NULL, sector = ?, command_id = ? WHERE id = ?",
                         (sector, number, existing[0]))
            return Applied(f"Subsector '{name}' is back on the list, under {sector}.", "subsectors", existing[0])
        cur = conn.execute("INSERT INTO subsectors (name, sector, command_id, created_at) VALUES (?, ?, ?, ?)",
                           (name, sector, number, clock.utc_iso()))
        return Applied(f"Subsector '{name}' added under {sector}.", "subsectors", cur.lastrowid)

    return Plan([f"add the subsector '{name}' under {sector}"], ["subsector", *args], apply)


register(Command("tag", "Fix a wrong tag mapping", "/tag Cummins company CMI · /tag Petrol commodity crude oil", changes=True,
                 phase=4, info=_tag_info, plan=_tag_plan, show_without_args=True))
register(Command("subsector", "Approve a new subsector", "/subsector add Energy Uranium", changes=True, phase=4,
                 info=_sub_info, plan=_sub_plan, show_without_args=True))
UNDO["tag"] = _undo_tag
