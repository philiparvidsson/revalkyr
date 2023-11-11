from pathlib import Path

from .service import Service


class BindingsStore(Service):
    def has_known_bindings(self, module_name: str) -> bool:
        path = Path("../..").joinpath("bindings", module_name)
        return path.exists()

    def get_known_bindings(self, module_name: str) -> str | None:
        if not self.has_known_bindings(module_name):
            return None

        self.log.info(f"Retrieved ready-made bindings for {module_name}")
        path = Path("../..").joinpath("bindings", module_name, f"{module_name}.res")
        return path.read_text(encoding="utf-8")
