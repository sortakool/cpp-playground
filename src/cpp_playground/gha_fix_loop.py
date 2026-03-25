from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any

from .common import CppPlaygroundError, print_json, run


def run_json(args: list[str], cwd: Path) -> Any:
    return json.loads(run(args, cwd=cwd).stdout)


def iso_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def parse_inputs(items: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for item in items:
        if "=" not in item:
            raise CppPlaygroundError(f"invalid --input value {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        parsed.append((key, value))
    return parsed


def get_repo_slug(cwd: Path) -> str:
    payload = run_json(["gh", "repo", "view", "--json", "nameWithOwner"], cwd)
    return payload["nameWithOwner"]


def workflow_run_list(cwd: Path, workflow: str, limit: int) -> list[dict[str, Any]]:
    return run_json(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            workflow,
            "--limit",
            str(limit),
            "--json",
            "databaseId,workflowName,status,conclusion,url,createdAt,updatedAt,headBranch,headSha,event,name",
        ],
        cwd,
    )


def dispatch_workflow(cwd: Path, workflow: str, ref: str | None, items: list[str]) -> None:
    args = ["gh", "workflow", "run", workflow]
    if ref:
        args.extend(["--ref", ref])
    for key, value in parse_inputs(items):
        args.extend(["-f", f"{key}={value}"])
    run(args, cwd=cwd)


def locate_dispatched_run(
    cwd: Path,
    workflow: str,
    after: dt.datetime,
    ref: str | None,
    *,
    limit: int,
    timeout_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        runs = workflow_run_list(cwd, workflow, limit)
        matches: list[dict[str, Any]] = []
        for workflow_run in runs:
            created_at = dt.datetime.fromisoformat(workflow_run["createdAt"].replace("Z", "+00:00"))
            if created_at < after:
                continue
            if ref and workflow_run.get("headBranch") and workflow_run["headBranch"] != ref:
                continue
            matches.append(workflow_run)
        if matches:
            matches.sort(key=lambda item: item["createdAt"], reverse=True)
            return matches[0]
        time.sleep(poll_seconds)
    raise CppPlaygroundError("timed out waiting for dispatched workflow run to appear")


def get_run(cwd: Path, run_id: int) -> dict[str, Any]:
    return run_json(
        [
            "gh",
            "run",
            "view",
            str(run_id),
            "--json",
            "databaseId,name,workflowName,status,conclusion,url,headBranch,headSha,event,createdAt,updatedAt",
        ],
        cwd,
    )


def get_jobs(cwd: Path, repo_slug: str, run_id: int) -> list[dict[str, Any]]:
    payload = run_json(
        ["gh", "api", f"repos/{repo_slug}/actions/runs/{run_id}/jobs?per_page=100"],
        cwd,
    )
    return list(payload.get("jobs", []))


def summarize_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for job in jobs:
        if job.get("conclusion") in {"success", "skipped"}:
            continue
        steps = []
        for step in job.get("steps", []) or []:
            if step.get("conclusion") in {None, "success", "skipped"}:
                continue
            steps.append(
                {
                    "name": step.get("name"),
                    "number": step.get("number"),
                    "conclusion": step.get("conclusion"),
                }
            )
        summary.append(
            {
                "name": job.get("name"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
                "html_url": job.get("html_url"),
                "steps": steps,
            }
        )
    return summary


def print_human_summary(run_summary: dict[str, Any], failing_jobs: list[dict[str, Any]]) -> None:
    print(f"workflow: {run_summary.get('workflowName') or run_summary.get('name')}")
    print(f"run_id: {run_summary['databaseId']}")
    print(f"status: {run_summary['status']}")
    print(f"conclusion: {run_summary.get('conclusion')}")
    print(f"url: {run_summary['url']}")
    print(f"head_branch: {run_summary.get('headBranch')}")
    print(f"head_sha: {run_summary.get('headSha')}")
    if not failing_jobs:
        return
    print("failing_jobs:")
    for job in failing_jobs:
        print(f"  - {job['name']} [{job['conclusion']}] {job['html_url']}")
        for step in job["steps"]:
            print(f"    step {step['number']}: {step['name']} [{step['conclusion']}]")


def workflow_run(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path(args.repo).resolve()
    if not cwd.exists():
        raise CppPlaygroundError(f"repo path not found: {cwd}")

    if args.dry_run:
        mode = "attach" if args.run_id else "trigger" if args.trigger else "latest"
        return {
            "mode": mode,
            "repo": str(cwd),
            "workflow": args.workflow,
            "ref": args.ref,
            "run_id": args.run_id,
            "requested_inputs": dict(parse_inputs(args.input)) if args.input else {},
            "poll_seconds": args.poll_seconds,
            "timeout_minutes": args.timeout_minutes,
            "max_runs_scan": args.max_runs_scan,
        }

    if args.trigger:
        dispatch_started_at = iso_now()
        dispatch_workflow(cwd, args.workflow, args.ref, args.input)
        run_summary = locate_dispatched_run(
            cwd,
            args.workflow,
            dispatch_started_at,
            args.ref,
            limit=args.max_runs_scan,
            timeout_seconds=args.timeout_minutes * 60,
            poll_seconds=args.poll_seconds,
        )
    elif args.run_id:
        run_summary = get_run(cwd, args.run_id)
    else:
        recent = workflow_run_list(cwd, args.workflow, args.max_runs_scan)
        if not recent:
            raise CppPlaygroundError(f"no runs found for workflow {args.workflow!r}")
        run_summary = recent[0]

    deadline = time.time() + (args.timeout_minutes * 60)
    while time.time() < deadline:
        if run_summary["status"] == "completed":
            break
        time.sleep(args.poll_seconds)
        run_summary = get_run(cwd, int(run_summary["databaseId"]))

    if run_summary["status"] != "completed":
        raise CppPlaygroundError("timed out waiting for workflow completion")

    repo_slug = get_repo_slug(cwd)
    failing_jobs = summarize_jobs(get_jobs(cwd, repo_slug, int(run_summary["databaseId"])))
    return {
        "repo": repo_slug,
        "workflow": run_summary.get("workflowName") or run_summary.get("name"),
        "run": run_summary,
        "failing_jobs": failing_jobs,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="GitHub Actions fix-loop helpers.")
    subparsers = root.add_subparsers(dest="command", required=True)

    workflow_parser = subparsers.add_parser(
        "workflow-run",
        help="Dispatch or attach to a GitHub Actions workflow run and poll until completion.",
    )
    workflow_parser.add_argument("--repo", default=".")
    workflow_parser.add_argument("--workflow")
    workflow_parser.add_argument("--ref")
    workflow_parser.add_argument("--input", action="append", default=[], metavar="KEY=VALUE")
    workflow_parser.add_argument("--trigger", action="store_true")
    workflow_parser.add_argument("--run-id", type=int)
    workflow_parser.add_argument("--poll-seconds", type=int, default=15)
    workflow_parser.add_argument("--timeout-minutes", type=int, default=120)
    workflow_parser.add_argument("--max-runs-scan", type=int, default=20)
    workflow_parser.add_argument("--json", action="store_true")
    workflow_parser.add_argument("--dry-run", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.run_id and not args.workflow:
        raise SystemExit("--workflow is required unless --run-id is supplied")
    if args.trigger and args.run_id:
        raise SystemExit("--trigger and --run-id are mutually exclusive")
    result = workflow_run(args)
    if args.json:
        print_json(result)
    else:
        if args.dry_run:
            print("dry-run: no gh commands executed")
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_human_summary(result["run"], result["failing_jobs"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
