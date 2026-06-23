"""File tools: list_dir, read_file, write_file, stat_path, delete_path (opt-in)."""
from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from pathlib import Path

from fastmcp.exceptions import ToolError

from . import config
from .security import resolve_in_allowlist


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def register(mcp) -> None:
    @mcp.tool
    def list_dir(path: str) -> dict:
        """List entries of a directory inside the allowlist.

        Args:
            path: Absolute path, or a path relative to an allowed root.
        Returns: {path, count, entries:[{name, type, size, mtime}]}.
        """
        target = resolve_in_allowlist(path)
        if not target.exists():
            raise ToolError(f"Path does not exist: {target}")
        if not target.is_dir():
            raise ToolError(f"Not a directory: {target}")

        entries = []
        with os.scandir(target) as it:
            for e in it:
                try:
                    st = e.stat()
                    entries.append({
                        "name": e.name,
                        "type": "dir" if e.is_dir() else "file",
                        "size": st.st_size,
                        "mtime": _iso(st.st_mtime),
                    })
                except OSError:
                    entries.append({"name": e.name, "type": "unknown", "size": None, "mtime": None})

        entries.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))
        return {"path": str(target), "count": len(entries), "entries": entries}

    @mcp.tool
    def read_file(path: str, encoding: str = "utf-8", max_bytes: int | None = None) -> dict:
        """Read a file inside the allowlist.

        Returns text when decodable with `encoding`; binary or undecodable content is
        returned base64-encoded (with encoding="base64"). `max_bytes` caps the read
        (defaults to KNOSSOS_MAX_READ_BYTES) to protect the agent's context window.
        """
        target = resolve_in_allowlist(path)
        if not target.exists() or not target.is_file():
            raise ToolError(f"Not a file: {target}")

        limit = max_bytes if max_bytes is not None else config.MAX_READ_BYTES
        size = target.stat().st_size
        with open(target, "rb") as f:
            raw = f.read(limit)
        truncated = size > len(raw)

        if encoding.lower() == "base64":
            content, enc = base64.b64encode(raw).decode("ascii"), "base64"
        else:
            try:
                content, enc = raw.decode(encoding), encoding
            except (UnicodeDecodeError, LookupError):
                content, enc = base64.b64encode(raw).decode("ascii"), "base64"

        return {
            "path": str(target),
            "encoding": enc,
            "bytes_read": len(raw),
            "size": size,
            "truncated": truncated,
            "content": content,
        }

    @mcp.tool
    def write_file(
        path: str, content: str, mode: str = "overwrite", encoding: str = "utf-8"
    ) -> dict:
        """Write a file inside the allowlist.

        Args:
            mode: 'overwrite' (default) or 'append'.
            encoding: text encoding, or 'base64' to decode `content` and write bytes.
        Parent directories are created as needed, but only inside the allowlist.
        """
        if mode not in ("overwrite", "append"):
            raise ToolError("mode must be 'overwrite' or 'append'.")

        target = resolve_in_allowlist(path)
        # Ensure the parent directory is also inside the allowlist before creating it.
        resolve_in_allowlist(str(target.parent))
        target.parent.mkdir(parents=True, exist_ok=True)

        if encoding.lower() == "base64":
            data = base64.b64decode(content)
        else:
            data = content.encode(encoding)

        flag = "ab" if mode == "append" else "wb"
        with open(target, flag) as f:
            f.write(data)

        return {"path": str(target), "mode": mode, "bytes_written": len(data)}

    @mcp.tool
    def stat_path(path: str) -> dict:
        """Return metadata for a path: exists, type, size, mtime/ctime/atime."""
        target = resolve_in_allowlist(path)
        if not target.exists():
            return {"path": str(target), "exists": False}
        st = target.stat()
        return {
            "path": str(target),
            "exists": True,
            "type": "dir" if target.is_dir() else "file",
            "size": st.st_size,
            "mtime": _iso(st.st_mtime),
            "ctime": _iso(st.st_ctime),
            "atime": _iso(st.st_atime),
        }

    if config.ALLOW_DELETE:
        @mcp.tool
        def delete_path(path: str, confirm: bool = False) -> dict:
            """Delete a file or EMPTY directory inside the allowlist. Requires confirm=True.

            This tool is registered only when KNOSSOS_ALLOW_DELETE=true.
            """
            if not confirm:
                raise ToolError("Refusing to delete without confirm=True.")
            target = resolve_in_allowlist(path)
            if not target.exists():
                raise ToolError(f"Path does not exist: {target}")
            if target.is_dir():
                target.rmdir()  # only succeeds on empty directories
                kind = "dir"
            else:
                target.unlink()
                kind = "file"
            return {"path": str(target), "deleted": True, "type": kind}
