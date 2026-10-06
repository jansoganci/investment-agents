"""uv run python -m shared.ai ping     one tiny call to each provider and model in settings.yaml: which keys and names work

Prints ✓ / ✗ and the reason (never a key). The first thing to run on the Mac before real use (phase 2 Mac check)."""

import os
import sys

from shared import ai, config
from shared import db as dbmod
from shared.ai import ProviderError, backends


def ping() -> str:
    seen, lines = set(), ["AI PING (each provider and model once; a few tokens each)"]
    try:
        conn = dbmod.connect()  # the calls are logged like any other (they cost a little)
    except dbmod.DatabaseMissing:
        conn = None
        lines.append("(no database yet: these calls are not logged — run: uv run python -m shared.db init)")
    for job, entries in (config.settings().get("models") or {}).items():
        if job == "hermes_chat":
            continue
        for e in entries:
            if (e["provider"], e["model"]) in seen:
                continue
            seen.add((e["provider"], e["model"]))
            backend = ai.BACKENDS.get(e["provider"])
            key = backends.KEYS.get(e["provider"])
            if backend is None:
                lines.append(f"✗ {e['provider']} {e['model']} — unknown provider")
                continue
            if key and not os.environ.get(key, "").strip():
                lines.append(f"✗ {e['provider']} {e['model']} — {key} is not set")
                continue
            try:
                reply = backend(dict(e, job="ping"), "", "Reply with the single word: OK", 200)
                cost, est = ai.cost_of(reply.model, reply.input_tokens, reply.output_tokens)
                reply.cost_usd, reply.estimated, reply.job = cost, est, "ping"
                if conn is not None:
                    ai.log_reply(conn, None, reply)
                price = " (no price in settings.yaml: counted at the default)" if est else ""
                lines.append(f"✓ {e['provider']} {e['model']} — answered {reply.text.strip()[:20]!r}{price}")
            except ProviderError as exc:
                if conn is not None and exc.usage:
                    n_in, n_out, given = exc.usage
                    c, est = (given, False) if given is not None else ai.cost_of(e["model"], n_in, n_out)
                    ai.log_reply(conn, None, ai.Reply("", e["provider"], e["model"], n_in, n_out, c, "ping", est), None, exc.outcome)
                lines.append(f"✗ {e['provider']} {e['model']} — {exc}")
    if conn is not None:
        conn.close()
    return "\n".join(lines)


if __name__ == "__main__":
    if sys.argv[1:] != ["ping"]:
        print(__doc__)
        sys.exit(2)
    print(ping())
