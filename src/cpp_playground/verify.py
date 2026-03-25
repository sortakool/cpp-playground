from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .common import (
    CppPlaygroundError,
    print_json,
    read_json,
    read_toml,
    repo_root,
    run,
    shutil_which,
)

REPO_ROOT = repo_root()
MANIFEST_PATH = REPO_ROOT / "verification" / "verification.toml"

SuiteHandler = Callable[[dict[str, Any]], dict[str, Any]]


class VerificationFailure(CppPlaygroundError):
    """Raised when a verification suite fails."""


def fail(message: str) -> None:
    raise VerificationFailure(message)


def tracked_files() -> list[Path]:
    output = run(["git", "ls-files"]).stdout.splitlines()
    paths = [REPO_ROOT / line for line in output if line.strip()]
    return [path for path in paths if path.exists()]


def relative_tracked_files() -> list[str]:
    return [path.relative_to(REPO_ROOT).as_posix() for path in tracked_files()]


def load_manifest() -> list[dict[str, Any]]:
    data = read_toml(MANIFEST_PATH)
    return list(data.get("suite", []))


def suite_index() -> dict[str, dict[str, Any]]:
    return {entry["name"]: entry for entry in load_manifest()}


def live_text_files() -> list[Path]:
    files: list[Path] = []
    roots = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "pixi.toml",
        REPO_ROOT / "mise.toml",
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "docker-bake.hcl",
        REPO_ROOT / ".devcontainer" / "devcontainer.json",
    ]
    files.extend(path for path in roots if path.exists())
    scan_roots = [
        REPO_ROOT / "docs",
        REPO_ROOT / ".agents" / "skills",
        REPO_ROOT / ".github" / "workflows",
    ]
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            path_str = path.as_posix()
            if not path.is_file():
                continue
            if any(
                marker in path_str
                for marker in (
                    "docs/archive/",
                    "docs/agent-runs/",
                    "docs/plan-reviews/",
                )
            ):
                continue
            files.append(path)
    return sorted(set(files))


def require_tokens(text: str, tokens: list[str], *, label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        fail(f"{label} missing token(s): {', '.join(missing)}")


def forbid_tokens(text: str, tokens: list[str], *, label: str) -> None:
    present = [token for token in tokens if token in text]
    if present:
        fail(f"{label} still contains forbidden token(s): {', '.join(present)}")


def handle_cleanup_one_dockerfile(_entry: dict[str, Any]) -> dict[str, Any]:
    dockerfiles = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in REPO_ROOT.rglob("Dockerfile*")
        if path.is_file() and ".git/" not in path.as_posix()
    )
    expected = [".devcontainer/Dockerfile.host-user", "Dockerfile"]
    if dockerfiles != expected:
        fail(f"unexpected Dockerfile surface: {dockerfiles}")
    return {"dockerfiles": dockerfiles}


def handle_image_stage_names_exact(_entry: dict[str, Any]) -> dict[str, Any]:
    lines = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    stages = [
        line.split(" AS ", 1)[1].strip()
        for line in lines
        if line.startswith("FROM ") and " AS " in line
    ]
    expected = ["base", "clang", "gcc", "final", "devcontainer"]
    if stages != expected:
        fail(f"unexpected stage order: {stages}")
    return {"stages": stages}


def handle_image_bake_targets(_entry: dict[str, Any]) -> dict[str, Any]:
    text = (REPO_ROOT / "docker-bake.hcl").read_text(encoding="utf-8")
    require_tokens(
        text,
        [
            'dockerfile = "Dockerfile"',
            'target "base"',
            'target "clang"',
            'target "gcc"',
            'target "final"',
            'target "devcontainer"',
            'group "toolchains"',
            'group "default"',
        ],
        label="docker-bake.hcl",
    )
    return {"status": "ok"}


