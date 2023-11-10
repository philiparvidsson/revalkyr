import re

from pathlib import Path
from textwrap import dedent

from .plugin import Plugin, PluginResult
from ..rescript.rescript_errors import (
    CompilationError,
    MissingModuleCompilationError,
    MissingValueCompilationError,
    UnknownCompilationError,
    WrongTypeCompilationError,
)
from ..services import GitHub, NPM, OpenAI, ReScript, SourceFileMgr


class AutoExternals(Plugin):
    def get_externals_dir(self) -> str:
        return self.ctx.config.src_dir.joinpath("autoexternals")

    def generate_externals_for_source_file(self, file: Path, module_name: str):
        github = self.get_service(GitHub)
        npm = self.get_service(NPM)
        openai = self.get_service(OpenAI)
        rescript = self.get_service(ReScript)
        source_file_mgr = self.get_service(SourceFileMgr)

        compiler_output = rescript.get_compiler_output()
        ast = rescript.get_ast(file)
        refs = ast.find_references(module_name)
        package_readme = github.download_readme(module_name.lower())
        package_source = github.download_source_code(module_name.lower())

        self.log("Asking AI assistant to generate externals...")

        thread = openai.create_assistant_thread()

        thread.add_message(
            f"""
            I need ReScript types and externals (@external and such) added for
            the following: {', '.join(refs)}

            Here's the ReScript source file I am currently working on:
            """
        )

        thread.add_source_code(source_file_mgr.read_file(file))

        externals_file = self.get_externals_dir().joinpath(f"{module_name}.res")
        if externals_file.exists():
            externals_source = source_file_mgr.read_file(externals_file)
            # Externals in 10 chars or less can't be useful.
            if len(externals_source) > 10:
                thread.add_message(
                    """
                    I have an externals file already. Don't remove anything unless
                    it's broken or incorrect, just add what's needed for my
                    ReScript source file to work:
                    """
                )
                thread.add_source_code(externals_source, "rescript")

        if package_source:
            thread.add_message(
                """
                Here's some of the source code for the NPM package that I need
                externals for. It's in TypeScript, but it should still give you
                an idea of how to write the externals for me.
                """
            )
            thread.add_source_code(package_source, "typescript")

        if package_readme:
            thread.add_message(
                """
                And here's the readme file for the NPM package, it will likely
                be of use when writing the externals, so you know how to @scope
                things. Sometimes you have to take extra care with @scope.
                """
            )
            thread.add_message(package_readme)

        thread.add_message(
            """
            Here's the compiler output so you know how to write the ReScript
            externals:
            """
        )
        thread.add_source_code(compiler_output, "shell")

        externals_source = thread.get_last_message().content
        externals_source = self.clean_externals_source(externals_source, module_name)
        if len(externals_source) < 10:
            self.log("Hrm, no, these externasls are not right. Let's try again.")
            self.generate_externals_for_source_file(file, module_name)
        else:
            source_file_mgr.write_file(externals_file, externals_source, overwrite=True)

    def clean_externals_source(self, source: str, module_name: str) -> str:
        # Remove backticks and crap.
        pattern = r"```.*?\n(.*?)```"
        matches = re.findall(pattern, source, re.DOTALL)
        source = "\n\n".join(matches).strip()

        # Dedent and debrace the module block, because sometimes the AI
        # generates a superfluous module block.
        source = self.debrace_module_block(source, module_name)
        return source

    def debrace_module_block(self, externals_source: str, module_name: str) -> str:
        externals_source = dedent(externals_source)
        lines = externals_source.splitlines()
        inside = False
        indent = None
        a = []
        for line in lines:
            if line.rstrip().startswith(f"module {module_name} = {{"):
                inside = True
            elif inside and line.rstrip() == "}":
                inside = False
            elif inside:
                n = len(line) - len(line.lstrip(" "))
                if indent is None:
                    indent = n
                if n >= indent:
                    line = line[indent:]
                a.append(line)
            else:
                a.append(line)
        return "\n".join(a)

    def run(self) -> PluginResult:
        rescript = self.get_service(ReScript)
        source_file_mgr = self.get_service(SourceFileMgr)

        error = rescript.get_compilation_error()
        if error is None:
            return PluginResult.NOTHING_TO_DO

        if isinstance(error, UnknownCompilationError):
            return PluginResult.NOTHING_TO_DO

        # Is there a problem in a Revalkyr generated ifle? If so, we introduced an error.
        if source_file_mgr.is_revalkyr_file(error.file):
            self.log(f"Oops, we introduced broken code!")
            source_file_mgr.delete_file(error.file)
        elif isinstance(error, MissingModuleCompilationError):
            self.log(f"Module {error.module_name} is missing. Trying to fix...")
            self.generate_externals_for_source_file(error.file, error.module_name)
        elif isinstance(error, MissingValueCompilationError):
            self.log("FOO")
        elif isinstance(error, UnknownCompilationError):
            self.log("It's not compiling, but it's not something I can fix.")
            return PluginResult.NOTHING_TO_DO
        elif isinstance(error, WrongTypeCompilationError):
            print(error)

        return PluginResult.RUN_AGAIN
