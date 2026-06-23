"""Local smoke test (run on Machine B). Starts nothing — assumes the server is up.

Usage:
    # terminal 1
    scripts\\run.ps1
    # terminal 2
    .venv\\Scripts\\python.exe scripts\\smoke_test.py

Verifies: health works with the token, a bad token is rejected (401), and a path
outside the allowlist is refused.
"""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

HOST = os.environ.get("KNOSSOS_HOST", "127.0.0.1")
if HOST == "0.0.0.0":
    HOST = "127.0.0.1"
PORT = os.environ.get("KNOSSOS_PORT", "8765")
TOKEN = os.environ.get("KNOSSOS_TOKEN", "")
URL = f"http://{HOST}:{PORT}/mcp"


async def main() -> int:
    from fastmcp import Client
    from fastmcp.client.auth import BearerAuth

    print(f"[smoke] target {URL}")

    # 1) Valid token -> health
    async with Client(URL, auth=BearerAuth(TOKEN)) as c:
        res = await c.call_tool("health", {})
        print("[smoke] health OK:", res.data)

    # 2) Bad token -> must fail
    try:
        async with Client(URL, auth=BearerAuth("wrong-token")) as c:
            await c.call_tool("health", {})
        print("[smoke] FAIL: bad token was accepted")
        return 1
    except Exception as e:
        print("[smoke] bad token rejected as expected:", type(e).__name__)

    # 3) Path outside allowlist -> must error
    async with Client(URL, auth=BearerAuth(TOKEN)) as c:
        try:
            await c.call_tool("list_dir", {"path": "C:\\Windows"})
            print("[smoke] FAIL: list_dir escaped the allowlist")
            return 1
        except Exception as e:
            print("[smoke] allowlist enforced as expected:", type(e).__name__)

    print("[smoke] ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
