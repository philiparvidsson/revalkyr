import re
import requests
import time

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import TypeVar

from ..context import Context

T = TypeVar("T")


class CompilationError:
    def __init__(self, file: Path, line: int):
        self.file = file
        self.line = line

    def __repr__(self):
        return f"{type(self).__name__}"


class MissingModuleCompilationError(CompilationError):
    def __init__(self, file: str, line: int, module_name: str):
        super().__init__(file, line)

        self.module_name = module_name


class MissingValueCompilationError(CompilationError):
    def __init__(self, file: str, line: int, value_name: str, module_name: str):
        super().__init__(file, line)

        self.value_name = value_name
        self.module_name = module_name


class WrongTypeCompilationError(CompilationError):
    def __init__(self, file: str, line: int, given_type: str, wanted_type: str):
        super().__init__(file, line)

        self.given_type = given_type
        self.wanted_type = wanted_type


class UnknownCompilationError(CompilationError):
    pass


class Service:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    def init(self):
        pass

    def get_service(service_type: type[T]) -> T:
        pass

    def log(self, message):
        self.ctx.log(f"{type(self).__name__} :: {message}")


class Compiler(Service):
    def __init__(self, ctx: Context):
        super().__init__(ctx)

        self.compiler_output = None

    def compile(self) -> bool:
        self.log("Compiling...")

        self.compiler_output = self.ctx.rescript.get_compiler_output()

        if self.compiler_output is None:
            self.log("Compilation finished successfully.")
            return True
        else:
            self.log("Compilation failed with errors.")
            return False

    def get_ast(self, filename: Path):
        return self.ctx.rescript.get_ast(filename)

    def get_compiler_output(self):
        if not self.compiler_output:
            raise RuntimeError("There is no compiler output - compile first")

        return self.compiler_output

    def get_error(self):
        compiler_output = self.get_compiler_output()

        m = re.search(r" *(.+\.res)\:(\d+)", compiler_output)
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


class NPM(Service):
    def __init__(self, ctx: Context):
        super().__init__(ctx)

        self.repo_urls = dict()

    def get_github_repo_url(self, package_name):
        repo_url = self.repo_urls.get(package_name)
        if repo_url:
            return repo_url

        self.log(f"Looking up GitHub repository URL for {package_name} on npmjs.com...")

        url = f"https://www.npmjs.com/package/{package_name}"
        try:
            res = requests.get(url)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "lxml")
            repo_url = "https://" + soup.select_one("#repository-link").text

            self.log(f"Found it! {repo_url}")
            self.repo_urls[package_name] = repo_url
            return repo_url
        except:
            self.log("Couldn't find the package.")
        return None


class URLFetcher(Service):
    def __init__(self, ctx: Context):
        super().__init__(ctx)

        self.cache = dict()

    def get_text(url: str) -> str:
        text = self.cache(url)
        if text is not None:
            return text

        res = requests.get(readme_url)
        res.raise_for_status()

        text = res.text
        self.cache[url] = text
        return text


class GitHub(Service):
    def download_readme(self, package_name):
        npm = self.get_service(NPM)
        url_fetcher = self.get_service(URLFetcher)

        filenames = ["readme.md", "README.md"]

        repo_url = npm.get_github_repo_url(package_name)
        repo_url = repo_url.replace(
            "https://github.com", "https://raw.githubusercontent.com"
        )
        while len(filenames) > 0:
            try:
                readme_name = filenames.pop()
                readme_url = repo_url + f"/main/{readme_name}"
                readme_text = url_fetcher.get_text(readme_url)
                code_blocks = re.findall(
                    r"```(?:.*?\n)?(.*?)```", readme_text, re.DOTALL
                )
                self.log(f"Downloaded {readme_name} for package {package_name}")
                return res.text
            except:
                pass
        return None

    def download_source_code(self, package_name):
        npm = self.get_service(NPM)
        url_fetcher = self.get_service(URLFetcher)

        filenames = [
            "source/index.ts",
            "source/index.js",
            "src/index.ts",
            "src/index.js",
        ]

        repo_url = npm.get_github_repo_url(package_name)
        repo_url = repo_url.replace(
            "https://github.com", "https://raw.githubusercontent.com"
        )
        while len(filenames) > 0:
            try:
                source_name = filenames.pop()
                source_url = repo_url + f"/main/{source_name}"
                source_text = url_fetcher.get_text(source_url)
                self.log(f"Downloaded {source_name} for package {package_name}")
                return source_text
            except:
                pass
        return None


