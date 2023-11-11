from pathlib import Path


class CompilationError:
    def __init__(self, file: Path, line: int):
        self.file = file
        self.line = line

    def __repr__(self):
        return f"{type(self).__name__}(file={self.file}, line={self.line})"


class MissingModuleCompilationError(CompilationError):
    def __init__(self, file: str, line: int, module_name: str):
        super().__init__(file, line)

        self.module_name = module_name


class MissingValueCompilationError(CompilationError):
    def __init__(self, file: str, line: int, value_name: str, module_name: str):
        super().__init__(file, line)

        self.value_name = value_name
        self.module_name = module_name


class SyntaxCompilationError(CompilationError):
    pass


class WrongTypeCompilationError(CompilationError):
    def __init__(self, file: str, line: int, given_type: str, wanted_type: str):
        super().__init__(file, line)

        self.given_type = given_type
        self.wanted_type = wanted_type


class UnknownCompilationError(CompilationError):
    pass
