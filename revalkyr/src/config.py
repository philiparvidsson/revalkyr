import yaml
from pathlib import Path


class Config:
    def __init__(self, root_dir, src_dir):
        self.root_dir = Path(root_dir)
        self.src_dir = Path(src_dir).relative_to(root_dir)


def load_config(filename: str) -> Config:
    s = Path(filename).read_text()
    c = yaml.safe_load(s)

    root_dir = c.get("root_dir", ".")
    src_dir = c.get("src_dir", "./src")
    config = Config(root_dir, src_dir)

    return config
