from datetime import datetime
from pathlib import Path

from .service import Service

# Something to put in the sources file we write just so we can identify theme.
COOKIE = "revalkyr-generated"


class NotCreatedByUsError(RuntimeError):
    """
    Raised when an operation is attempted on a file not created by this system.
    """

    pass


class OutOfSourceDirectoryError(RuntimeError):
    """
    Raised when an operation is attempted on a file outside the allowed source
    directory.
    """

    pass


class SourceFileMgr(Service):
    def is_revalkyr_file(self, file: Path) -> bool:
        self._check_permitted(file)
        if not file.exists():
            return False
        with file.open("r", encoding="utf-8") as f:
            return f.readline().startswith(f"// {COOKIE} ")

    def get_files(self, pattern: str) -> Path:
        return self.ctx.config.src_dir.rglob(pattern)

    def delete_file(self, file: Path) -> bool:
        self._check_permitted(file)

        if not file.exists():
            return False

        if not self.is_revalkyr_file(file):
            raise NotCreatedByUsError(
                "Operation aborted: The file was not created by Revalkyr"
            )

        file.unlink()
        self.log.debug(f"Deleted {file}")

        return True

    def read_file(self, file: Path) -> str:
        self._check_permitted(file)

        if not file.exists():
            raise FileNotFoundError(f"File not found: {file}")

        content = file.read_text(encoding="utf-8")
        return self._without_cookie(content)

    def write_file(self, file: Path, content: str, overwrite: bool = False) -> None:
        self._check_permitted(file)

        if file.exists():
            if not self.is_revalkyr_file(file):
                raise NotCreatedByUsError()

            if not overwrite:
                raise FileExistsError(
                    f"Operation aborted: The specified file already exists and overwrite flag is not set"
                )

        file.parent.mkdir(parents=True, exist_ok=True)

        file.write_text(self._with_cookie(content), encoding="utf-8")
        self.log.debug(f"Wrote {file} ({len(content)} chars)")

    def _check_permitted(self, file: Path) -> None:
        if not self._is_file_in_src_dir(file):
            raise OutOfSourceDirectoryError(
                f"Operation aborted: The specified file is not in the source file path"
            )

    def _is_file_in_src_dir(self, file: Path) -> bool:
        src_dir = self.ctx.config.src_dir.resolve()
        return str(file.resolve()).startswith(str(src_dir))

    def _with_cookie(self, content: str) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"// {COOKIE} {timestamp}\n" + content

    def _without_cookie(self, content: str) -> str:
        if content.startswith(f"// {COOKIE} "):
            return "\n".join(content.splitlines()[1:])
        return content
