"""uv run python -m shared.commands <name> [args …] [--yes]
uv run python -m shared.commands --setcommands      prints the text for @BotFather → /setcommands"""

from __future__ import annotations

import sys

from shared import commands


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--setcommands"]:
        print(commands.setcommands_text())
        return 0
    code, text = commands.run(argv)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
