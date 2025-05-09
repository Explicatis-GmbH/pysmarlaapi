import asyncio
import logging
import random
import uuid

from pysignalr.client import SignalRClient
from pysignalr.transport.abstract import ConnectionState

from ..classes import Connection


async def event_wait(event, timeout):
    try:
        await asyncio.wait_for(event.wait(), timeout)
    except asyncio.TimeoutError:
        return


class ConnectionHub:
    """SignalRCore Hub
    Provides interface via websocket for the controller using the SignalRCore protocol.
    """

    @property
    def running(self):
        return self._running

    @property
    def connected(self):
        return self.client._transport._state == ConnectionState.connected if self.client else False

    def __init__(
        self,
        event_loop: asyncio.AbstractEventLoop,
        connection: Connection,
        interval: int = 60,
        backoff: int = 300,
    ):
        self.connection: Connection = connection
        self._loop = event_loop
        self._interval = interval
        self._backoff = backoff

        self.logger = logging.getLogger(f"{__package__}[{self.connection.token.serialNumber}]")

        self.listeners = set()

        self._running = False
        self._wake = asyncio.Event()

        self.client = None
        self.setup()

    async def notifycontrollerconnection(self, args):
        value = args[0]
        if value == "ControllerConnected":
            await self.notify_listeners(True)
        else:
            await self.notify_listeners(False)

    def setup(self):
        self.client = SignalRClient(self.connection.url + "/MobileAppHub", retry_count=1)
        self.client.on_open(self.on_open_function)
        self.client.on_close(self.on_close_function)
        self.client.on_error(self.on_error)
        self.client.on("SetNotifyAppConnectionCallback", self.notifycontrollerconnection)

    def add_listener(self, listener):
        if self.running:
            return
        self.listeners.add(listener)

    def remove_listener(self, listener):
        if self.running:
            return
        self.listeners.remove(listener)

    async def notify_listeners(self, value):
        for listener in self.listeners:
            await listener(value)

    async def on_open_function(self):
        self.logger.info("Connection to server established")

    async def on_close_function(self):
        self.logger.info("Connection to server closed")

    async def on_error(self, message):
        self.logger.error("Connection error occurred: %s", str(message))

    def start(self):
        if self.running:
            return
        self._running = True
        asyncio.run_coroutine_threadsafe(self.connection_watcher(), self._loop)

    def stop(self):
        if not self.running:
            return
        self._running = False
        self.close_connection()
        self.wake_up()

    async def connection_watcher(self):
        while self.running:
            await self.refresh_token()
            try:
                await self.client.run()
            except Exception as e:
                self.logger.warning("Error during connection: %s: %s", type(e).__name__, str(e))

            # Random backoff to avoid simultaneous connection attempts
            backoff = random.randint(0, self._backoff)
            await event_wait(self._wake, self._interval + backoff)
            self._wake.clear()

    def wake_up(self):
        self._wake.set()

    def close_connection(self):
        if not self.connected:
            return
        asyncio.run_coroutine_threadsafe(self.client._transport._ws.close(), self._loop)

    async def refresh_token(self):
        await self.connection.refresh_token()
        self.client._transport._headers["Authorization"] = f"Bearer {self.connection.get_token()}"
        self.logger.info("Auth token refreshed")

    def send_serialized_data(self, event, value=None):
        serialized_result = {
            "callIdentifier": {
                "requestNonce": str(uuid.uuid4()),
            },
        }
        if value is not None:
            serialized_result["value"] = value

        self.logger.debug("Sending data, Event: %s, Payload: %s", event, str(serialized_result))

        asyncio.run_coroutine_threadsafe(self.async_send_data(event, [serialized_result]), self._loop)

    async def async_send_data(self, event, data):
        try:
            await self.client.send(event, data)
        except Exception:
            pass
