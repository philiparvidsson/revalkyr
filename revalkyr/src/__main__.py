import argparse
import os
import subprocess
import time
import sys

from pathlib import Path


from . import services

from .config import Config, load_config
from .context import Context
from .plugins import PluginResult
from .services.service_mgr import ServiceMgr


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
            subprocess.run(["npm", "i"], capture_output=True, check=True)
            subprocess.run(["npm", "run", "clean"], capture_output=True, check=True)

        config = load_config("revalkyr.yaml")
        run(config)

        subprocess.run(["npm", "run", "build"], capture_output=True, check=True)
        subprocess.run(["npm", "start"], capture_output=True, check=True)
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
    run(config)

    return 0


def run(config: Config) -> None:
    ctx = Context(config)

    service_mgr = ServiceMgr(ctx, services.__all__)
    service_mgr.init()

    plugins = config.plugins
    while plugins:
        plugins_to_keep = []

        for plugin in plugins:
            plugin.ctx = ctx
            plugin.service_mgr = service_mgr
            if plugin.run() != PluginResult.NOTHING_TO_DO:
                plugins_to_keep.append(plugin)

        plugins = plugins_to_keep
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
