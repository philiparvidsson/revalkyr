import re
import subprocess

from pathlib import Path

from .service import Service
from ..context import Context
from ..rescript.rescript_ast import AST, Node
from ..rescript.rescript_errors import (
    CompilationError,
    MissingModuleCompilationError,
    MissingValueCompilationError,
    UnknownCompilationError,
    WrongTypeCompilationError,
)
from ..utils.file_watcher import FileWatcher


class ReScript(Service):
    def __init__(self, ctx: Context):
        super().__init__(ctx)

        self.compiler_output: str | None = None

    def init(self):
        self.src_dir_watcher = FileWatcher(self.ctx.config.src_dir)

    def compile(self) -> bool:
        self.log("Compiling...")

        result = self._npm_run("rescript")
        if result.returncode == 0:
            self.compiler_output = None

            self.log("Compilation finished successfully")
            return True

        self.compiler_output = result.stdout

        self.log("Compilation failed with errors")
        return False

    def compile_if_needed(self) -> None:
        if self.src_dir_watcher.has_changed():
            self.compile()

    def get_ast(self, filename: Path) -> AST:
        result = self._npm_run("bsc", "-dparsetree", filename)
        if result.returncode == 0:
            return None

        return AST.parse(result.stderr)

    def get_compiler_output(self) -> str | None:
        self.compile_if_needed()
        return self.compiler_output

    def get_compilation_error(self) -> CompilationError | None:
        compiler_output = self.get_compiler_output()
        if not compiler_output:
            return None

        m = re.search(r" *(.+\.res)\:(\d+)", compiler_output)
        if not m:
            return None

        file = Path(m.group(1)).relative_to(Path.cwd())
        line = int(m.group(2))

        m = re.search(r"The module or file (.+) can't be found\.", compiler_output)
        if m:
            return MissingModuleCompilationError(file, line, m.group(1))

        m = re.search(r"The value (.+) can't be found in (.+)", compiler_output)
        if m:
            return MissingValueCompilationError(file, line, m.group(1), m.group(2))

        m = re.search(r"This has type: (.+)\n *Somewhere wanted: (.+)", compiler_output)
        if m:
            return WrongTypeCompilationError(file, line, m.group(1), m.group(2))

        return UnknownCompilationError(file, line)

    def _npm_run(self, command: str, *args: list[str]):
        command = Path(".").joinpath("node_modules", ".bin", command)
        return subprocess.run([command, *args], capture_output=True, text=True)
