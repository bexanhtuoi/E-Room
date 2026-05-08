from __future__ import annotations

import json
from typing import Any, Optional


class ApiClient:
    def __init__(self, base_url: str = "/api/v1") -> None:
        self._base_url = base_url

    def _auth_headers(self) -> dict[str, str]:
        token = None
        try:
            raw = __import__("json").loads(
                __import__("pathlib").Path("./auth.json").read_text()
            )
        except Exception:
            raw = {}
        stored = raw or {}
        # also check localStorage via injected value
        return {"Authorization": f"Bearer {stored.get('token', '')}", "Content-Type": "application/json"}

    async def get(self, path: str) -> Any:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self._base_url}{path}", headers=self._auth_headers()) as resp:
                if resp.status >= 400:
                    raise Exception(f"API {resp.status}: {await resp.text()}")
                return await resp.json()

    async def post(self, path: str, data: dict) -> Any:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}{path}", json=data, headers=self._auth_headers()
            ) as resp:
                if resp.status >= 400:
                    raise Exception(f"API {resp.status}: {await resp.text()}")
                return await resp.json()

    def get_sync(self, path: str) -> Any:
        import urllib.request
        req = urllib.request.Request(f"{self._base_url}{path}", headers=self._auth_headers())
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def post_sync(self, path: str, data: dict) -> Any:
        import urllib.request
        req = urllib.request.Request(
            f"{self._base_url}{path}",
            data=json.dumps(data).encode(),
            headers=self._auth_headers(),
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
