from ...connection_hub import ConnectionHub
from ..classes import Property, Service


class InfoService(Service):

    def __init__(self, hub: ConnectionHub):
        super().__init__()
        self.add_property("display_name", DisplayNameProperty(hub))
        self.add_property("version", VersionProperty(hub))


class DisplayNameProperty(Property[str]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetDisplayName")

    def register(self):
        self.hub.client.on("GetDisplayNameCallback", self.on_callback)


class VersionProperty(Property[str]):

    async def on_callback(self, args):
        value = args[0]["value"]
        self.set(value, push=False)
        await self.notify_listeners()

    def __init__(self, hub: ConnectionHub):
        super().__init__(hub)

    def pull(self):
        self.hub.send_serialized_data("GetVersion")

    def register(self):
        self.hub.client.on("GetVersionCallback", self.on_callback)