def handle_image_bake_print_devcontainer(_entry: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(
        run(["docker", "buildx", "bake", "-f", "docker-bake.hcl", "--print", "devcontainer"]).stdout
    )
    target = payload["target"]["devcontainer"]
    if target.get("dockerfile") != "Dockerfile":
        fail(f"unexpected dockerfile: {target.get('dockerfile')}")
    if target.get("context") != ".":
        fail(f"unexpected context: {target.get('context')}")
    return {"dockerfile": target["dockerfile"], "context": target["context"]}


def handle_image_final_bootstrap_boundary(_entry: dict[str, Any]) -> dict[str, Any]:
    text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    final_segment = text.split("FROM base AS final", 1)[1]
    require_tokens(
        final_segment,
        [
            "COPY .chezmoiversion",
            "COPY docker-bake.hcl",
            "COPY home /opt/cpp-playground/home",
            "COPY mise.lock /opt/cpp-playground/mise.lock",
            "COPY src/cpp_playground /opt/cpp-playground/src/cpp_playground",
            "RUN chmod +x /opt/cpp-playground/install.sh && \\",
            "COPY . /opt/cpp-playground",
        ],
        label="final stage",
    )
    first_copy = final_segment.index("COPY .chezmoiversion")
    full_copy = final_segment.index("COPY . /opt/cpp-playground")
    if not first_copy < full_copy:
        fail("full repo copy must happen after bootstrap inputs")
    return {"status": "ok"}


def handle_bootstrap_install_entrypoint(_entry: dict[str, Any]) -> dict[str, Any]:
    text = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
    require_tokens(
        text,
        [
            "CPP_PLAYGROUND_REPO_ROOT=$script_dir",
            "home/.chezmoitemplates/mise-bootstrap.sh.tmpl",
            "mise install --locked",
            "mise reshim",
            "uv sync --locked --group dev",
            ".venv/bin/cpp-playground bootstrap install-dotfiles",
        ],
        label="install.sh",
    )
    forbid_tokens(
        text,
        ["read ", "sudo ", "python3 -m cpp_playground", "mise exec -- python"],
        label="install.sh",
    )
    return {"status": "ok"}


def handle_cli_console_scripts(_entry: dict[str, Any]) -> dict[str, Any]:
    scripts = read_toml(REPO_ROOT / "pyproject.toml")["project"]["scripts"]
    if "cpp-playground" not in scripts:
        fail("pyproject.toml is missing the cpp-playground console script")
    if scripts["cpp-playground"] != "cpp_playground.cli:main":
        fail(f"unexpected cpp-playground entrypoint: {scripts['cpp-playground']}")
    return {"scripts": sorted(scripts)}


def handle_devcontainer_surface(_entry: dict[str, Any]) -> dict[str, Any]:
    config = read_json(REPO_ROOT / ".devcontainer" / "devcontainer.json")
    runtime_helper = (REPO_ROOT / "src" / "cpp_playground" / "devcontainer.py").read_text(
        encoding="utf-8"
    )
    initialize = config.get("initializeCommand", "")
    post_create = config.get("postCreateCommand", "")
    post_start = config.get("postStartCommand", "")
    require_tokens(
        initialize,
        [
            "uv sync --locked --group dev",
            "uv run cpp-playground devcontainer initialize-host",
        ],
        label="initializeCommand",
    )
    require_tokens(
        post_create,
        [
            "uv sync --locked --group dev",
            "uv run cpp-playground devcontainer post-create",
        ],
        label="postCreateCommand",
    )
    require_tokens(
        post_start,
        [
            "uv sync --locked --group dev",
            "uv run cpp-playground devcontainer ensure-ssh",
        ],
        label="postStartCommand",
    )
    mounts = config.get("mounts", [])
    required_mount = (
        "type=bind,source=${localEnv:HOME}/.local/state/cpp-playground,"
        "target=/tmp/cpp-playground-host-state"
    )
    if required_mount not in mounts:
        fail("missing host state bind mount")
    run_args = config.get("runArgs", [])
    if "--platform=linux/amd64" not in run_args:
        fail("missing linux/amd64 runArg")
    container_env = config.get("containerEnv", {})
    expected_project_env = "/home/${localEnv:USER}/.local/share/cpp-playground/.venv"
    if container_env.get("UV_PROJECT_ENVIRONMENT") != expected_project_env:
        fail(f"unexpected UV_PROJECT_ENVIRONMENT: {container_env.get('UV_PROJECT_ENVIRONMENT')}")
    remote_env = config.get("remoteEnv", {})
    if remote_env.get("SSH_AUTH_SOCK") != "/tmp/cpp-playground-ssh-agent.sock":
        fail(f"unexpected remote SSH_AUTH_SOCK: {remote_env.get('SSH_AUTH_SOCK')}")
    remote_path = remote_env.get("PATH", "")
    if "${containerEnv:UV_PROJECT_ENVIRONMENT}/bin" not in remote_path:
        fail("remote PATH must include the container-local UV project environment")
    require_tokens(
        runtime_helper,
        [
            'DEVCONTAINER_OVERRIDE_ENV_PATH = repo_root() / ".devcontainer" / "devcontainer.env"',
            "DEVCONTAINER_DEFAULT_SSH_PORT = 3333",
            'DEVCONTAINER_USER_ENV_VAR = "CPP_PLAYGROUND_DEVCONTAINER_USER"',
            'DEVCONTAINER_SSH_PORT_ENV_VAR = "CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT"',
            'DEVCONTAINER_WORKSPACE_LABEL = "cpp-playground.devcontainer.workspace"',
            'f"{DEVCONTAINER_NAME_PREFIX}-{devcontainer_user}-{ssh_port}"',
            'HOST_DEVCONTAINER_RUNTIME_CONFIG_DIR = "devcontainer-runtime-{port}"',
            "devcontainer-metadata-{port}.json",
            "--config",
            "--id-label",
            "validate_host_ssh_target",
            "remove_repo_devcontainer_instances",
            "ssh_port_source",
        ],
        label="devcontainer.py",
    )
    return {"status": "ok"}


def handle_policy_codex_config_surface(_entry: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        ".codex/config.toml",
        ".codex/agents/docs_researcher.toml",
        ".codex/agents/explorer.toml",
        ".codex/agents/monitor.toml",
        ".codex/agents/reviewer.toml",
        ".codex/agents/worker.toml",
    }
    actual = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / ".codex").rglob("*")
        if path.is_file()
    }
    if actual != allowed:
        fail(f".codex contains non-config files: {sorted(actual - allowed)}")
    return {"paths": sorted(actual)}


