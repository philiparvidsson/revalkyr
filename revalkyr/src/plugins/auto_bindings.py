import re

from pathlib import Path
from textwrap import dedent

from .plugin import Plugin, PluginResult
from ..rescript.rescript_errors import (
    CompilationError,
    MissingModuleCompilationError,
    MissingValueCompilationError,
    SyntaxCompilationError,
    UnknownCompilationError,
    WrongTypeCompilationError,
)
from ..services import BindingsStore, GitHub, NPM, OpenAI, ReScript, SourceFileMgr
from ..services.ai import AssistantThread


class AutoBindings(Plugin):
    def is_revalkyr_bindings_file(self, file: Path):
        source_file_mgr = self.get_service(SourceFileMgr)
        return source_file_mgr.is_revalkyr_file(file) and str(
            file.resolve()
        ).startswith(str(self.get_bindings_dir().resolve()))

    def get_bindings_dir(self) -> str:
        return self.ctx.config.src_dir.joinpath("autobindings")

    def get_thread(self, name: str) -> [AssistantThread, bool]:
        self.log.info("Asking the AI assistant for help...")

        openai = self.get_service(OpenAI)

        is_new = False

        if name not in self.threads:
            self.log.debug(f"Created new AI thread (name='{name}')")
            self.threads[name] = openai.create_assistant_thread()
            is_new = True

        return (self.threads[name], is_new)

    def add_readme_and_source(self, thread: AssistantThread, package_name: str) -> None:
        github = self.get_service(GitHub)

        github_readme = github.download_readme(package_name)
        github_source = github.download_source_code(package_name)
        if github_readme:
            thread.add_message(
                f"""
                I need ReScript bindings for the NPM package {package_name}. To
                begin with, here's some documentation for the NPM package. It's
                a TypeScript package, but it should still tell you how the
                package works so that you can implement the ReScript bindings
                properly.
                """
            )
            thread.add_message(github_readme)

        if github_source:
            thread.add_message(
                """
                Here's some of the package's source code (in TypeScript) which
                might be of help when creating types, bindings and let bindings,
                as well as how to @scope the different bindings.
                """
            )
            thread.add_source_code(github_source, "typescript")

    def generate_bindings(self, file: Path, module_name: str) -> PluginResult:
        bindings_store = self.get_service(BindingsStore)
        npm = self.get_service(NPM)
        rescript = self.get_service(ReScript)
        source_file_mgr = self.get_service(SourceFileMgr)

        if not npm.is_npm_package(module_name.lower()):
            # We only deal with NPM packages.
            return PluginResult.NOTHING_TO_DO

        ast = rescript.get_ast(file)
        refs = ast.find_references(module_name)

        thread, is_new_thread = self.get_thread(f"{module_name}.res")

        if is_new_thread:
            self.add_readme_and_source(thread, module_name.lower())

        thread.add_message(
            f"""
            Write the ReScript bindings for me so I can compile my project. I
            need bindings added for: {", ".join(map(lambda ref: ref.name, refs))}

            Here's the ReScript language source file that is not compiling:
            """
        )

        thread.add_source_code(source_file_mgr.read_file(file), "rescript")

        thread.add_message(
            """
            And here's the ReScript compiler output showing the compilation
            error:
            """
        )
        thread.add_source_code(rescript.get_compiler_output(), "shell")

        bindings_file = self.get_bindings_dir().joinpath(f"{module_name}.res")
        if bindings_file.exists():
            bindings_source = source_file_mgr.read_file(bindings_file)
            # Need more than 10 chars for the file to be intersting.
            if len(bindings_source) > 10:
                thread.add_message(
                    f"""
                    Here's the current {module_name}.res file, by the way. You
                    can add your code to it; don't remove anything that isn't
                    broken.
                    """
                )
                thread.add_source_code(bindings_source, "rescript")

        lf = "\n        "
        bindings_suggestion_source = f"""
        // {module_name}.res
        // 1. Js, Belt, promise<>, option<> and so on are built-in
        //    modules/types, do not try to add definitions for them!
        // 2. Remember to add @scope() as needed for the bindings to work
        //    properly! Some NPM packages (especially those with default
        //    exports) might require @scope("default") to work properly.
        // 3. You can't use @module and @send together - it's one or the other.

        type t

        {lf.join(map(lambda ref: f'@module("{module_name.lower()}"){lf}external {ref.name}: ... = "{ref.name}"{lf}', refs))}
        """

        if bindings_store.has_known_bindings(module_name):
            bindings_suggestion_source = bindings_store.get_known_bindings(module_name)

        bindings_suggestion = f"""
        Here's a suggestion for how the bindings might look:

        ```rescript
        {bindings_suggestion_source}
        ```

        Alright, please write the file for me and reply back to me with the
        contents of the file only (don't say anything else, but if you feel the
        need to, you can add comments to the file). The file must be
        self-contained, compilable, correct, error-free and written in proper
        and accurate ReScript language source code.

        I have my own style of writing ReScript and since bindings can be done
        in many different ways, make sure to adjust your bindings where
        possible, so that they fit with my particular code.
        """

        thread.add_message(bindings_suggestion)

        thread.run()
        bindings_source = thread.get_last_message().content
        bindings_source = self.clean_bindings_source(bindings_source, module_name)
        source_file_mgr.write_file(bindings_file, bindings_source, True)

        return PluginResult.RUN_AGAIN

    def fix_bindings(self, file: Path) -> PluginResult:
        rescript = self.get_service(ReScript)
        source_file_mgr = self.get_service(SourceFileMgr)

        thread, is_new_thread = self.get_thread(file.name)

        if is_new_thread:
            self.add_readme_and_source(thread, module_name.lower())

        thread.add_message("There's a problem with the file you gave me:")
        thread.add_source_code(rescript.get_compiler_output(), "shell")
        thread.add_message(
            f"""
            Make sure you're not using @module and @send together, for example.

            Fix the issue for me and give me a new version {file.name}.
            """
        )

        thread.add_message("Here's the file I have right now:")
        thread.add_source_code(source_file_mgr.read_file(file), "rescript")

        thread.add_message(
            """
            Fix the error in your code and give me the new, fixed version with
            correct, accurate, error-free, self-contained and compiling ReScript
            code, that addresses the error in the compiler output and lets my
            project compile.

            Remember to use @scope properly as well, since some modules (that
            use default exports, for example), require @scope("default") to
            work.
            """
        )

        thread.run()
        bindings_source = thread.get_last_message().content
        bindings_source = self.clean_bindings_source(bindings_source, file.stem)
        source_file_mgr.write_file(file, bindings_source, True)

        return PluginResult.RUN_AGAIN

    def clean_bindings_source(self, source: str, module_name: str) -> str:
        # Remove backticks and crap.
        pattern = r"```.*?\n(.*?)```"
        matches = re.findall(pattern, source, re.DOTALL)
        source = "\n\n".join(matches).strip()

        # Dedent and debrace the module block, because sometimes the AI
        # generates a superfluous module block.
        # source = self.debrace_module_block(source, module_name)
        return source

    def debrace_module_block(self, bindings_source: str, module_name: str) -> str:
        bindings_source = dedent(bindings_source)
        lines = bindings_source.splitlines()
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

    def init(self) -> None:
        self.threads: dict[str, AssistantThread] = dict()

    def run(self) -> PluginResult:
        rescript = self.get_service(ReScript)
        source_file_mgr = self.get_service(SourceFileMgr)

        error = rescript.get_compilation_error()
        if error is None:
            return PluginResult.NOTHING_TO_DO

        # Is there a problem in a Revalkyr generated ifle? If so, we introduced an error.
        if source_file_mgr.is_revalkyr_file(error.file):
            self.log.warn("Hrm, we might have introduced broken code...")
            if isinstance(error, SyntaxCompilationError):
                source_file_mgr.delete_file(error.file)
            else:
                self.fix_bindings(error.file)

        elif isinstance(error, MissingModuleCompilationError):
            self.log.info(f"Module {error.module_name} is missing. Trying to fix...")
            return self.generate_bindings(error.file, error.module_name)

        elif isinstance(error, MissingValueCompilationError):
            self.log.info(
                f"Value {error.value_name} is missing in {error.module_name}. Trying to fix..."
            )
            return self.generate_bindings(error.file, error.module_name)

        elif isinstance(error, UnknownCompilationError):
            self.log.warn("It's not compiling, but it's not something I can fix.")
            return PluginResult.NOTHING_TO_DO

        elif isinstance(error, WrongTypeCompilationError):
            given = error.given_type.split(".")[0]
            wanted = error.wanted_type.split(".")[0]

            try_to_fix = False

            # If given or wanted refers to a Revalkyr bindings file.
            if self.is_revalkyr_bindings_file(
                self.get_bindings_dir().joinpath(f"{given}.res")
            ):
                try_to_fix = True
                module_name = given
            elif self.is_revalkyr_bindings_file(
                self.get_bindings_dir().joinpath(f"{wanted}.res")
            ):
                try_to_fix = True
                module_name = wanted

            if try_to_fix:
                return self.generate_bindings(error.file, module_name)

        self.log.debug("Nothing to do...")
        return PluginResult.NOTHING_TO_DO
