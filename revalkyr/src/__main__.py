import argparse
import os
import subprocess
import time
import sys

from pathlib import Path

from .config import load_config
from .context import Context
from .plugins import autobind

import openai


def parse_args():
    parser = argparse.ArgumentParser(description="Revalkyr 0.1.0")

    parser.add_argument(
        "-c",
        "--config",
        default="revalkyr.yaml",
        help="Specify the configuration file. Default i 'revalkyr.yaml'.",
    )

    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run tests.",
    )

    parser.add_argument(
        "--run-tests-dirty",
        action="store_true",
        help="Run tests without resetting them first.",
    )

    args = parser.parse_args()
    return args


def run_test(test_dir, clean):
    print(f"---- running test {test_dir.name} ---")

    cwd = Path.cwd().resolve()
    os.chdir(str(test_dir.resolve()))
    try:
        if clean:
            subprocess.run(["npm", "i"], capture_output=True)
            subprocess.run(["npm", "run", "clean"], capture_output=True)

        config = load_config("revalkyr.yaml")
        ctx = Context(config)
        plugins = [autobind]

        for plugin in plugins:
            plugin.run(ctx)

        subprocess.run(["npm", "start"], capture_output=True)
    finally:
        os.chdir(str(cwd))


def run_tests(clean):
    successes = []
    failures = []

    test_dirs = Path("../tests").iterdir()
    for test_dir in test_dirs:
        if test_dir.is_dir():
            start = time.time()
            try:
                run_test(test_dir, clean)
                finish = time.time()
                print()
                print(f" ---- {test_dir.name} ok after {finish - start:.1f}s ----")
                print()
                successes.append(test_dir.name)
            except:
                finish = time.time()
                print()
                print(f" ---- {test_dir.name} fail after {finish - start:.1f}s ----")
                print()
                failures.append(test_dir.name)

    print()
    print("ok:", ", ".join(successes))
    print()
    print("failed:", ", ".join(failures))
    print()

    return 0


def main() -> int:
    args = parse_args()
    if args.run_tests or args.run_tests_dirty:
        return run_tests(not args.run_tests_dirty)

    config = load_config(args.config)

    os.chdir(config.root_dir)

    ctx = Context(config)
    plugins = [autobind]

    for plugin in plugins:
        plugin.run(ctx)

    return 0


if __name__ == "__main__":
    sys.exit(main())
