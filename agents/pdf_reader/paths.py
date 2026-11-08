"""Folders for the PDF reader. Nothing is imported from shared or from the other agents."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
SETTINGS_FILE = ROOT / "settings.yaml"
ENV_FILE = ROOT / ".env"

load_dotenv(ENV_FILE, override=False)


class PathsError(Exception):
    pass


def data_dir() -> Path:
    value = os.environ.get("DATA_DIR")
    if not value:
        value = yaml.safe_load(SETTINGS_FILE.read_text("utf-8"))["paths"]["data_dir"]
    path = Path(value).expanduser()
    drive = os.environ.get("DRIVE_DIR")
    if drive and path.resolve().is_relative_to(Path(drive).expanduser().resolve()):
        raise PathsError(f"DATA_DIR {path} is inside Drive; working files never go in Drive.")
    return path


def drive_dir() -> Path:
    value = os.environ.get("DRIVE_DIR")
    if not value:
        raise PathsError("DRIVE_DIR is not set in .env (the path of the Drive folder `Investing/`).")
    return Path(value).expanduser()


def new_dir() -> Path:
    return drive_dir() / "PDF" / "New"


def done_dir() -> Path:
    return drive_dir() / "PDF" / "Done"


def failed_dir() -> Path:
    return drive_dir() / "PDF" / "Failed"


def work_root() -> Path:
    return data_dir() / "pdf_work"


def work_dir(fingerprint: str) -> Path:
    return work_root() / fingerprint


def registry_file() -> Path:
    return data_dir() / "pdf_registry.jsonl"


def ensure_dirs() -> None:
    for folder in (new_dir(), done_dir(), failed_dir(), work_root()):
        folder.mkdir(parents=True, exist_ok=True)