def handle_policy_no_shell_automation(_entry: dict[str, Any]) -> dict[str, Any]:
    archived_prefixes = ("docs/archive/", "docs/agent-runs/", "docs/plan-reviews/")
    shell_paths = sorted(
        path
        for path in relative_tracked_files()
        if (path.endswith(".sh") or path.endswith(".bash"))
        and not path.startswith(archived_prefixes)
    )
    if shell_paths != ["install.sh"]:
        fail(f"tracked shell automation must be limited to install.sh, found: {shell_paths}")
    return {"shell_paths": shell_paths}


def handle_policy_no_executable_helpers(_entry: dict[str, Any]) -> dict[str, Any]:
    forbidden_prefixes = [
        ".agents/skills/",
        ".devcontainer/",
        "scripts/",
        ".codex/scripts/",
    ]
    executable_suffixes = {
        ".bash",
        ".fish",
        ".js",
        ".mjs",
        ".cjs",
        ".py",
        ".rb",
        ".sh",
        ".ts",
        ".zsh",
    }
    offenders = []
    for relative_path in relative_tracked_files():
        path = REPO_ROOT / relative_path
        if relative_path == "install.sh":
            continue
        if relative_path.startswith("src/cpp_playground/"):
            continue
        if any(relative_path.startswith(prefix) for prefix in forbidden_prefixes):
            if (
                "/references/" in relative_path
                or "/assets/" in relative_path
                or relative_path.endswith(".json")
                or relative_path.endswith(".lock")
                or relative_path.endswith(".md")
                or relative_path.endswith(".pkl")
                or relative_path.endswith(".toml")
                or relative_path.endswith(".yaml")
                or relative_path.endswith(".yml")
            ):
                continue
            if "/agents/" in relative_path:
                continue
            if path.name.startswith("Dockerfile"):
                continue
            if (
                "/scripts/" in relative_path
                or path.suffix in executable_suffixes
                or path.stat().st_mode & 0o111
            ):
                offenders.append(relative_path)
    if offenders:
        fail(
            f"repo-owned executable helpers remain outside src/cpp_playground: {sorted(offenders)}"
        )
    return {"status": "ok"}


