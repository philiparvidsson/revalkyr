from typing import TypeVar

from ..context import Context

T = TypeVar("T")


class Service:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    def init(self) -> None:
        # Overridden by services that need initialization logic.
        pass

    def get_service(self, service_type: type[T] | str) -> T:
        # This method will be set by the service manager.
        pass

    def log(self, message: str) -> None:
        self.ctx.log(f"{type(self).__name__} :: {message}")
