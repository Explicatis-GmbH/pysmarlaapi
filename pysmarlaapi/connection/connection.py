import asyncio

import aiohttp
import jsonpickle

from .exceptions import AuthenticationException, ConnectionException
from .token import AuthToken


class Connection:

    def __init__(
            self,
            url: str,
            token: AuthToken | None = None,
            token_str: str | None = None,
            token_json : dict | None = None,
            token_b64: str | None = None,
        ):
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
            raise ValueError("Token missing")

    def get_token(self) -> str:
        return self.token.token

    async def refresh_token(self):
        try:
            async with aiohttp.ClientSession(self.url) as session:
                response = await session.post(
                    "/api/AppParing/getToken",
                    headers={"accept": "*/*", "Content-Type": "application/json"},
                    data=jsonpickle.encode(self.token, unpicklable=False),
                )
                if response.status != 200:
                    raise AuthenticationException
                content = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            raise ConnectionException from e

        try:
            self.token = AuthToken.from_json(content)
        except ValueError as e:
            raise AuthenticationException from e