def handle_hooks_hk_only(_entry: dict[str, Any]) -> dict[str, Any]:
    pixi_text = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    forbid_tokens(pixi_text, ["pre-commit", "lefthook"], label="pixi.toml")
    mise_text = (REPO_ROOT / "mise.toml").read_text(encoding="utf-8")
    require_tokens(mise_text, ['hk = "', 'pkl = "'], label="mise.toml")
    hook_config = REPO_ROOT / "hk.pkl"
    if not hook_config.exists():
        fail("missing hk.pkl")
    hook_text = hook_config.read_text(encoding="utf-8")
    require_tokens(
        hook_text,
        ['"pre-commit"', '"pre-push"', "uv run cpp-playground verify run"],
        label="hk.pkl",
    )
    return {"status": "ok"}


def handle_docs_live_surface(_entry: dict[str, Any]) -> dict[str, Any]:
    forbidden = [
        ".codex/multi-agent",
        ".codex/skills",
        ".devcontainer/initialize-host.sh",
        ".devcontainer/ssh_agent_proxy.py",
        "scripts/benchmark-devcontainer-build.sh",
        "scripts/report-devcontainer-size.sh",
        "scripts/smoke-devcontainer-image.sh",
        "select-perspectives.sh",
        "gha_workflow_run.py",
        "sync_agents_learnings.sh",
        "collect_thread_telemetry.sh",
        "ma_dev_image_gate.sh",
        "strict_multi_agent_gate.sh",
        "python3 -m cpp_playground",
        "python -m cpp_playground",
    ]
    offenders: dict[str, list[str]] = {}
    for path in live_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        present = [token for token in forbidden if token in text]
        if present:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = present
    if offenders:
        fail(f"live docs/config still reference deprecated surfaces: {offenders}")
    return {"checked_files": len(live_text_files())}


def handle_docs_canonical_plan(_entry: dict[str, Any]) -> dict[str, Any]:
    canonical = REPO_ROOT / "docs" / "plans" / "2026-03-24-canonical-merged-plan.md"
    if not canonical.exists():
        fail("missing canonical merged plan")
    archive_roots = [
        REPO_ROOT / "docs" / "archive" / "plans",
        REPO_ROOT / "docs" / "archive" / "spec",
        REPO_ROOT / "docs" / "plan-reviews",
        REPO_ROOT / "docs" / "agent-runs",
    ]
    missing = [
        path.relative_to(REPO_ROOT).as_posix() for path in archive_roots if not path.exists()
    ]
    if missing:
        fail(f"missing archive root(s): {missing}")
    return {"canonical_plan": canonical.relative_to(REPO_ROOT).as_posix()}


def handle_workflow_hosted_candidate_flow(_entry: dict[str, Any]) -> dict[str, Any]:
    text = (REPO_ROOT / ".github" / "workflows" / "devcontainer-build-hosted.yml").read_text(
        encoding="utf-8"
    )
    require_tokens(
        text,
        [
            "contract-preflight:",
            "uv run cpp-playground image publish-plan",
            "authoritative-published-image:",
            "candidate_tag",
            "docker buildx bake -f docker-bake.hcl base",
            "--set base.tags=",
            "docker buildx bake -f docker-bake.hcl clang",
            "--set clang.tags=",
            "docker buildx bake -f docker-bake.hcl gcc",
            "--set gcc.tags=",
            "uv run cpp-playground image promote",
        ],
        label="devcontainer-build-hosted.yml",
    )
    forbid_tokens(
        text,
        [
            "./scripts/smoke-devcontainer-image.sh",
            "devcontainer-load",
            "Load hosted devcontainer image for structural smoke",
            "Publish devcontainer image",
        ],
        label="devcontainer-build-hosted.yml",
    )
    return {"status": "ok"}


