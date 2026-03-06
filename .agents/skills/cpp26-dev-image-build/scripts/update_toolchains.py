#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path


def shell(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def read_value(content: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*\"?([^\n\"]+)\"?\s*$", content, re.MULTILINE)
    if not match:
        raise ValueError(f"missing key: {key}")
    return match.group(1)


def replace_value(content: str, key: str, value: str) -> str:
    return re.sub(
        rf"^({re.escape(key)}:\s*)\"?([^\n\"]+)\"?\s*$",
        rf'\1"{value}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )


def latest_ref(repo: str, ref: str) -> str:
    out = shell(["git", "ls-remote", repo, ref])
    first = out.splitlines()[0].split()[0]
    return first


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or bump pinned toolchain refs")
    parser.add_argument("--lock-file", default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bump", action="store_true")
    args = parser.parse_args()

    if args.check == args.bump:
        print("Use exactly one of --check or --bump", file=sys.stderr)
        return 1

    if args.lock_file:
        lock_path = Path(args.lock_file)
    else:
        lock_path = Path(__file__).resolve().parent.parent / "references" / "toolchain-lock.yaml"

    content = lock_path.read_text()
    clang_repo = read_value(content, "clang_repo")
    gcc_repo = read_value(content, "gcc_repo")
    current_clang = read_value(content, "clang_ref")
    current_gcc = read_value(content, "gcc_ref")

    latest_clang = latest_ref(clang_repo, "refs/heads/p2996")
    latest_gcc = latest_ref(gcc_repo, "refs/heads/reflection")

    print(f"clang_ref current={current_clang} latest={latest_clang}")
    print(f"gcc_ref   current={current_gcc} latest={latest_gcc}")

    if args.check:
        if current_clang == latest_clang and current_gcc == latest_gcc:
            print("Pins are up to date")
            return 0
        print("Pins are stale")
        return 2

    updated = content
    updated = replace_value(updated, "clang_ref", latest_clang)
    updated = replace_value(updated, "gcc_ref", latest_gcc)
    lock_path.write_text(updated)
    print(f"Updated {lock_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
