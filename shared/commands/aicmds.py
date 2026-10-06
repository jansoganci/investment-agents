"""Phase 2 commands: the AI's spend and models (roadmap section 10.2).

    /spend                       this month's AI spend by provider, and what is left of the limit
    /model                       which job runs on which model now
    /model strong gpt-6-sol      a stored override: that model goes first for the job, the others stay as fallbacks
    /model strong default        back to settings.yaml
"""

from __future__ import annotations

from shared import ai, clock, config
from shared.commands import Applied, Command, Plan, Refused, register

JOBS = ("cheap", "strong", "auditor")


def _spend(conn, args):
    limit = (config.settings().get("budget") or {}).get("ai_monthly_max_usd")
    rows = ai.spend_by_provider(conn)
    lines = [f"SPEND · {ai.month_start()[:7]} (this month, UTC)"]
    if not rows:
        lines.append("No AI calls yet.")
    for r in rows:
        extra = f", {r['unpriced']} unpriced (no price in settings.yaml)" if r["unpriced"] else ""
        lines.append(f"- {r['provider']}: ${r['usd']:.2f} · {r['calls']} calls{extra}")
    total = ai.month_spend(conn)
    if limit is not None:
        lines.append(f"Total ${total:.2f} of ${limit} · ${max(limit - total, 0):.2f} left")
    else:
        lines.append(f"Total ${total:.2f}")
    lines.append("An unpriced call is counted as $0 here; the real bill is on the provider's page.")
    return "\n".join(lines)


def _current(conn, job):
    first = ai.chain(job, conn)[0]
    return f"{first['model']} ({first['provider']})"


def _model_info(conn, args):
    lines = ["MODELS (the first one that answers is used; the others are fallbacks)"]
    for job in JOBS:
        override = ai._override(conn, job)
        chain = ai.chain(job, conn)
        lines.append(f"- {job}: {chain[0]['model']} ({chain[0]['provider']})" + (" · my override" if override else "")
                     + f" · then {len(chain) - 1} fallback(s)")
    lines.append("Change: /model <cheap|strong|auditor> <model | default>. Known: " + ", ".join(ai.model_names()))
    return "\n".join(lines)


def _model_plan(conn, args):
    if len(args) != 2 or args[0].lower() not in JOBS:
        raise Refused("usage: /model <cheap|strong|auditor> <model | default>   (or /model to see the models)")
    job, name = args[0].lower(), args[1]
    value = None if name.lower() == "default" else name
    if value is not None and ai.resolve(value) is None:
        raise Refused(f"Unknown model '{name}'. Known: {', '.join(ai.model_names())}.")
    if value is not None and job in ("strong", "auditor"):
        other = "auditor" if job == "strong" else "strong"
        mine, theirs = ai.entry_family(ai.resolve(value)), ai.entry_family(ai.chain(other, conn)[0])
        if mine == theirs:
            raise Refused(f"The auditor must be of a different model family than the writer: both would be {mine} "
                          f"(the {other} job runs {ai.chain(other, conn)[0]['model']}). Choose another model.")
    now = _current(conn, job)
    after = f"{ai.resolve(value)['model']}" if value else "the default in settings.yaml"
    preview = [f"{job}: {now} → {after}" + ("" if value is None else " (first; the others stay as fallbacks)"),
               "the spend limit still applies"]

    def apply(conn, number):
        before = ai._override(conn, job)
        cur = conn.execute("INSERT INTO settings (key, value, command_id, created_at) VALUES (?, ?, ?, ?)",
                           (f"model.{job}", value, number, clock.utc_iso()))
        return Applied(f"{job} model: {now} → {after}.", "settings", cur.lastrowid, before={"override": before})

    return Plan(preview, ["model", job, name], apply)


register(Command("spend", "This month's AI spend by provider and what is left", "/spend", phase=2, info=_spend))
register(Command("model", "Which job runs on which model; with arguments, changes it", "/model · /model strong gpt-6-sol",
                 changes=True, phase=2, info=_model_info, plan=_model_plan, show_without_args=True))
