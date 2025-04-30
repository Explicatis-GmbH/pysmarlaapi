import asyncio
import threading

from ..classes import Connection
from ..connection_hub import ConnectionHub
from .classes import Service
from .services import AnalyserService, BabywiegeService, InfoService


class Federwiege:

    @property
    def running(self):
        return self.hub.running

    @property
    def connected(self):
        return self.hub.connected

    async def on_controller_connection_change(self, value):
        self.available = value
        if value:
            self.sync()

    def __init__(self, event_loop: asyncio.AbstractEventLoop, connection: Connection):
        self.serial_number = connection.token.serialNumber
        self.hub = ConnectionHub(event_loop, connection)
        self.services: dict[str, Service] = {
            "babywiege": BabywiegeService(self.hub),
            "analyser": AnalyserService(self.hub),
            "info": InfoService(self.hub),
        }

        self.registered = False
        self._lock = threading.Lock()

        self.available = False

    def get_service(self, key: str):
        if key not in self.services:
            return None
        return self.services[key]

    def get_property(self, service_key: str, prop_key: str):
        service = self.get_service(service_key)
        if not service:
            return None
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
            self.registered = True
            self.hub.add_listener(self.on_controller_connection_change)
            for service in self.services.values():
                service.register()
