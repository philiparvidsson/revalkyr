from enum import Enum, auto
from typing import TypeVar

T = TypeVar("T")


class PluginResult(Enum):
    NOTHING_TO_DO = auto()
    RUN_AGAIN = auto()


class Plugin:
    def __init__(self):
        self.ctx = None
        self.log = None
        self.service_mgr = None

    def get_service(self, service_type: type[T] | str) -> T:
        return self.service_mgr.get_service(service_type)

    def init(self) -> None:
        pass

    def run(self) -> PluginResult:
        pass
