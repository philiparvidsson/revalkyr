class Context:
    def __init__(
        self,
        config,
    ):
        self.config = config

    def log(self, message: str = None):
        print(message or "")
