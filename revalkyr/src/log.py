from rich import print


class Log:
    def debug(self, *args: tuple[any, ...]) -> None:
        print(f"[magenta]{' '.join(map(str, args))}[/magenta]")

    def good(self, *args: tuple[any, ...]) -> None:
        print(f"[green]{' '.join(map(str, args))}[/green]")

    def info(self, *args: tuple[any, ...]) -> None:
        print(f"[white]{' '.join(map(str, args))}[/white]")

    def warn(self, *args: tuple[any, ...]) -> None:
        print(f"[yellow]{' '.join(map(str, args))}[/yellow]")

    def error(self, *args: tuple[any, ...]) -> None:
        print(f"[red]{' '.join(map(str, args))}[/red]")