def handle_workflow_pr_source_build_proof(_entry: dict[str, Any]) -> dict[str, Any]:
    text = (REPO_ROOT / ".github" / "workflows" / "devcontainer-authoritative-smoke.yml").read_text(
        encoding="utf-8"
    )
    require_tokens(
        text,
        [
            "self-hosted",
            "latest-kernel",
            "docker buildx bake -f docker-bake.hcl devcontainer --load",
            "uv run cpp-playground image smoke",
            "uv run cpp-playground verify run",
        ],
        label="devcontainer-authoritative-smoke.yml",
    )
    forbid_tokens(
        text,
        ["./scripts/smoke-devcontainer-image.sh"],
        label="devcontainer-authoritative-smoke.yml",
    )
    return {"status": "ok"}


HANDLERS: dict[str, SuiteHandler] = {
    "cleanup_one_dockerfile": handle_cleanup_one_dockerfile,
    "image_stage_names_exact": handle_image_stage_names_exact,
    "image_bake_targets": handle_image_bake_targets,
    "image_bake_print_devcontainer": handle_image_bake_print_devcontainer,
    "image_final_bootstrap_boundary": handle_image_final_bootstrap_boundary,
    "bootstrap_install_entrypoint": handle_bootstrap_install_entrypoint,
    "cli_console_scripts": handle_cli_console_scripts,
    "devcontainer_surface": handle_devcontainer_surface,
    "policy_codex_config_surface": handle_policy_codex_config_surface,
    "policy_no_shell_automation": handle_policy_no_shell_automation,
    "policy_no_executable_helpers": handle_policy_no_executable_helpers,
    "hooks_hk_only": handle_hooks_hk_only,
    "docs_live_surface": handle_docs_live_surface,
    "docs_canonical_plan": handle_docs_canonical_plan,
    "workflow_hosted_candidate_flow": handle_workflow_hosted_candidate_flow,
    "workflow_pr_source_build_proof": handle_workflow_pr_source_build_proof,
}


def missing_commands(required: list[str]) -> list[str]:
    return [name for name in required if not shutil_which(name)]


def run_suite(entry: dict[str, Any]) -> dict[str, Any]:
    required = list(entry.get("requires_commands", []))
    missing = missing_commands(required)
    if missing:
        return {
            "name": entry["name"],
            "status": "skipped",
            "reason": f"missing commands: {', '.join(missing)}",
            "details": {},
        }
    handler_name = entry["handler"]
    if handler_name not in HANDLERS:
        return {
            "name": entry["name"],
            "status": "failed",
            "reason": f"unknown verification handler: {handler_name}",
            "details": {},
        }
    try:
        details = HANDLERS[handler_name](entry)
    except VerificationFailure as exc:
        return {
            "name": entry["name"],
            "status": "failed",
            "reason": str(exc),
            "details": {},
        }
    return {"name": entry["name"], "status": "passed", "reason": "", "details": details}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Run declarative cpp-playground verification suites."
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Execute verification suites.")
    run_parser.add_argument("--all", action="store_true")
    run_parser.add_argument("--suite", action="append", default=[])
    run_parser.add_argument("--json", action="store_true")
    return root


def selected_suites(args: argparse.Namespace) -> list[dict[str, Any]]:
    suites = suite_index()
    if args.all or not args.suite:
        return list(suites.values())
    missing = [name for name in args.suite if name not in suites]
    if missing:
        raise SystemExit(f"unknown suite(s): {', '.join(missing)}")
    return [suites[name] for name in args.suite]


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
        print_json(summary)
    else:
        for result in results:
            line = f"{result['status'].upper():7} {result['name']}"
            if result["reason"]:
                line = f"{line} :: {result['reason']}"
            print(line)
        summary_line = (
            f"summary: passed={summary['passed']} "
            f"failed={summary['failed']} skipped={summary['skipped']}"
        )
        print(summary_line)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
