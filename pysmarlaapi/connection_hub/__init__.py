import asyncio
import logging
import random
import uuid

from pysignalr.client import SignalRClient
from pysignalr.transport.abstract import ConnectionState

from ..classes import Connection


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
        return self.client._transport._state == ConnectionState.connected if self.client else False

    def __init__(
        self,
        event_loop: asyncio.AbstractEventLoop,
        connection: Connection,
        max_delay: int = 256,
        forced_reconnect_interval: int = 86400,
    ):
        self.connection: Connection = connection
        self._loop = event_loop
        self._retry_delay = 1 # Initial connection retry delay
        self._max_delay = max_delay
        self._forced_reconnect_interval = forced_reconnect_interval

        self.logger = logging.getLogger(f"{__package__}[{self.connection.token.serialNumber}]")

        self.listeners = set()

        self._running = False
        self._wake = asyncio.Event()

        self._reconnect_future: asyncio.Future = None
        self._reconnect_lock = asyncio.Lock()
        self._reconnect_cancel_event = asyncio.Event()

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
        self._retry_delay = 1
        self.logger.info("Connection to server established")
        await self.start_reconnect_job()

    async def on_close_function(self):
        self.logger.info("Connection to server closed")
        await self.cancel_reconnect_job()

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
            await self.refresh_token()
            try:
                await self.client.run()
            except Exception as e:
                self.logger.warning("Error during connection: %s: %s", type(e).__name__, str(e))

            # Random backoff to avoid simultaneous connection attempts
            jitter = random.uniform(0, 0.5) * self._retry_delay
            delay = self._retry_delay + jitter
            await event_wait(self._wake, delay)
            self._wake.clear()

            # Double the delay for the next attempt
            if self._retry_delay < self._max_delay:
                self._retry_delay *= 2

    def wake_up(self):
        self._wake.set()

    async def close_connection(self):
        await self.cancel_reconnect_job()
        await self.client._transport._ws.close()

    async def start_reconnect_job(self):
        async with self._reconnect_lock:
            if self._reconnect_future and not self._reconnect_future.done():
                return
            self._reconnect_cancel_event.clear()
            self._reconnect_future = asyncio.create_task(self.reconnect_job())

    async def cancel_reconnect_job(self):
        async with self._reconnect_lock:
            if not self._reconnect_future or self._reconnect_future.done():
                return
            self._reconnect_cancel_event.set()
            await self._reconnect_future

    async def reconnect_job(self):
        cancelled = await event_wait(self._reconnect_cancel_event, self._forced_reconnect_interval)
        if cancelled:
            return

        # Close connection to trigger a reconnection
        # Make sure that connection stays healthy
        await self.client._transport._ws.close()

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
