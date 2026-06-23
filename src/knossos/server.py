"""Knossos MCP server — Streamable HTTP transport, Bearer auth, allowlisted FS + CLI.

Run:  python -m knossos.server   (or the `knossos` console script)
"""
from __future__ import annotations

import uvicorn
from starlette.middleware import Middleware

from fastmcp import FastMCP

from . import config, tools_cli, tools_diag, tools_files
from .auth import BearerAuthMiddleware


def build_mcp() -> FastMCP:
    mcp = FastMCP("Knossos")
    tools_files.register(mcp)
    tools_cli.register(mcp)
    tools_diag.register(mcp)
    return mcp


def build_app(mcp: FastMCP | None = None):
    """Build the Streamable HTTP ASGI app with Bearer auth in front."""
    mcp = mcp or build_mcp()
    return mcp.http_app(
        path="/mcp",
        stateless_http=True,
        json_response=True,
        middleware=[Middleware(BearerAuthMiddleware, token=config.TOKEN)],
    )


def main() -> None:
    if not config.TOKEN:
        raise SystemExit(
            "KNOSSOS_TOKEN is not set. Create a .env (see .env.example) with a strong token."
        )
    if not config.ALLOWED_DIRS:
        raise SystemExit(
            "KNOSSOS_ALLOWED_DIRS is empty. Set at least one allowed root in .env."
        )

    app = build_app()
    print(f"[knossos] listening on http://{config.HOST}:{config.PORT}/mcp")
    print(f"[knossos] allowed dirs: {config.ALLOWED_DIRS}")
    print(
        f"[knossos] allowed bins: "
        f"{sorted(config.ALLOWED_BINS) or 'ANY (not recommended)'}"
    )
    if not config.ALLOWED_BINS:
        print("[knossos] WARNING: KNOSSOS_ALLOWED_BINS is empty — run_command can launch any binary.")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")


if __name__ == "__main__":
    main()
