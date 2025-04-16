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

    async def get_token(self) -> AuthToken:
        try:
            async with aiohttp.ClientSession(self.url) as session:
                async with session.post(
                    "/api/AppParing/getToken",
                    headers={"accept": "*/*", "Content-Type": "application/json"},
                    data=jsonpickle.encode(self.token, unpicklable=False),
                ) as response:
                    if response.status != 200:
                        return None
                    json_body = await response.json()
        except ValueError:
            return None
        try:
            new_token = AuthToken.from_json(json_body)
        except ValueError:
            return None
        self.token = new_token
        return self.token
