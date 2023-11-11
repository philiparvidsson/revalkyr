import re


class Ident:
    def __init__(self, name: str):
        self.module_name: str | None = None
        self.name: str | None = None

        a = name.split(".")
        if len(a) > 1:
            self.module_name = a[0]
            self.name = a[1]
        else:
            self.name = a[0]

    def __str__(self):
        if self.module_name:
            return f"{self.module_name}.{self.name}"
        return self.name


class Node:
    def __init__(self, data: list):
        pattern = r'(?:(?<=\s)|^)\([^()]*\)|[^\s"\'()]+|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
        self.data = [m.strip("\"'") for m in re.findall(pattern, data[0])]
        self.type = self.data[0]

        self.children = [Node(c) for c in data[1]]

    def __str__(self):
        s = f"{' '.join(self.data)}"
        for child in self.children:
            s += "\n" + "\n  ".join(str(child).splitlines())
        return s


class AST:
    def __init__(self, root: Node):
        self.root = root

    def find_references(self, identifier: str, root: Node = None) -> list[Ident]:
        if root is None:
            root = self.root

        refs = []

        for child in root.children:
            if child.type == "Pexp_ident":
                name = child.data[1]
                if name == identifier or name.startswith(f"{identifier}."):
                    refs.append(name)

            refs.extend(self.find_references(identifier, child))

        return [Ident(ref) if isinstance(ref, str) else ref for ref in refs]

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

        root = Node(p())
        ast = AST(root)
        return ast
