import pytest


@pytest.fixture(autouse=True)
def pdf_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    return {
        "data": data,
        "drive": drive,
        "new": drive / "PDF" / "New",
        "done": drive / "PDF" / "Done",
        "failed": drive / "PDF" / "Failed",
    }
