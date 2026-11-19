from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope


class SinglePageApplicationFiles(StaticFiles):
    """Serve an exported web app while preserving API 404 responses."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await self._find(path, scope)
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
