from typing import TypeVar

from ..context import Context

T = TypeVar("T")


class Service:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.log = ctx.log

    def init(self) -> None:
        # Overridden by services that need initialization logic.
        pass

    def get_service(self, service_type: type[T] | str) -> T:
        # This method will be set by the service manager.
        pass
