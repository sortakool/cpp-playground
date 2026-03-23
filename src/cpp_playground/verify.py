from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "verification" / "verification.toml"


def load_manifest() -> list[dict[str, Any]]:
    data = tomllib.loads(MANIFEST_PATH.read_text())
    return list(data.get("suite", []))


def suite_index() -> dict[str, dict[str, Any]]:
    return {entry["name"]: entry for entry in load_manifest()}


def run_shell(command: str, *, cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        executable="/bin/sh",
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{proc.stdout}{proc.stderr}".strip()
    return proc.returncode, output


def missing_commands(required: list[str]) -> list[str]:
    return [name for name in required if shutil.which(name) is None]


def run_suite(entry: dict[str, Any]) -> dict[str, Any]:
    required = list(entry.get("requires_commands", []))
    missing = missing_commands(required)
    if missing:
        return {
            "name": entry["name"],
            "status": "skipped",
            "reason": f"missing commands: {', '.join(missing)}",
            "steps": [],
        }

    cwd = REPO_ROOT / entry.get("cwd", ".")
    steps: list[dict[str, Any]] = []
    for command in entry.get("commands", []):
        code, output = run_shell(command, cwd=cwd)
        steps.append({"command": command, "exit_code": code, "output": output})
        if code != 0:
            return {
                "name": entry["name"],
                "status": "failed",
                "reason": output or f"step failed with exit code {code}",
                "steps": steps,
            }

    return {
        "name": entry["name"],
        "status": "passed",
        "reason": "",
        "steps": steps,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Run declarative cpp-playground verification suites."
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Execute verification suites.")
    run_parser.add_argument("--all", action="store_true", help="Run every suite in the manifest.")
    run_parser.add_argument(
        "--suite",
        action="append",
        default=[],
        help="Run a specific suite by name. Can be repeated.",
    )
    run_parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return root


def selected_suites(args: argparse.Namespace) -> list[dict[str, Any]]:
    suites = suite_index()
    if args.all or not args.suite:
        return list(suites.values())
    if args.suite:
        missing = [name for name in args.suite if name not in suites]
        if missing:
            raise SystemExit(f"unknown suite(s): {', '.join(missing)}")
        return [suites[name] for name in args.suite]
    raise SystemExit("failed to resolve verification suites")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command != "run":
        raise SystemExit(f"unsupported command: {args.command}")

    results = [run_suite(entry) for entry in selected_suites(args)]
    summary = {
        "repo_root": str(REPO_ROOT),
        "results": results,
        "passed": sum(result["status"] == "passed" for result in results),
        "failed": sum(result["status"] == "failed" for result in results),
        "skipped": sum(result["status"] == "skipped" for result in results),
    }

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        for result in results:
            line = f"{result['status'].upper():7} {result['name']}"
            if result["reason"]:
                line = f"{line} :: {result['reason']}"
            print(line)
        print(f"summary: passed={summary['passed']}", end=" ")
        print(f"failed={summary['failed']} skipped={summary['skipped']}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