class BindingsGenerator(Service):
    def generate_bindings_for_source_file(self, file: Path, module_name: str):
        autobindings = self.get_service(AutoBindings)
        compiler = self.get_service(Compiler)
        github = self.get_service(GitHub)
        npm = self.get_service(NPM)
        source_file_mgr = self.get_service(SourceFileMgr)

        if npm.get_github_repo_url(module_name.lower()) is None:
            self.log(
                "Since I couldn't find it, I'm won't write bindings for it. Not fixing."
            )
            return False

        compiler_output = compiler.get_compiler_output()
        ast = compiler.get_ast(file)
        refs = ast.find_references(module_name)
        package_readme = github.download_readme(module_name.lower())
        package_source = github.download_source_code(module_name.lower())

        bindings_file = autobindings.get_bindings_dir().joinpath(f"{module_name}.res")
        bindings_exist = bindings_file.exists()

        thread = self.ctx.ai.create_assistant_thread()
        thread.add_message(
            f"""
            I cannot compile my ReScript project because bindings for the module
            {module_name} are missing. Specifically, {', '.join(refs)} need to
            be double-checked.

            I want you to write the bindings file for me. I am providing my
            source code so you can figure out how to write the exact bindings I
            need:
            """
        )

        thread.add_source_code(source_file_mgr.read_file(file))

        if bindings_exist:
            bindings_source = source_file_mgr.read_file(bindings_file).strip()
            if len(bindings_source) > 20:
                thread.add_message(
                    """
                    Here are the bindings I have right now, please adjust and
                    add to them as needed for my project to compile. Don't
                    remove anything unless it's broken or wrong.
                    """
                )
                thread.add_source_code(bindings_source)

        if package_readme:
            thread.add_message(
                """
                Here's the NPM package readme for the ReScript module I need:
                """
            )
            thread.add_message(package_readme)

        if package_source:
            thread.add_message(
                """
                On top of that, here's the NPM package's main source file where
                the exports are done. They are not in ReScript, but you can use
                it to figoure out how to write accurate bindings.
                """
            )
            thread.add_source_code(package_source, "typescript")

        thread.add_message(
            """
            And here's the error message the ReScript compiler is giving me:
            """
        )
        thread.add_source_code(compiler_output, "bash")

        thread.add_message(
            """
            That's all I have. Please write the ReScript bindings for me.
            Remember to write them in proper ReScript language, and only give me
            the file contents back.
            """
        )

        self.log("Asking AI assistant to generate bindings...")
        bindings_source = thread.get_last_message().content
        bindings_source = self.clean_bindings_source(bindings_source, module_name)
        if len(bindings_source) < 10:
            self.log("Hrm, no, these bindings are not right. Let's try again.")
            self.generate_bindings_for_source_file(file, module_name)
        else:
            source_file_mgr.write_file(bindings_file, bindings_source, overwrite=True)

        return True

    def clean_bindings_source(self, module_source: str, module_name: str) -> str:
        # Remove backticks and crap.
        pattern = r"```.*?\n(.*?)```"
        matches = re.findall(pattern, module_source, re.DOTALL)
        module_source = "\n\n".join(matches).strip()

        # Dedent and debrace the module block, because sometimes the AI
        # generates a superfluous module block.
        module_source = self.debrace_module_block(module_source, module_name)
        return module_source

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


