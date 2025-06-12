from ...connection_hub import ConnectionHub
from ..classes import Property, Service


class BabywiegeService(Service):

    def __init__(self, hub: ConnectionHub):
        super().__init__()
        self.add_property("swing_active", SwingActiveProperty(hub))
        self.add_property("intensity", IntensityProperty(hub))
        self.add_property("smart_mode", SmartModeProperty(hub))


class SwingActiveProperty(Property[bool]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetSwingActive")

    def push(self, value: bool):
        self.hub.send_serialized_data("SetSwingActive", value)

    def register(self):
        self.hub.client.on("GetSwingActiveCallback", self.on_callback)


class IntensityProperty(Property[int]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetIntensity")

    def push(self, value: int):
        self.hub.send_serialized_data("SetIntensity", value)

    def register(self):
        self.hub.client.on("GetIntensityCallback", self.on_callback)


class SmartModeProperty(Property[bool]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetSmartMode")

    def push(self, value: bool):
        self.hub.send_serialized_data("SetSmartMode", value)

    def register(self):
        self.hub.client.on("GetSmartModeCallback", self.on_callback)
