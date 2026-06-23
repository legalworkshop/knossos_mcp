"""Path allowlist + binary allowlist enforcement. Prevents path traversal / escapes.

Every filesystem tool MUST route its path through resolve_in_allowlist(). Every CLI
launch MUST route argv[0] through check_bin_allowed()."""
from __future__ import annotations

import os
from pathlib import Path

from fastmcp.exceptions import ToolError

from . import config


def _normcase_real(p: str) -> str:
    # realpath resolves symlinks and normalizes '..'; normcase makes the compare
    # case-insensitive on Windows.
    return os.path.normcase(os.path.realpath(p))


def _is_within(child: str, parent: str) -> bool:
    child_r = _normcase_real(child)
    parent_r = _normcase_real(parent)
    try:
        return os.path.commonpath([child_r, parent_r]) == parent_r
    except ValueError:
        # Different drives on Windows -> not comparable -> not contained.
        return False


def resolve_in_allowlist(path: str) -> Path:
    """Resolve `path` (absolute, or relative to an allowed root) and guarantee it lies
    inside one of KNOSSOS_ALLOWED_DIRS. Raises ToolError otherwise.

    Resolution uses realpath, so symlinks that escape the allowlist and `..` traversal
    are both rejected.
    """
    if not config.ALLOWED_DIRS:
        raise ToolError("No allowed directories configured (KNOSSOS_ALLOWED_DIRS is empty).")

    raw = (path or "").strip()
    if not raw:
        raise ToolError("Empty path.")

    p = Path(raw)
    candidates: list[str] = []
    if p.is_absolute():
        candidates.append(str(p))
    else:
        for root in config.ALLOWED_DIRS:
            candidates.append(str(Path(root) / p))

    for cand in candidates:
        for root in config.ALLOWED_DIRS:
            if _is_within(cand, root):
                return Path(os.path.realpath(cand))

    raise ToolError(
        f"Path '{path}' is outside the allowed directories. "
        f"Allowed roots: {config.ALLOWED_DIRS}"
    )


def check_bin_allowed(argv0: str) -> None:
    """If KNOSSOS_ALLOWED_BINS is set, ensure the executable is approved. Empty list
    means open mode (any binary) — not recommended."""
    if not config.ALLOWED_BINS:
        return

    name = os.path.basename(argv0).lower()
    stem = name
    for ext in (".exe", ".bat", ".cmd", ".com"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break

    if stem not in config.ALLOWED_BINS and name not in config.ALLOWED_BINS:
        raise ToolError(
            f"Executable '{argv0}' is not in the allowlist KNOSSOS_ALLOWED_BINS "
            f"({sorted(config.ALLOWED_BINS)})."
        )
