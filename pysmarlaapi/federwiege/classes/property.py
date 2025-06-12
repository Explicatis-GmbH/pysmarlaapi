import asyncio
from typing import Generic, TypeVar

from ...connection_hub import ConnectionHub

_VT = TypeVar("_VT")


class Property(Generic[_VT]):

    value: _VT | None = None

    def __init__(self, hub: ConnectionHub):
        self.hub = hub
        self.listeners = set()
        self.lock = asyncio.Lock()

    async def add_listener(self, listener):
        async with self.lock:
            self.listeners.add(listener)

    async def remove_listener(self, listener):
        async with self.lock:
            self.listeners.remove(listener)

    async def notify_listeners(self):
        async with self.lock:
            for listener in self.listeners:
                await listener(self.value)

    def get(self) -> _VT | None:
        return self.value

    def set(self, new_value: _VT, push=True):
        if push:
            self.push(new_value)
        else:
            self.value = new_value

    def push(self, value: _VT):
        pass

    def pull(self):
        pass

    def register(self):
        pass
