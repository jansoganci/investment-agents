"""uv run python -m shared.prices            the nightly price job
uv run python -m shared.prices --ticker KO  one ticker on demand (10 years the first time)"""

from __future__ import annotations

import sys

from shared import db as dbmod
from shared import notify, runlog
from shared import prices


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["--ticker"] and len(argv) == 2:
        symbol = argv[1].upper()

        def one(_run):
            conn = dbmod.connect()
            try:
                new = prices.ensure_history(conn, symbol)
                last = prices.latest_close(conn, symbol)
                n_splits = len(prices.splits(conn, symbol))
            finally:
                conn.close()
            close = f"{last[1]:.2f} on {last[0]}" if last else "none"
            return notify.message(f"PRICES · {symbol}", [f"New days stored: {new} · latest close: {close} · splits on record: {n_splits}"])

        return runlog.job_main("prices", one)
    if argv:
        print("usage: python -m shared.prices [--ticker KO]")
        return 2

    def nightly(_run):
        conn = dbmod.connect()
        try:
            return prices.run_job(conn)
        finally:
            conn.close()

    return runlog.job_main("prices", nightly)


if __name__ == "__main__":
    sys.exit(main())
