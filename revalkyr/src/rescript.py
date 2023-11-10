import re
import subprocess


class ReScriptASTNode:
    def __init__(self, data: list):
        pattern = r'(?:(?<=\s)|^)\([^()]*\)|[^\s"\'()]+|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
        self.data = [m.strip("\"'") for m in re.findall(pattern, data[0])]
        self.type = self.data[0]

        self.children = [ReScriptASTNode(c) for c in data[1]]

    def __str__(self):
        s = f"{' '.join(self.data)}"
        for child in self.children:
            s += "\n" + "\n  ".join(str(child).splitlines())
        return s


class ReScriptAST:
    def __init__(self, root: ReScriptASTNode):
        self.root = root

    def find_references(
        self, identifier: str, root: ReScriptASTNode = None
    ) -> list[str]:
        if root is None:
            root = self.root

        refs = []

        for child in root.children:
            if child.type == "Pexp_ident":
                name = child.data[1]
                if name == identifier or name.startswith(f"{identifier}."):
                    refs.append(name)

            refs.extend(self.find_references(identifier, child))

        return refs

    @staticmethod
    def parse(compiler_output: str):
        l = compiler_output.splitlines()

        def p():
            while len(l[0].strip()) == 0 or l[0].strip() == "<arg>":
                l.pop(0)
            if l[0].strip() == "[]":
                l.pop(0)
                return ["<empty>", []]
            if l[0].strip() == "[":
                l.pop(0)
                a = []
                while 1:
                    a.append(p())
                    if l[0].strip() == "]":
                        l.pop(0)
                        break
                return ["<list>", a]
            i = len(l[0]) - len(l[0].lstrip())
            n = l.pop(0).strip()
            c = []
            while 1:
                j = len(l[0]) - len(l[0].lstrip())
                if j <= i:
                    break
                c.append(p())
            return [n, c]

        root = ReScriptASTNode(p())
        ast = ReScriptAST(root)
        return ast


class ReScript:
    def __init__(self):
        self._compiler_output = None

    def npm_run(self, command: str, *args: list[str]):
        command = "./node_modules/.bin/" + command
        return subprocess.run([command, *args], capture_output=True, text=True)

    def get_compiler_output(self):
        self.check_for_changes()

        if self._compiler_output is None:
            result = self.npm_run("rescript")
            if result.returncode == 0:
                self._compiler_output = None
            else:
                self._compiler_output = result.stdout

        return self._compiler_output

    def get_ast(self, filename: str):
        result = self.npm_run("bsc", "-dparsetree", filename)
        if result.returncode == 0:
            return None

        return ReScriptAST.parse(result.stderr)

    def check_for_changes(self):
        self._compiler_output = None
        pass
