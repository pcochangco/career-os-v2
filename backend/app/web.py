import re
from base64 import b64encode
from hashlib import sha256
from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

GOOGLE_SIGN_IN = "https://accounts.google.com"


def content_security_policy(index_html: str) -> str:
    """Allow only this app, the exported page's own inline script(s), and Google sign-in.

    Inline script hashes are read from the build so an Expo upgrade can't silently break the
    page. Styles stay inline-allowed because React Native Web injects them at runtime.
    """
    inline_scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", index_html, re.S)
    hashes = " ".join(
        f"'sha256-{b64encode(sha256(script.encode()).digest()).decode()}'"
        for script in dict.fromkeys(inline_scripts)
    )
    return "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' {hashes} {GOOGLE_SIGN_IN}/gsi/client".replace("  ", " "),
            f"style-src 'self' 'unsafe-inline' {GOOGLE_SIGN_IN}/gsi/style",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            f"connect-src 'self' {GOOGLE_SIGN_IN}/gsi/",
            f"frame-src {GOOGLE_SIGN_IN}/gsi/",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
    )


class SinglePageApplicationFiles(StaticFiles):
    """Serve an exported web app while preserving API 404 responses."""

    def __init__(self, *, directory: Path, html: bool = False) -> None:
        super().__init__(directory=directory, html=html)
        index = Path(directory) / "index.html"
        self.csp = content_security_policy(index.read_text() if index.is_file() else "")

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await self._find(path, scope)
        if response.headers.get("content-type", "").startswith("text/html"):
            response.headers["Content-Security-Policy"] = self.csp
        # Hashed bundles never change; pages revalidate so a deploy reaches open browsers.
        immutable = path.startswith("_expo/static/") and response.status_code == 200
        response.headers["Cache-Control"] = (
            "public, max-age=31536000, immutable" if immutable else "no-cache"
        )
        return response

    async def _find(self, path: str, scope: Scope) -> Response:
        # API routes and build assets 404 honestly; only app routes fall back to the page.
        no_fallback = path.startswith(("api/", "_expo/"))
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or no_fallback:
                raise
            return await super().get_response("index.html", scope)
        if response.status_code != 404 or no_fallback:
            return response
        return await super().get_response("index.html", scope)


def mount_frontend(application: Starlette, static_directory: str | None) -> None:
    if not static_directory:
        return
    path = Path(static_directory)
    if not path.is_dir():
        return
    application.mount(
        "/",
        SinglePageApplicationFiles(directory=path, html=True),
        name="frontend",
    )
