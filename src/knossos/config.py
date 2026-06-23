"""Configuration loaded from the environment (.env via python-dotenv)."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _parse_dirs(raw: str) -> list[str]:
    dirs: list[str] = []
    for part in raw.split(";"):
        part = part.strip().strip('"')
        if part:
            dirs.append(os.path.realpath(part))
    return dirs


def _parse_bins(raw: str) -> set[str]:
    bins: set[str] = set()
    for part in raw.split(";"):
        part = part.strip().strip('"').lower()
        if part:
            bins.add(part)
    return bins


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in ("1", "true", "yes", "on")


TOKEN: str = os.environ.get("KNOSSOS_TOKEN", "").strip()
HOST: str = os.environ.get("KNOSSOS_HOST", "0.0.0.0").strip()
PORT: int = int(os.environ.get("KNOSSOS_PORT", "8765"))

ALLOWED_DIRS: list[str] = _parse_dirs(os.environ.get("KNOSSOS_ALLOWED_DIRS", ""))
ALLOWED_BINS: set[str] = _parse_bins(os.environ.get("KNOSSOS_ALLOWED_BINS", ""))

CMD_TIMEOUT: int = int(os.environ.get("KNOSSOS_CMD_TIMEOUT", "300"))
MAX_READ_BYTES: int = int(os.environ.get("KNOSSOS_MAX_READ_BYTES", "5000000"))
ALLOW_DELETE: bool = _parse_bool(os.environ.get("KNOSSOS_ALLOW_DELETE", "false"))
