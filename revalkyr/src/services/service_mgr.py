from .service import Service
from ..context import Context


class ServiceMgr:
    def __init__(self, ctx: Context, service_types: list[type[Service]]):
        self.ctx = ctx
        self.service_types = service_types

    def init(self):
        self._services: dict[str, Service] = dict()

        for service_type in self.service_types:
            service = service_type(self.ctx)
            self._services[service_type.__name__] = service

            service.get_service = self.get_service

        for service in self._services.values():
            service.init()

    def get_service(self, service_type: type[Service] | str) -> Service:
        k = service_type if isinstance(service_type, str) else service_type.__name__
        if k not in self._services:
            raise KeyError(f"No such service provided: {k}")
        return self._services[k]
