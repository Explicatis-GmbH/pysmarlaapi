import asyncio

import aiohttp
import jsonpickle

from . import AuthToken


class Connection:

    def __init__(self, url: str, token: AuthToken = None, token_str=None, token_json=None, token_b64=None):
        self.url = url
        if token is not None:
            self.token = token
        elif token_json is not None:
            self.token = AuthToken.from_json(token_json)
        elif token_str is not None:
            self.token = AuthToken.from_string(token_str)
        elif token_b64 is not None:
            self.token = AuthToken.from_base64(token_b64)
        else:
            self.token = None

    def get_token(self) -> str:
        return self.token.token

    async def refresh_token(self) -> bool:
        try:
            async with aiohttp.ClientSession(self.url) as session:
                content = await self._get_token(session)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False

        if not content:
            return False

        try:
            self.token = AuthToken.from_json(content)
        except ValueError:
            return False

        return True

    async def _get_token(self, session: aiohttp.ClientSession):
        async with await session.post(
            "/api/AppParing/getToken",
            headers={"accept": "*/*", "Content-Type": "application/json"},
            data=jsonpickle.encode(self.token, unpicklable=False),
        ) as response:
            if response.status != 200:
                return None
            return await response.json()
