#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def shell(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def latest_ref(repo: str, ref: str) -> str:
    out = shell(["git", "ls-remote", repo, ref])
    return out.splitlines()[0].split()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or bump pinned cpp26 toolchain refs")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--bump", action="store_true")
    args = parser.parse_args()

    if args.check == args.bump:
        print("Use exactly one of --check or --bump", file=sys.stderr)
        return 1

    if args.manifest:
        manifest_path = Path(args.manifest)
    else:
        manifest_path = Path(__file__).resolve().parent.parent / "tool-version-manifest.json"

    manifest = json.loads(manifest_path.read_text())
    image_config = manifest["cpp26_dev_images"]

    latest_clang = latest_ref(image_config["clang_p2996_repo"], "refs/heads/p2996")
    latest_gcc = latest_ref(image_config["gcc_reflection_repo"], "refs/heads/reflection")

    print(f"clang_p2996_ref current={image_config['clang_p2996_ref']} latest={latest_clang}")
    print(f"gcc_reflection_ref current={image_config['gcc_reflection_ref']} latest={latest_gcc}")

    if args.check:
        if (
            image_config["clang_p2996_ref"] == latest_clang
            and image_config["gcc_reflection_ref"] == latest_gcc
        ):
            print("Pins are up to date")
            return 0
        print("Pins are stale")
        return 2

    image_config["clang_p2996_ref"] = latest_clang
    image_config["gcc_reflection_ref"] = latest_gcc
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")
    print(f"Updated {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
