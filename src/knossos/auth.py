"""Bearer-token ASGI middleware. Rejects any request without a valid token (401).

Pure ASGI (does not buffer the request body), so it works with streaming and large
uploads. Token comparison is constant-time (secrets.compare_digest)."""
from __future__ import annotations

import secrets

from starlette.responses import JSONResponse


class BearerAuthMiddleware:
    def __init__(self, app, token: str):
        self.app = app
        self.token = token or ""

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        raw = headers.get(b"authorization", b"").decode("latin-1")

        presented = ""
        parts = raw.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            presented = parts[1].strip()

        authorized = bool(self.token) and secrets.compare_digest(presented, self.token)
        if not authorized:
            response = JSONResponse(
                {"error": "unauthorized", "detail": "Missing or invalid Bearer token."},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
