from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from . import adversarial, bootstrap, devcontainer, gha_fix_loop, image, verify
from .common import CppPlaygroundError

Runner = Callable[[list[str] | None], int]


COMMANDS: dict[str, tuple[str, Runner]] = {
    "bootstrap": ("Bootstrap and host tool installation helpers.", bootstrap.main),
    "devcontainer": ("Devcontainer host and runtime helpers.", devcontainer.main),
    "image": ("Container image validation, reporting, and CI helpers.", image.main),
    "gha-fix-loop": ("GitHub Actions workflow dispatch and polling helpers.", gha_fix_loop.main),
    "adversarial": ("Adversarial helper commands for repo skills.", adversarial.main),
    "verify": ("Declarative repository verification suites.", verify.main),
}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Unified automation CLI for cpp-playground.")
    root.add_argument("group", choices=sorted(COMMANDS), help="Command group to execute.")
    root.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the group.")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    _description, runner = COMMANDS[args.group]
    forwarded = args.args
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    try:
        return runner(forwarded)
    except CppPlaygroundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
