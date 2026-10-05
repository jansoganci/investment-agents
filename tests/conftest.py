import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A clean data folder and Drive folder for each test; the real .env and database are never touched."""
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    return {"data": data, "drive": drive}


@pytest.fixture
def db(env):
    """An initialized database; yields a write connection."""
    from shared import db as dbmod

    dbmod.init()
    conn = dbmod.connect()
    yield conn
    conn.close()
