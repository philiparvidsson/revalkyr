import hashlib

from pathlib import Path


class FileWatcher:
    def __init__(self, path: Path | str, pattern: str = "*"):
        if isinstance(path, str):
            path = Path(path)

        self.path = path
        self.pattern = pattern

        self._files: dict[str, str] = dict()

    def any_files_changed(self) -> bool:
        files: dict[str, str] = dict()

        for file in self.path.rglob(self.pattern):
            if file.is_file():
                files[file.resolve()] = self._hash_file(file)

        # Compare both ways to catch all changes.

        try:
            for filename, hash in files.items():
                other_hash = self._files.get(filename)
                if hash != other_hash:
                    return True

            for filename, hash in self._files.items():
                other_hash = files.get(filename)
                if hash != other_hash:
                    return True
        finally:
            self._files = files

        return False

    def _hash_file(self, file: Path) -> str:
        hash_func = hashlib.sha256()
        with file.open("rb") as f:
            # Read 1MB chunks.
            for chunk in iter(lambda: f.read(1048576), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
