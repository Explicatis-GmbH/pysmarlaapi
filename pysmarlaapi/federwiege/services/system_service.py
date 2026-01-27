from ...connection_hub import ConnectionHub
from ..classes import Property, Service
from ..types import SendDiagStatus, UpdateStatus


class SystemService(Service):

    def __init__(self, hub: ConnectionHub):
        super().__init__()
        self.add_property("firmware_update", FirmwareUpdateProperty(hub))
        self.add_property("firmware_update_status", FirmwareUpdateStatusProperty(hub))
        self.add_property("send_diagnostic_data", SendDiagnosticDataProperty(hub))
        self.add_property("send_diagnostic_data_status", SendDiagnosticDataStatusProperty(hub))


class FirmwareUpdateProperty(Property[int]):

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def push(self, value: int):
        self.hub.send_serialized_data("SetFirmwareUpdate", value)


class FirmwareUpdateStatusProperty(Property[UpdateStatus]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetFirmwareUpdate")

    def register(self):
        self.hub.client.on("GetFirmwareUpdateCallback", self.on_callback)


class SendDiagnosticDataProperty(Property[str]):

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def push(self, value: str):
        self.hub.send_serialized_data("SetSendDiagnosticData", value)


class SendDiagnosticDataStatusProperty(Property[SendDiagStatus]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetSendDiagnosticData")

    def register(self):
        self.hub.client.on("GetSendDiagnosticDataCallback", self.on_callback)
