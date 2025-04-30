import base64
import json
from dataclasses import dataclass
from typing import Self

import jsonpickle


@dataclass
class AuthToken:
    refreshToken: str
    token: str
    dateCreated: str
    appIdentifier: str
    serialNumber: str
    appVersion: str
    appCulture: str

    @classmethod
    def from_json(cls, value: dict) -> Self:
        value["py/object"] = "pysmarlaapi.classes.auth_token.AuthToken"
        return jsonpickle.decode(json.dumps(value))

    @classmethod
    def from_string(cls, value: str) -> Self:
        return AuthToken.from_json(json.loads(value))

    @classmethod
    def from_base64(cls, value: str) -> Self:
        token = base64.b64decode(value.encode()).decode()
        return AuthToken.from_string(token)

    def get_string(self) -> str:
        return jsonpickle.encode(self, unpicklable=False)

    def get_base64(self) -> str:
        return base64.b64encode(self.get_string().encode()).decode()
