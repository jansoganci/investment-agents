"""uv run python -m shared.auditor testset [model]    run the error test sets against the real auditor (costs a few cents)"""

import sys

from shared import runlog
from shared.auditor import testset


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "testset" or len(argv) > 2:
        print(__doc__)
        return 2

    def work(run):
        from shared import ai
        from shared import db as dbmod

        results = testset.run(argv[1] if len(argv) == 2 else None, run=run)
        conn = dbmod.connect()
        try:
            spent = ai.month_spend(conn)
        finally:
            conn.close()
        return testset.report(results) + f"\nSpent this month so far: ${spent:.2f}"

    return runlog.job_main("auditor_testset", work)


if __name__ == "__main__":
    sys.exit(main())
