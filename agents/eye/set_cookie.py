"""Put my login cookie into `.env` without ever showing it.

    uv run python -m agents.eye.set_cookie emtia          (copy the cookie header in the browser first; it is read from the clipboard)
    uv run python -m agents.eye.set_cookie dragonomi
    uv run python -m agents.eye.set_cookie emtia --stdin  (read it from standard input instead of the clipboard)

Copy the value of the `cookie` request header (developer tools → Network → the post's request → Request Headers). Easier: right-click the
post's request → Copy → Copy as cURL; the cookie is taken out of the command. A whole block of headers also works: the line that starts with `cookie:` is taken. The old line of that site is replaced; lines in `.env` that are not
`NAME=value`, comments or blank (left over from a broken paste) are removed; the old file is kept as `.env.bak` — delete it when all
is well. The value is never printed and the clipboard is emptied afterwards."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from agents.eye.sites import SITES
from shared import config

USAGE = "usage: python -m agents.eye.set_cookie emtia|dragonomi [--stdin]"
VAR_LINE = re.compile(r"^[A-Z][A-Z0-9_]*=")


def env_path() -> Path:
    return config.ROOT / ".env"


def clean(text: str) -> str:
    """The cookie header value from what was copied: one line, the `cookie:` line of a block of headers, or a `Copy as cURL` command."""
    curl = re.search(r"""(?:\s-b|\s--cookie)\s+(?:\$)?'([^']+)'|\s-H\s+(?:\$)?'(?i:cookie):\s*([^']+)'""", text)
    if text.lstrip().startswith("curl"):
        if not curl:
            raise ValueError("that curl command has no cookie in it; open a post while logged in, then copy that request")
        return (curl.group(1) or curl.group(2)).strip()
    lines = [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]
    for line in lines:
        found = re.match(r"(?i)^cookie\s*:\s*(.+)$", line)
        if found:
            return found.group(1).strip().strip("'\"")
    if len(lines) == 1:
        return lines[0].strip("'\"")
    raise ValueError("what was copied has several lines and none starts with `cookie:`; copy only the value of the `cookie` request header")


def check(value: str) -> None:
    if len(value) < 20 or "=" not in value:
        raise ValueError(f"that does not look like a cookie header ({len(value)} characters, expected name=value pairs); nothing was written")
    if "'" in value or "${" in value or re.search(r"[\x00-\x1f]", value):
        raise ValueError("the cookie holds a quote, `${` or a control character, which `.env` cannot keep safely; nothing was written")


def rewrite(env_text: str, name: str, value: str) -> tuple[str, int]:
    """The new `.env` text and how many broken lines were dropped. The old line of `name` is replaced."""
    kept, dropped = [], 0
    for line in env_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            kept.append(line)
        elif line.startswith(name + "="):
            continue
        elif VAR_LINE.match(line):
            kept.append(line)
        else:
            dropped += 1
    kept.append(f"{name}='{value}'")
    return "\n".join(kept) + "\n", dropped


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    use_stdin = "--stdin" in argv
    args = [a for a in argv if a != "--stdin"]
    if len(args) != 1 or args[0] not in SITES:
        print(USAGE)
        return 2
    name = SITES[args[0]].cookie_env
    try:
        if use_stdin:
            text = sys.stdin.read()
        else:
            try:
                text = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True).stdout
            except (OSError, subprocess.CalledProcessError):
                print("The clipboard could not be read (pbpaste exists only on a Mac). Use --stdin.")
                return 1
        value = clean(text)
        check(value)
    except ValueError as error:
        print(error)
        return 1
    path = env_path()
    old = path.read_text() if path.exists() else ""
    if path.exists():
        backup = path.with_name(".env.bak")
        shutil.copyfile(path, backup)
        os.chmod(backup, 0o600)
    new, dropped = rewrite(old, name, value)
    path.write_text(new)
    os.chmod(path, 0o600)
    if not use_stdin:
        subprocess.run(["pbcopy"], input=b"", check=False)
    tail = "The clipboard is empty." if not use_stdin else ""
    print(f"{name} saved ({len(value)} characters). Broken lines removed from .env: {dropped}. "
          f"The old file is kept as .env.bak (delete it when all is well). {tail}".strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
