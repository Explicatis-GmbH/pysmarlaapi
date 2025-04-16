from .property import Property


class Service:

    def __init__(self):
        self.registered = False
        self.props: dict[str, Property] = {}

    def add_property(self, key: str, prop: Property):
        self.props[key] = prop

    def get_properties(self):
        return self.props

    def get_property(self, key: str):
        if key not in self.props:
            return None
        return self.props[key]

    def register(self):
        for prop in self.props.values():
            prop.register()
        self.registered = True

    def sync(self):
        for prop in self.props.values():
            prop.pull()
