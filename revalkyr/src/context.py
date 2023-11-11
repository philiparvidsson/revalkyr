from .log import Log


class Context:
    def __init__(
        self,
        config,
    ):
        self.config = config
        self.log = Log()
