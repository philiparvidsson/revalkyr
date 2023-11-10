from .ai import OpenAI
from .rescript import ReScript
from .config import Config


class Context:
    def __init__(self, config: Config, ai: OpenAI = None, rescript: ReScript = None):
        self.ai = ai if ai is not None else OpenAI()
        self.config = config
        self.rescript = rescript if rescript is not None else ReScript()

    def log(self, message: str = None):
        print(message or "")
