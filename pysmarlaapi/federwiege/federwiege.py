import asyncio
import threading

import aiohttp

from ..connection import Connection
from ..connection.hub import ConnectionHub
from .services import (AnalyserService, BabywiegeService, InfoService,
                       SystemService)
from .services.classes import Service


class Federwiege:

    @property
    def running(self):
        return self.hub.running

    @property
    def connected(self):
        return self.hub.connected

    async def on_connection_change(self, value):
        if value == self.available:
            return

        self.available = value
        await self.notify_listeners()

        if self.available:
            self.sync()

    def __init__(self, event_loop: asyncio.AbstractEventLoop, connection: Connection, auth_failure_callback=None):
        self.serial_number = connection.token.serialNumber
        self.connection = connection
        self.hub = ConnectionHub(event_loop, connection, self.on_connection_change, auth_failure_callback)
        self.services: dict[str, Service] = {
            "babywiege": BabywiegeService(self.hub),
            "analyser": AnalyserService(self.hub),
            "info": InfoService(self.hub),
            "system": SystemService(self.hub),
        }

        self.registered = False
        self._lock = threading.Lock()

        self._listeners = set()
        self._listeners_lock = asyncio.Lock()

        self.available = False

    async def check_firmware_update(self) -> tuple[str, str] | None:
        await self.connection.refresh_token()

        try:
            async with aiohttp.ClientSession(self.connection.url) as session:
                response = await session.get(
                    "/api/Firmware/CheckFirmwareUpdate",
                    headers={"accept": "*/*", "Content-Type": "application/json", "Authorization": f"Bearer {self.connection.get_token()}"},
                )
                if response.status != 200:
                    return None
                content = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None

        return (content["targetFirmware"], content["releaseNotes"])

    def get_service(self, key: str):
        return self.services[key]

    def get_property(self, service_key: str, prop_key: str):
        service = self.get_service(service_key)
        return service.get_property(prop_key)

    def connect(self):
        with self._lock:
            if not self.registered:
                return
            self.hub.start()

    def disconnect(self):
        self.hub.stop()

    def sync(self):
        for service in self.services.values():
            service.sync()

    def register(self):
        with self._lock:
            if self.registered:
                return
            for service in self.services.values():
                service.register()
            self.registered = True

    async def add_listener(self, listener):
        async with self._listeners_lock:
            self._listeners.add(listener)

    async def remove_listener(self, listener):
        async with self._listeners_lock:
            self._listeners.remove(listener)

    async def notify_listeners(self):
        async with self._listeners_lock:
            for listener in self._listeners:
                await listener(self.available)
