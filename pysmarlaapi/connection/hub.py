import asyncio
import logging
import random
import uuid

from pysignalr.client import SignalRClient
from pysignalr.transport.abstract import ConnectionState

from . import Connection
from .exceptions import AuthenticationException, ConnectionException


async def event_wait(event, timeout) -> bool:
    try:
        await asyncio.wait_for(event.wait(), timeout)
    except asyncio.TimeoutError:
        return False
    return True


# suppress warnings from pysignalr (to avoid missing client method warnings)
logging.getLogger('pysignalr.client').setLevel(logging.ERROR)


class ConnectionHub:
    """SignalRCore Hub
    Provides interface via websocket for the controller using the SignalRCore protocol.
    """

    @property
    def running(self):
        return self._running

    @property
    def connected(self):
        return self.client._transport._state == ConnectionState.connected

    def __init__(
        self,
        event_loop: asyncio.AbstractEventLoop,
        connection: Connection,
        connection_callback = None,
        auth_failure_callback = None,
        max_delay: int = 256,
    ):
        self.connection: Connection = connection
        self._loop = event_loop
        self._retry_delay = 1 # Initial connection retry delay
        self._max_delay = max_delay

        self.logger = logging.getLogger(f"{__package__}[{self.connection.token.serialNumber}]")

        self.connection_callback = connection_callback
        self.auth_failure_callback = auth_failure_callback

        self._running = False
        self._wake = asyncio.Event()

        self.client = SignalRClient(self.connection.url + "/MobileAppHub", retry_count=1)
        self.client.on_open(self.on_open_function)
        self.client.on_close(self.on_close_function)
        self.client.on_error(self.on_error)
        self.client.on("SetNotifyAppConnectionCallback", self.notifycontrollerconnection)

    def on(self, event: str, callback):
        self.client.on(event, callback)

    async def notifycontrollerconnection(self, args):
        value = args[0]
        if value == "ControllerConnected":
            self.logger.info("Controller connected")
            if self.connection_callback:
                await self.connection_callback(True)
        else:
            self.logger.info("Controller disconnected")
            if self.connection_callback:
                await self.connection_callback(False)

    async def on_open_function(self):
        self._retry_delay = 1
        self.logger.info("Connection to server established")

    async def on_close_function(self):
        self.logger.info("Connection to server closed")
        if self.connection_callback:
            await self.connection_callback(False)

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
        self.wake_up()
        asyncio.run_coroutine_threadsafe(self.close_connection(), self._loop)

    async def connection_watcher(self):
        while self.running:
            try:
                response = await self.refresh_connection()
            except AuthenticationException:
                self.logger.warning("Authentication failed, Won't retry.")
                if self.auth_failure_callback:
                    await self.auth_failure_callback()
                return

            if response:
                try:
                    await self.client.run()
                except Exception as e:
                    self.logger.warning("Error during connection: %s: %s", type(e).__name__, str(e))

            # Random backoff to avoid simultaneous connection attempts
            jitter = random.uniform(0, 0.5) * self._retry_delay
            delay = self._retry_delay + jitter

            self.logger.debug("Will retry connection in %i seconds.", delay)

            await event_wait(self._wake, delay)
            self._wake.clear()

            # Double the delay for the next attempt
            if self._retry_delay < self._max_delay:
                self._retry_delay *= 2

    def wake_up(self):
        self._wake.set()

    async def close_connection(self):
        if not self.connected:
            return
        await self.client._transport._ws.close()

    async def refresh_connection(self) -> bool:
        try:
            await self.connection.refresh_token()
        except ConnectionException:
            self.logger.warning("Failed to refresh auth token")
            return False

        self.client._transport._headers["Authorization"] = f"Bearer {self.connection.get_token()}"
        self.logger.info("Auth token refreshed")
        return True

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
