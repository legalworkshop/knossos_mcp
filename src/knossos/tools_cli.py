"""CLI tool: run_command with argv list or string, restricted cwd, timeout, bin allowlist."""
from __future__ import annotations

import os
import shlex
import subprocess
import time
from typing import Union

from fastmcp.exceptions import ToolError

from . import config
from .security import check_bin_allowed, resolve_in_allowlist

_MAX_OUTPUT = 1_000_000  # cap each stream at ~1 MB so output never floods the agent


def _truncate(s: str | None) -> tuple[str, bool]:
    s = s or ""
    if len(s) > _MAX_OUTPUT:
        return s[:_MAX_OUTPUT], True
    return s, False


def _split_command(s: str) -> list[str]:
    """Split a command string into argv on Windows safely.

    Quotes group arguments and are stripped after grouping; backslashes stay
    literal (NOT treated as escapes, unlike default POSIX shlex); spaces inside
    double quotes are preserved. This lets Windows paths with spaces work when
    quoted, e.g. -File "C:\\Some Dir\\x.ps1".
    """
    lex = shlex.shlex(s, posix=True)
    lex.whitespace_split = True   # split on whitespace only, not on punctuation
    lex.escape = ""               # do NOT treat '\' as an escape char (key for Windows)
    lex.commenters = ""           # '#' does not start a comment
    return list(lex)


def register(mcp) -> None:
    @mcp.tool
    def run_command(
        command: Union[str, list[str]],
        cwd: str | None = None,
        timeout: int | None = None,
        env: dict | None = None,
    ) -> dict:
        """Run a command on Machine B; capture stdout, stderr, returncode and duration.

        Args:
            command: argv list (preferred) or a string. String parsing keeps backslashes
                 literal and respects double-quoted arguments, so Windows paths with
                 spaces work when quoted. NO shell is used.
            cwd: working directory; must be inside the allowlist. Defaults to the first
                 allowed root.
            timeout: seconds; clamped to at most KNOSSOS_CMD_TIMEOUT.
            env: extra environment variables merged onto the server's environment.

        Commands run WITHOUT a shell (shell=False). If KNOSSOS_ALLOWED_BINS is set, the
        executable must be approved. Each output stream is truncated at ~1 MB.
        """
        if isinstance(command, str):
            argv = _split_command(command)
        else:
            argv = [str(a) for a in command]
        if not argv:
            raise ToolError("Empty command.")

        check_bin_allowed(argv[0])

        work = str(resolve_in_allowlist(cwd)) if cwd else config.ALLOWED_DIRS[0]
        tmo = config.CMD_TIMEOUT if timeout is None else min(int(timeout), config.CMD_TIMEOUT)

        run_env = None
        if env:
            run_env = {**os.environ, **{str(k): str(v) for k, v in env.items()}}

        start = time.monotonic()
        try:
            proc = subprocess.run(
                argv,
                cwd=work,
                env=run_env,
                capture_output=True,
                text=True,
                timeout=tmo,
                shell=False,
            )
        except FileNotFoundError:
            raise ToolError(f"Executable not found: {argv[0]}")
        except subprocess.TimeoutExpired as e:
            dur = time.monotonic() - start
            out, out_tr = _truncate(e.stdout if isinstance(e.stdout, str) else None)
            err, err_tr = _truncate(e.stderr if isinstance(e.stderr, str) else None)
            return {
                "argv": argv, "cwd": work, "timed_out": True,
                "duration": round(dur, 3), "returncode": None,
                "stdout": out, "stderr": err,
                "stdout_truncated": out_tr, "stderr_truncated": err_tr,
            }

        dur = time.monotonic() - start
        out, out_tr = _truncate(proc.stdout)
        err, err_tr = _truncate(proc.stderr)
        return {
            "argv": argv, "cwd": work, "timed_out": False,
            "duration": round(dur, 3), "returncode": proc.returncode,
            "stdout": out, "stderr": err,
            "stdout_truncated": out_tr, "stderr_truncated": err_tr,
        }
