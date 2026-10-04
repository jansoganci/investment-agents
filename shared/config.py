"""settings.yaml + .env → paths and settings. The code knows nothing about Hermes."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "settings.yaml"

# .env never overrides a variable that is already set (tests set their own paths).
load_dotenv(ROOT / ".env", override=False)


class SettingMissing(RuntimeError):
    pass


def settings() -> dict:
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def data_dir() -> Path:
    value = os.environ.get("DATA_DIR") or settings()["paths"]["data_dir"]
    return Path(value).expanduser()


def db_path() -> Path:
    return data_dir() / settings()["paths"]["database"]


def drive_dir() -> Path:
    """The Drive root `Investing/` on this machine (DRIVE_DIR in .env)."""
    value = os.environ.get("DRIVE_DIR")
    if not value:
        raise SettingMissing("DRIVE_DIR is not set in .env (the path of the Drive folder `Investing/`).")
    return Path(value).expanduser()