class AutoBindings(Service):
    def get_bindings_dir(self) -> Path:
        return self.ctx.config.src_dir.joinpath("autobinds")

    def is_autobindings_exist(self, module_name):
        return self.get_bindings_dir().joinpath(f"{module_name}.res").exists()

    def fix_problematic_bindings(self):
        compiler = self.get_service(Compiler)
        bindings_generator = self.get_service(BindingsGenerator)
        source_file_mgr = self.get_service(SourceFileMgr)

        if compiler.compile():
            self.log("Bindings are ok - or at least we can compile.")
            return True

        error = compiler.get_error()
        if isinstance(error, UnknownCompilationError):
            if (
                error.file.parent.resolve() == self.get_bindings_dir().resolve()
                and source_file_mgr.is_generated_by_us(error.file)
            ):
                self.log(f"Oops, we generated bad bindings!")
                source_file_mgr.delete_file(error.file)
            else:
                self.log("Compilation has errors, but I don't know how to fix them")

        if isinstance(error, MissingModuleCompilationError):
            self.log(
                f"Module {error.module_name} is missing. This is something we can fix!"
            )
            if not bindings_generator.generate_bindings_for_source_file(
                error.file, error.module_name
            ):
                self.log("No bindings were generated.")
                return True

        if isinstance(error, MissingValueCompilationError):
            self.log(
                f"Value '{error.value_name}' is missing in module {error.module_name}. This is something we can fix!"
            )
            if not bindings_generator.generate_bindings_for_source_file(
                error.file, error.module_name
            ):
                self.log("No bindings were generated.")
                return True

        if isinstance(error, WrongTypeCompilationError):
            module_name = error.wanted_type.split(".")[0]
            if self.is_autobindings_exist(module_name):
                self.log(
                    f"There's a type error related to an autobinding in {module_name}. We'll try to fix it."
                )
                if not bindings_generator.generate_bindings_for_source_file(
                    error.file, module_name
                ):
                    self.log("No bindings were generated.")
                    return True
            self.log("There's some type error that I can't fix.")
            return True

        return False


class SourceFileMgr(Service):
    def check_permitted(self, file: Path):
        src_dir = self.ctx.config.src_dir.resolve()
        if not str(file.resolve()).startswith(str(src_dir)):
            raise RuntimeError("Not permitted - cannot touch files outside src dir")

    def is_generated_by_us(self, file: Path) -> bool:
        self.check_permitted(file)
        return file.read_text(encoding="utf-8").startswith("// revalkyr ")

    def delete_file(self, file: Path):
        self.check_permitted(file)
        if not self.is_generated_by_us(file):
            raise RuntimeError("Not permitted - we didn't create the file")
        file.unlink()
        self.log(f"Deleted {file}")

    def read_file(self, file: Path) -> str:
        self.check_permitted(file)
        content = file.read_text(encoding="utf-8")
        if content.startswith("// revalkyr"):
            content = "\n".join(content.splitlines()[1:])
        return content

    def write_file(self, file: Path, content: str, overwrite: bool = False):
        self.check_permitted(file)
        if file.exists():
            if not self.is_generated_by_us(file):
                raise RuntimeError("Not permitted - we didn't create the file")

            if not overwrite:
                raise RuntimeError("Not permitted - file exists already")

        file.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"// revalkyr {timestamp}\n" + content
        file.write_text(content, encoding="utf-8")

        self.log(f"Wrote {file} ({len(content)} chars)")


def run(ctx: Context):
    ctx.log()

    service_types = [
        AutoBindings,
        BindingsGenerator,
        Compiler,
        GitHub,
        NPM,
        SourceFileMgr,
        URLFetcher,
    ]

    services = dict()
    for service_type in service_types:
        service = service_type(ctx)
        services[service_type] = service
        service.get_service = lambda service_type: services.get(service_type)

    for service in services.values():
        service.init()
        ctx.log(f"Spun up {type(service).__name__} service.")

    ctx.log()

    while 1:
        r = services[AutoBindings].fix_problematic_bindings()
        if r:
            break
        time.sleep(1)
