import io
import os

import pytest

from agents.eye import set_cookie

COOKIE = "ghost-members-ssr=abc123def456ghi789; _ga=GA1.1.1234.5678"


def test_clean_takes_the_value_of_one_line_or_the_cookie_line_of_a_block():
    assert set_cookie.clean(COOKIE + "\n") == COOKIE
    assert set_cookie.clean("cookie: " + COOKIE) == COOKIE
    assert set_cookie.clean("accept: */*\nCookie: " + COOKIE + "\nhost: x.com\n") == COOKIE
    with pytest.raises(ValueError):
        set_cookie.clean("a=1\nb=2")


def test_clean_takes_the_cookie_out_of_a_copied_curl_command():
    chrome = ("curl 'https://x.com/post/' \\\n  -H 'accept: text/html' \\\n  -b '" + COOKIE + "' \\\n  -H 'user-agent: Mozilla/5.0'")
    assert set_cookie.clean(chrome) == COOKIE
    header_style = "curl 'https://x.com/post/' -H 'accept: */*' -H 'Cookie: " + COOKIE + "'"
    assert set_cookie.clean(header_style) == COOKIE
    with pytest.raises(ValueError):
        set_cookie.clean("curl 'https://x.com/post/?a=1' -H 'accept: */*'")


def test_check_refuses_what_is_not_a_cookie_or_cannot_be_kept():
    set_cookie.check(COOKIE)
    for bad in ("", "short=1", "x" * 30, COOKIE + "'", COOKIE + "${HOME}"):
        with pytest.raises(ValueError):
            set_cookie.check(bad)


def test_rewrite_replaces_the_old_line_and_drops_broken_ones():
    old = ("# keys\nANTHROPIC_API_KEY=k\n\nEMTIA_COOKIE=''\nDRAGONOMI_COOKIE=\n"
           "EMTIA_COOKIE='a=1; b=2\naccept: */*\n_ga=GA1.2'\nhost: x.com\n")
    new, dropped = set_cookie.rewrite(old, "EMTIA_COOKIE", COOKIE)
    assert dropped == 3
    lines = new.splitlines()
    assert lines[-1] == f"EMTIA_COOKIE='{COOKIE}'"
    assert sum(line.startswith("EMTIA_COOKIE=") for line in lines) == 1
    assert "ANTHROPIC_API_KEY=k" in lines and "DRAGONOMI_COOKIE=" in lines and "# keys" in lines


def test_main_writes_a_private_env_keeps_a_backup_and_prints_no_value(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text("SEC_UA=me\nEMTIA_COOKIE=''\n")
    monkeypatch.setattr(set_cookie, "env_path", lambda: env)
    monkeypatch.setattr("sys.stdin", io.StringIO("cookie: " + COOKIE + "\n"))
    assert set_cookie.main(["emtia", "--stdin"]) == 0
    assert env.read_text() == f"SEC_UA=me\nEMTIA_COOKIE='{COOKIE}'\n"
    assert oct(os.stat(env).st_mode & 0o777) == "0o600"
    assert (tmp_path / ".env.bak").read_text() == "SEC_UA=me\nEMTIA_COOKIE=''\n"
    out = capsys.readouterr().out
    assert COOKIE not in out and "ghost-members-ssr" not in out and "EMTIA_COOKIE saved" in out


def test_main_refuses_a_bad_copy_and_changes_nothing(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text("SEC_UA=me\n")
    monkeypatch.setattr(set_cookie, "env_path", lambda: env)
    monkeypatch.setattr("sys.stdin", io.StringIO("nope"))
    assert set_cookie.main(["emtia", "--stdin"]) == 1
    assert env.read_text() == "SEC_UA=me\n"
    assert set_cookie.main(["nowhere"]) == 2


def test_the_written_line_is_read_back_by_dotenv(tmp_path):
    from dotenv import dotenv_values
    new, _ = set_cookie.rewrite("SEC_UA=me\n", "EMTIA_COOKIE", COOKIE)
    path = tmp_path / ".env"
    path.write_text(new)
    assert dotenv_values(path)["EMTIA_COOKIE"] == COOKIE
