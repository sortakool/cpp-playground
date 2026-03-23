from __future__ import annotations

import argparse
import contextlib
import getpass
import json
import os
import platform
import pwd
import re
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import textwrap
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
MISE_TOML_PATH = REPO_ROOT / "mise.toml"
PIXI_TOML_PATH = REPO_ROOT / "pixi.toml"
PYPROJECT_TOML_PATH = REPO_ROOT / "pyproject.toml"
CHEZMOI_ROOT_FILE_PATH = REPO_ROOT / ".chezmoiroot"
CHEZMOI_VERSION_FILE_PATH = REPO_ROOT / ".chezmoiversion"
CHEZMOI_SOURCE_ROOT = REPO_ROOT / "home"
CHEZMOI_CONFIG_PATH = CHEZMOI_SOURCE_ROOT / ".chezmoi.toml.tmpl"
CHEZMOI_SCRIPTS_DIR = CHEZMOI_SOURCE_ROOT / ".chezmoiscripts"
DOCKERFILE_PATH = REPO_ROOT / ".devcontainer" / "Dockerfile"
DEVCONTAINER_JSON_PATH = REPO_ROOT / ".devcontainer" / "devcontainer.json"
DOCKER_BAKE_PATH = REPO_ROOT / "docker-bake.hcl"
CMAKE_PRESETS_PATH = REPO_ROOT / "CMakePresets.json"
CPP26_IMAGE_DIR = REPO_ROOT / "tooling" / "cpp26-dev-images"
CPP26_IMAGE_CLANG_DOCKERFILE_PATH = CPP26_IMAGE_DIR / "Dockerfile.clang-p2996"
CPP26_IMAGE_CLANG_QUANTLIB_DOCKERFILE_PATH = CPP26_IMAGE_DIR / "Dockerfile.clang-p2996-quantlib"
CPP26_IMAGE_GCC_DOCKERFILE_PATH = CPP26_IMAGE_DIR / "Dockerfile.gcc-reflection"
OPERATIONAL_SHELL_SCRIPT_DIRS = (
    REPO_ROOT / "scripts",
    REPO_ROOT / "tooling" / "scripts",
    REPO_ROOT / ".devcontainer" / "scripts",
)
DEVCONTAINER_POST_CREATE_COMMAND = "uv run -m tooling post-create"
DEVCONTAINER_POST_START_COMMAND = "uv run -m tooling ensure-devcontainer-ssh"
DEVCONTAINER_SSH_SMOKE_COMMAND = "mise run smoke-ssh-git-gh-parity"
DEVCONTAINER_HOST_SSH_SMOKE_COMMAND = "mise run smoke-ssh-into-devcontainer"
GITHUB_META_API = "https://api.github.com/meta"
DEVCONTAINER_SSH_HOST = "127.0.0.1"
DEVCONTAINER_SSH_PORT = 2222
DEVCONTAINER_SSH_PUBLISH_ARG = f"--publish={DEVCONTAINER_SSH_HOST}:{DEVCONTAINER_SSH_PORT}:22"
DEVCONTAINER_DEFAULT_USER = "devcontainer"
DEVCONTAINER_SSH_KNOWN_HOSTS = (
    f"[localhost]:{DEVCONTAINER_SSH_PORT}",
    f"[{DEVCONTAINER_SSH_HOST}]:{DEVCONTAINER_SSH_PORT}",
)
DEVCONTAINER_SSHD_BIN = "/usr/sbin/sshd"
PLAN_REVIEW_ROOT = REPO_ROOT / ".codex" / "plan-reviews"
CODEX_SKILLS_DIR = REPO_ROOT / ".codex" / "skills"
PROJECT_SKILLS_DIR = REPO_ROOT / ".agents" / "skills"
DEFAULT_PHASE0_PLAN_PATH = (
    REPO_ROOT / "spec" / "2026-03-22-chezmoi-mise-devcontainer-migration-plan.md"
)
PHASE0_DEFAULT_TIMEOUT_SECONDS = 120
DEVCONTAINER_SSHD_DROPIN_PATH = Path("/etc/ssh/sshd_config.d/10-cpp-playground.conf")
DEVCONTAINER_SSH_AUTH_PROFILE_PATH = Path("/etc/profile.d/cpp-playground-ssh-auth-sock.sh")

EXPECTED_PRESETS = {
    "llvm-stable",
    "llvm-asan",
    "llvm-tsan",
    "llvm-msan",
    "gcc-stable",
    "gcc-reflection",
    "clang-p2996",
}

REQUIRED_KERNEL_SOURCES = {
    REPO_ROOT / "tests" / "kernel" / "shared_memory_smoke.cpp",
    REPO_ROOT / "tests" / "kernel" / "epoll_smoke.cpp",
    REPO_ROOT / "tests" / "kernel" / "io_uring_smoke.cpp",
    REPO_ROOT / "tests" / "kernel" / "ebpf_smoke.cpp",
}

REQUIRED_RUNTIME_COMMANDS = {
    "node": ["node", "--version"],
    "mise": ["mise", "--version"],
    "uv": ["uv", "--version"],
    "pixi": ["pixi", "--version"],
    "gh": ["gh", "--version"],
    "codex": ["codex", "--version"],
    "claude": ["claude", "--version"],
    "gemini": ["gemini", "--version"],
    "just": ["just", "--version"],
    "chezmoi": ["chezmoi", "--version"],
    "watchexec": ["watchexec", "--version"],
    "docker": ["docker", "buildx", "version"],
    "iwyu": ["pixi", "run", "-e", "llvm-stable", "include-what-you-use", "--version"],
}

NATIVE_VALIDATION_COMMANDS = {
    "mise_doctor": ["mise", "doctor"],
    "pixi_info": ["pixi", "info"],
    "uv_tool_list": ["uv", "tool", "list"],
    "docker_buildx_inspect": ["docker", "buildx", "inspect"],
}

MISE_NATIVE_TOOL_ALIASES = {
    "node": "node",
    "python": "python",
    "uv": "uv",
    "pixi": "pixi",
    "gh": "gh",
    "codex_cli": "codex",
    "claude_code": "claude-code",
    "gemini_cli": "gemini-cli",
    "just": "just",
    "chezmoi": "chezmoi",
    "watchexec": "watchexec",
}

MISE_GLOBAL_CONFIG_PATH = Path.home() / ".config" / "mise"
FORBIDDEN_REPO_GENERATED_PATHS = (
    Path("README.md"),
    Path("mise.toml"),
    Path("pixi.toml"),
    Path("CMakePresets.json"),
    Path("docker-bake.hcl"),
)
FORBIDDEN_REPO_GENERATED_DIRS = (
    Path(".devcontainer"),
    Path("tooling") / "cpp26-dev-images",
)
CHEZMOI_NON_TARGET_PATH_PREFIXES = (
    ".chezmoiscripts",
    ".chezmoidata",
    ".chezmoitemplates",
)
MISE_PUBLIC_TASKS = {
    "bootstrap": "uv run -m tooling bootstrap",
    "build-cpp26-images": "uv run -m tooling build-cpp26-images --toolchain all --flavor core",
    "build-devcontainer-image": "uv run -m tooling build-devcontainer-image",
    "bump-cpp26-toolchain-pins": "uv run -m tooling bump-cpp26-toolchain-pins",
    "check-cpp26-toolchain-pins": "uv run -m tooling check-cpp26-toolchain-pins",
    "devcontainer-up-macos": "uv run -m tooling devcontainer-up-macos",
    "host-preflight-macos": "uv run -m tooling host-preflight-macos",
    "install-phase0-review-skills": "uv run -m tooling install-phase0-review-skills",
    "refresh": "uv run -m tooling refresh",
    "review-plan-phase0": (
        "uv run -m tooling review-plan-phase0 "
        "spec/2026-03-22-chezmoi-mise-devcontainer-migration-plan.md"
    ),
    "review-plan-phase0-dry-run": (
        "uv run -m tooling review-plan-phase0 "
        "spec/2026-03-22-chezmoi-mise-devcontainer-migration-plan.md --dry-run"
    ),
    "smoke-ssh-git-gh-parity": "uv run -m tooling smoke-ssh-git-gh-parity",
    "smoke-ssh-into-devcontainer": "uv run -m tooling smoke-ssh-into-devcontainer",
    "sync-devcontainer-ssh-known-hosts": "uv run -m tooling sync-devcontainer-ssh-known-hosts",
    "sync-generated": "uv run -m tooling sync-generated",
    "validate-all": "uv run -m tooling validate --mode all",
    "validate-docker-images": "uv run -m tooling validate-docker-images",
    "validate-repo": "uv run -m tooling validate --mode repo",
    "validate-runtime": "uv run -m tooling validate --mode runtime",
    "prove-devcontainer": "uv run -m tooling prove --surface devcontainer",
    "prove-latest-kernel-vm": "uv run -m tooling prove --surface latest-kernel-vm",
    "prove-latest-kernel-ci": "uv run -m tooling prove --surface latest-kernel-ci",
}
PHASE0_SKILL_SPECS: dict[str, dict[str, Any]] = {
    "adversarial-thinking": {
        "repo": "wojons/skills",
        "purpose": "main structured adversarial lens",
        "sections": (
            "When to use me",
            "Adversarial Thinking Framework",
            "When to Use Which Adversarial Perspective",
        ),
    },
    "code-doubter": {
        "repo": "reminiscent-io/wanderluxe",
        "purpose": "anti-overengineering and simplification lens",
        "sections": (
            "How to Review a Plan",
            "How to Deliver Your Review",
            "Tone",
        ),
    },
    "adversarial-committee": {
        "repo": "simhacker/moollm",
        "purpose": "escalation-only arbitration rubric",
        "sections": (
            "The Roster",
            "Debate Protocol",
            "Output Format",
        ),
    },
}
PHASE0_SKILL_NAMES = tuple(PHASE0_SKILL_SPECS)
UPSTREAM_TOOL_SOURCES: dict[str, dict[str, str]] = {
    "node": {"kind": "github_release", "owner": "nodejs", "repo": "node", "tag_prefix": "v"},
    "llvm": {
        "kind": "github_release",
        "owner": "llvm",
        "repo": "llvm-project",
        "tag_prefix": "llvmorg-",
    },
    "gcc": {"kind": "gnu_gcc_latest"},
    "mise": {"kind": "github_release", "owner": "jdx", "repo": "mise", "tag_prefix": "v"},
    "uv": {"kind": "github_release", "owner": "astral-sh", "repo": "uv", "tag_prefix": ""},
    "pixi": {
        "kind": "github_release",
        "owner": "prefix-dev",
        "repo": "pixi",
        "tag_prefix": "v",
    },
    "gh": {"kind": "github_release", "owner": "cli", "repo": "cli", "tag_prefix": "v"},
    "codex_cli": {"kind": "npm", "package": "@openai/codex"},
    "claude_code": {"kind": "npm", "package": "@anthropic-ai/claude-code"},
    "gemini_cli": {"kind": "npm", "package": "@google/gemini-cli"},
    "just": {"kind": "github_release", "owner": "casey", "repo": "just", "tag_prefix": ""},
    "chezmoi": {
        "kind": "github_release",
        "owner": "twpayne",
        "repo": "chezmoi",
        "tag_prefix": "v",
    },
    "watchexec": {
        "kind": "github_release",
        "owner": "watchexec",
        "repo": "watchexec",
        "tag_prefix": "v",
    },
    "ruff": {"kind": "pypi", "package": "ruff"},
    "ty": {"kind": "pypi", "package": "ty"},
    "include_what_you_use": {"kind": "pixi_search", "package": "include-what-you-use"},
}


class ToolingError(RuntimeError):
    """Raised when control-plane actions fail."""


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text())


def extract_json_payload(text: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "\n".join(lines[index:])
    raise ToolingError(f"command output did not contain JSON: {text[:200]!r}")


def run_json(cmd: list[str], *, env: dict[str, str] | None = None) -> Any:
    return json.loads(extract_json_payload(run(cmd, env=env, capture=True, strip=False)))


def extract_bake_variable_default(text: str, name: str) -> str:
    match = re.search(
        rf'^variable "{re.escape(name)}" \{{\n\s+default = "([^"]+)"\n\}}',
        text,
        flags=re.MULTILINE,
    )
    if match is None:
        raise ToolingError(f"docker-bake.hcl is missing variable {name!r}")
    return match.group(1)


def extract_arg_value(text: str, name: str) -> str:
    match = re.search(rf"^ARG {re.escape(name)}=(.+)$", text, flags=re.MULTILINE)
    if match is None:
        raise ToolingError(f"missing ARG {name!r}")
    return match.group(1).strip()


def pyproject_dev_dependency_version(pyproject_data: dict[str, Any], name: str) -> str:
    dependencies = pyproject_data["dependency-groups"]["dev"]
    for dependency in dependencies:
        if dependency.startswith(f"{name}=="):
            return dependency.split("==", maxsplit=1)[1]
    raise ToolingError(f"pyproject.toml is missing dev dependency {name!r}")


def pixi_exact_dependency_version(
    pixi_data: dict[str, Any],
    feature_name: str,
    dependency_name: str,
) -> str:
    dependencies = pixi_data["feature"][feature_name]["target"]["linux-64"]["dependencies"]
    spec = str(dependencies[dependency_name])
    if not spec.startswith("=="):
        raise ToolingError(
            f"pixi dependency {feature_name}.{dependency_name} must be exact; got {spec!r}"
        )
    return spec.removeprefix("==")


def load_manifest() -> dict[str, Any]:
    mise_data = load_toml(MISE_TOML_PATH)
    pixi_data = load_toml(PIXI_TOML_PATH)
    pyproject_data = load_toml(PYPROJECT_TOML_PATH)
    docker_bake_text = DOCKER_BAKE_PATH.read_text()
    dockerfile_text = DOCKERFILE_PATH.read_text()
    clang_dockerfile_text = CPP26_IMAGE_CLANG_DOCKERFILE_PATH.read_text()
    gcc_dockerfile_text = CPP26_IMAGE_GCC_DOCKERFILE_PATH.read_text()

    mise_tools = mise_data["tools"]
    tools = {
        "node": {"version": str(mise_tools["node"])},
        "python": {"version": str(mise_tools["python"])},
        "mise": {
            "version": extract_bake_variable_default(docker_bake_text, "MISE_VERSION").removeprefix(
                "v"
            )
        },
        "uv": {"version": str(mise_tools["uv"])},
        "pixi": {"version": str(mise_tools["pixi"])},
        "gh": {"version": str(mise_tools["gh"])},
        "codex_cli": {"version": str(mise_tools["codex"])},
        "claude_code": {"version": str(mise_tools["claude-code"])},
        "gemini_cli": {"version": str(mise_tools["gemini-cli"])},
        "just": {"version": str(mise_tools["just"])},
        "chezmoi": {"version": str(mise_tools["chezmoi"])},
        "watchexec": {"version": str(mise_tools["watchexec"])},
        "llvm": {
            "version": str(
                pixi_data["feature"]["llvm-stable"]["activation"]["env"]["LLVM_VERSION"]
            )
        },
        "gcc": {"version": pixi_exact_dependency_version(pixi_data, "gcc-stable", "gcc_linux-64")},
        "ruff": {"version": pyproject_dev_dependency_version(pyproject_data, "ruff")},
        "ty": {"version": pyproject_dev_dependency_version(pyproject_data, "ty")},
        "include_what_you_use": {
            "version": pixi_exact_dependency_version(
                pixi_data, "llvm-stable", "include-what-you-use"
            )
        },
    }

    cpp26_image_tag = extract_bake_variable_default(docker_bake_text, "CPP26_IMAGE_TAG")
    return {
        "python_version": str(mise_tools["python"]),
        "channels": {},
        "images": {
            "cpp_devcontainer": {
                "repository": extract_bake_variable_default(docker_bake_text, "IMAGE"),
                "default_tag": extract_bake_variable_default(docker_bake_text, "TAG"),
            },
            "cpp_devcontainer_repo_base": {
                "repository": extract_bake_variable_default(docker_bake_text, "REPO_BASE_IMAGE"),
                "default_tag": cpp26_image_tag,
            },
            "cpp_devcontainer_base": {
                "repository": extract_bake_variable_default(docker_bake_text, "FINAL_BASE_IMAGE"),
                "default_tag": cpp26_image_tag,
            },
            "cpp26_dev_clang": {
                "repository": extract_bake_variable_default(docker_bake_text, "CLANG_IMAGE"),
                "default_tag": cpp26_image_tag,
            },
            "cpp26_dev_gcc": {
                "repository": extract_bake_variable_default(docker_bake_text, "GCC_IMAGE"),
                "default_tag": cpp26_image_tag,
            },
            "cpp26_dev_clang_quantlib": {
                "repository": extract_bake_variable_default(
                    docker_bake_text, "CLANG_QUANTLIB_IMAGE"
                ),
                "default_tag": cpp26_image_tag,
            },
        },
        "cpp26_dev_images": {
            "platform_default": extract_bake_variable_default(docker_bake_text, "PLATFORM"),
            "ubuntu_version": extract_arg_value(dockerfile_text, "UBUNTU_VERSION"),
            "quantlib_version": extract_arg_value(
                CPP26_IMAGE_CLANG_QUANTLIB_DOCKERFILE_PATH.read_text(), "QUANTLIB_VERSION"
            ),
            "vcpkg_bundle_url": extract_arg_value(dockerfile_text, "VCPKG_BUNDLE_URL"),
            "clang_p2996_repo": extract_arg_value(clang_dockerfile_text, "CLANG_P2996_REPO"),
            "clang_p2996_ref": extract_arg_value(clang_dockerfile_text, "CLANG_P2996_REF"),
            "gcc_reflection_repo": extract_arg_value(gcc_dockerfile_text, "GCC_REFLECTION_REPO"),
            "gcc_reflection_ref": extract_arg_value(gcc_dockerfile_text, "GCC_REFLECTION_REF"),
        },
        "tools": tools,
    }


def version_of(manifest: dict[str, Any], name: str) -> str:
    return str(manifest["tools"][name]["version"])


def node_major(manifest: dict[str, Any]) -> str:
    return version_of(manifest, "node").split(".", maxsplit=1)[0]


def llvm_archive_name(manifest: dict[str, Any]) -> str:
    return f"LLVM-{version_of(manifest, 'llvm')}-Linux-X64.tar.xz"


def llvm_download_url(manifest: dict[str, Any]) -> str:
    llvm_version = version_of(manifest, "llvm")
    archive = llvm_archive_name(manifest)
    return (
        f"https://github.com/llvm/llvm-project/releases/download/llvmorg-{llvm_version}/{archive}"
    )


def image_repo(manifest: dict[str, Any], key: str) -> str:
    return str(manifest["images"][key]["repository"])


def image_tag(manifest: dict[str, Any], key: str) -> str:
    return str(manifest["images"][key]["default_tag"])


def image_ref(manifest: dict[str, Any], key: str) -> str:
    return f"{image_repo(manifest, key)}:{image_tag(manifest, key)}"


def cpp26_local_image_refs(manifest: dict[str, Any], image_tag_value: str) -> dict[str, str]:
    return {
        "repo_base": f"{image_repo(manifest, 'cpp_devcontainer_repo_base')}:{image_tag_value}",
        "final_base": f"{image_repo(manifest, 'cpp_devcontainer_base')}:{image_tag_value}",
        "clang": f"{image_repo(manifest, 'cpp26_dev_clang')}:{image_tag_value}",
        "gcc": f"{image_repo(manifest, 'cpp26_dev_gcc')}:{image_tag_value}",
        "quantlib": f"{image_repo(manifest, 'cpp26_dev_clang_quantlib')}:{image_tag_value}",
        "devcontainer": f"{image_repo(manifest, 'cpp_devcontainer')}:{image_tag_value}",
    }


def run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    capture: bool = False,
    strip: bool = True,
    stream: bool = False,
) -> str:
    if capture and stream:
        raise ToolingError("run() cannot capture and stream output at the same time")

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    if stream:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or REPO_ROOT,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        output_chunks: list[str] = []
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="")
            output_chunks.append(line)
        proc.wait()
        output = "".join(output_chunks)
        if proc.returncode != 0:
            raise ToolingError(
                f"command failed ({proc.returncode}): {' '.join(cmd)}\n{output.strip()}"
            )
        if strip:
            return output.strip()
        return output

    proc = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ToolingError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr.strip()}"
        )
    if not capture:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
    if strip:
        return proc.stdout.strip()
    return proc.stdout


def replace_required_line(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ToolingError(f"unable to update {label}: missing pattern {pattern!r}")
    return updated


def replace_quoted_setting(text: str, pattern: str, value: str, label: str) -> str:
    updated, count = re.subn(pattern, rf'\1"{value}"\2', text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ToolingError(f"unable to update {label}: missing pattern {pattern!r}")
    return updated


def ensure_repo_text_absent(token: str) -> None:
    proc = subprocess.run(
        ["rg", "-n", "--hidden", "--glob", "!.git", "-F", token, str(REPO_ROOT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        raise ToolingError(f"repo contains forbidden token {token!r}:\n{proc.stdout.strip()}")
    if proc.returncode > 1:
        raise ToolingError(
            f"failed to scan repo for forbidden token {token!r}: {proc.stderr.strip()}"
        )


@contextlib.contextmanager
def isolated_mise_environment() -> Iterator[dict[str, str]]:
    with TemporaryDirectory(prefix="cpp-playground-mise-") as temp_dir:
        config_dir = Path(temp_dir)
        global_config = config_dir / "config.toml"
        global_config.write_text("")
        yield {
            "MISE_GLOBAL_CONFIG_FILE": str(global_config),
            "MISE_IGNORED_CONFIG_PATHS": str(MISE_GLOBAL_CONFIG_PATH),
        }


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "cpp-playground-tooling/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:  # pragma: no cover - network surface
        raise ToolingError(f"failed to fetch {url}: {exc}") from exc


def current_username() -> str:
    return pwd.getpwuid(os.getuid()).pw_name


def ensure_socket(path_str: str, *, label: str) -> None:
    path = Path(path_str)
    if not path.exists():
        raise ToolingError(f"{label} does not exist: {path}")
    if not stat.S_ISSOCK(path.stat().st_mode):
        raise ToolingError(f"{label} does not point to a socket: {path}")


def ensure_user_access_to_socket(path_str: str, *, actual_user: str, label: str) -> str | None:
    if not path_str:
        return None

    try:
        ensure_socket(path_str, label=label)
    except ToolingError as exc:
        print(f"warning: {exc}")
        return None

    if os.access(path_str, os.R_OK | os.W_OK):
        return path_str

    try:
        run(["sudo", "chgrp", actual_user, path_str])
        run(["sudo", "chmod", "660", path_str])
    except ToolingError as exc:
        print(f"warning: failed to grant {actual_user} access to {label}: {exc}")
        return None

    if os.access(path_str, os.R_OK | os.W_OK):
        return path_str

    print(f"warning: {label} is still not accessible by {actual_user}: {path_str}")
    return None


def ensure_user_ssh_paths() -> tuple[Path, Path]:
    ssh_dir = Path(os.environ.get("HOME", str(Path.home()))) / ".ssh"
    known_hosts_path = ssh_dir / "known_hosts"
    ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    ssh_dir.chmod(0o700)
    return ssh_dir, known_hosts_path


def sudo_install_text(
    path: Path,
    content: str,
    *,
    mode: int,
    owner: str | None = None,
    group: str | None = None,
) -> None:
    with TemporaryDirectory(prefix="cpp-playground-install-") as temp_dir:
        temp_path = Path(temp_dir) / path.name
        temp_path.write_text(content)
        run(["sudo", "install", "-d", str(path.parent)])
        cmd = ["sudo", "install", "-m", f"{mode:o}"]
        if owner is not None:
            cmd.extend(["-o", owner])
        if group is not None:
            cmd.extend(["-g", group])
        cmd.extend([str(temp_path), str(path)])
        run(cmd)


def ssh_agent_public_keys(ssh_auth_sock: str | None) -> list[str]:
    if not ssh_auth_sock:
        return []

    try:
        proc = subprocess.run(
            ["ssh-add", "-L"],
            cwd=REPO_ROOT,
            env={**os.environ, "SSH_AUTH_SOCK": ssh_auth_sock},
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolingError(
            "ssh-add is unavailable in the runtime image. Install openssh-client."
        ) from exc

    output = proc.stdout.strip()
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        recoverable_errors = (
            "The agent has no identities",
            "Error connecting to agent",
            "Could not open a connection to your authentication agent",
        )
        if any(message in output or message in stderr for message in recoverable_errors):
            return []
        raise ToolingError(f"ssh-add -L failed: {stderr or output}")
    return [line.strip() for line in output.splitlines() if line.strip()]


def sshd_running() -> bool:
    proc = subprocess.run(
        ["pgrep", "-x", "sshd"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def devcontainer_ssh_host_key_entries(*, wait: bool = True) -> list[str]:
    deadline = time.monotonic() + 15 if wait else time.monotonic()
    while True:
        proc = subprocess.run(
            [
                "ssh-keyscan",
                "-p",
                str(DEVCONTAINER_SSH_PORT),
                "localhost",
                DEVCONTAINER_SSH_HOST,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        entries = [
            line.strip()
            for line in proc.stdout.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if entries:
            return entries
        if time.monotonic() >= deadline:
            raise ToolingError(
                "failed to discover the devcontainer SSH host keys on "
                f"{DEVCONTAINER_SSH_HOST}:{DEVCONTAINER_SSH_PORT}"
            )
        time.sleep(0.5)


def remove_known_host_entry(known_hosts_path: Path, host: str) -> None:
    backup_path = known_hosts_path.with_name(f"{known_hosts_path.name}.old")
    proc = subprocess.run(
        ["ssh-keygen", "-R", host, "-f", str(known_hosts_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in {0, 255}:
        error_text = proc.stderr.strip() or proc.stdout.strip()
        raise ToolingError(
            f"failed to remove known_hosts entry for {host}: {error_text}"
        )
    if backup_path.exists():
        backup_path.unlink()


def ensure_host_port_available(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            raise ToolingError(
                f"{host}:{port} is already in use on the host. "
                "Free the port before starting the devcontainer."
            ) from exc


def ensure_local_devcontainer_image_user(image_ref: str, username: str) -> None:
    inspect = subprocess.run(
        ["docker", "image", "inspect", image_ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode != 0:
        raise ToolingError(
            f"local image {image_ref!r} is missing. "
            "Run `mise run build-devcontainer-image` first."
        )

    platform_probe = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform=linux/amd64",
            "--user",
            "root",
            "--entrypoint",
            "uname",
            image_ref,
            "-m",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if platform_probe.returncode != 0:
        error_text = platform_probe.stderr.strip() or platform_probe.stdout.strip()
        raise ToolingError(
            f"local image {image_ref!r} is not runnable as linux/amd64. "
            "Rebuild it with `mise run build-devcontainer-image` first. "
            f"Docker said: {error_text}"
        )

    proc = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform=linux/amd64",
            "--user",
            "root",
            "--entrypoint",
            "getent",
            image_ref,
            "passwd",
            username,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ToolingError(
            f"local image {image_ref!r} does not contain user {username!r}. "
            "Rebuild it with `mise run build-devcontainer-image` "
            "before running `mise run devcontainer-up-macos`."
        )


def docker_image_config_user(image_ref: str) -> str:
    proc = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .Config.User}}", image_ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        error_text = proc.stderr.strip() or proc.stdout.strip()
        raise ToolingError(f"failed to inspect {image_ref}: {error_text}")
    return json.loads(proc.stdout.strip())


def docker_run_shell(image_ref: str, script: str, *, user: str = "root") -> str:
    proc = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform=linux/amd64",
            "--user",
            user,
            "--entrypoint",
            "bash",
            image_ref,
            "-lc",
            script,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        error_text = proc.stderr.strip() or proc.stdout.strip()
        raise ToolingError(f"{image_ref} failed validation command {script!r}: {error_text}")
    return proc.stdout.strip()


def docker_export_paths(image_ref: str) -> set[str]:
    create = subprocess.run(
        ["docker", "create", image_ref],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if create.returncode != 0:
        error_text = create.stderr.strip() or create.stdout.strip()
        raise ToolingError(f"failed to create a validation container for {image_ref}: {error_text}")
    container_id = create.stdout.strip()
    try:
        export_proc = subprocess.run(
            ["docker", "export", container_id],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if export_proc.returncode != 0:
            error_text = export_proc.stderr.decode("utf-8", errors="replace").strip()
            raise ToolingError(f"failed to export {image_ref}: {error_text}")
        tar_proc = subprocess.run(
            ["tar", "-tf", "-"],
            cwd=REPO_ROOT,
            input=export_proc.stdout,
            capture_output=True,
            text=True,
            check=False,
        )
        if tar_proc.returncode != 0:
            error_text = tar_proc.stderr.strip() or tar_proc.stdout.strip()
            raise ToolingError(
                f"failed to inspect exported filesystem for {image_ref}: {error_text}"
            )
        return {line.strip().rstrip("/") for line in tar_proc.stdout.splitlines() if line.strip()}
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


def assert_contains(output: str, expected: str, *, label: str) -> None:
    if expected not in output:
        raise ToolingError(f"{label} must contain {expected!r}; got {output!r}")


def validate_repo_base_image(manifest: dict[str, Any], image_ref: str) -> None:
    config_user = docker_image_config_user(image_ref)
    if config_user not in {"", "root"}:
        raise ToolingError(
            f"{image_ref} must remain root-addressable; got Config.User={config_user!r}"
        )

    binary_checks = {
        "bash": "command -v bash",
        "git": "command -v git",
        "node": "command -v node",
        "mise": "command -v mise",
        "uv": "command -v uv",
        "pixi": "command -v pixi",
        "python3": "command -v python3",
        "clang-stable++": "command -v clang-stable++",
        "vcpkg": "test -x /opt/vcpkg/vcpkg && printf yes",
    }
    for _label, script in binary_checks.items():
        docker_run_shell(image_ref, script)

    version_checks = {
        "node": (["node", "--version"], f"v{version_of(manifest, 'node')}"),
        "mise": (["mise", "--version"], version_of(manifest, "mise")),
        "uv": (["uv", "--version"], version_of(manifest, "uv")),
        "pixi": (["pixi", "--version"], version_of(manifest, "pixi")),
        "python3": (["python3", "--version"], manifest_python_version(manifest)),
        "clang": (["clang", "--version"], version_of(manifest, "llvm")),
    }
    for label, (cmd, expected) in version_checks.items():
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--platform=linux/amd64",
            "--entrypoint",
            cmd[0],
            image_ref,
            *cmd[1:],
        ]
        output = run(
            docker_cmd,
            capture=True,
        )
        assert_contains(output, expected, label=f"{image_ref} {label}")

    path_checks = {
        "/opt/vcpkg": "test -d /opt/vcpkg && printf ok",
        "/opt/llvm/current": "test -L /opt/llvm/current && readlink -f /opt/llvm/current",
        "/usr/local/bin/clang-stable++": "test -x /usr/local/bin/clang-stable++ && printf ok",
    }
    for label, script in path_checks.items():
        output = docker_run_shell(image_ref, script)
        if label == "/opt/llvm/current":
            assert_contains(output, version_of(manifest, "llvm"), label=f"{image_ref} {label}")

    native_checks = (
        "mise doctor >/tmp/mise-doctor.txt && test -s /tmp/mise-doctor.txt",
        "pixi info >/tmp/pixi-info.txt && test -s /tmp/pixi-info.txt",
        "python3 -m pip show conan | grep -F 'Version: 2.'",
        "/opt/vcpkg/vcpkg version",
    )
    for script in native_checks:
        docker_run_shell(image_ref, script)


def validate_artifact_image(image_ref: str, required_paths: tuple[str, ...]) -> None:
    exported_paths = docker_export_paths(image_ref)
    missing_paths = [path for path in required_paths if path not in exported_paths]
    if missing_paths:
        raise ToolingError(f"{image_ref} is missing exported artifact paths: {missing_paths}")


def validate_final_base_image(manifest: dict[str, Any], image_ref: str) -> None:
    config_user = docker_image_config_user(image_ref)
    if config_user not in {"", "root"}:
        raise ToolingError(
            f"{image_ref} must not bake in a devcontainer user; got {config_user!r}"
        )
    docker_run_shell(
        image_ref,
        "command -v clang-p2996++ && command -v g++-reflection && "
        "command -v smoke-reflection",
    )
    docker_run_shell(
        image_ref,
        "test -d /opt/clang-p2996 && test -d /opt/gcc-reflection && smoke-reflection",
    )
    assert_contains(
        docker_run_shell(image_ref, "clang-p2996++ --version"),
        version_of(manifest, "llvm"),
        label=f"{image_ref} clang-p2996++",
    )
    gcc_version = docker_run_shell(image_ref, "g++-reflection --version")
    assert_contains(gcc_version, "g++", label=f"{image_ref} g++-reflection")
    default_home = Path(f"/home/{DEVCONTAINER_DEFAULT_USER}").as_posix().lstrip("/")
    if default_home in docker_export_paths(image_ref):
        raise ToolingError(f"{image_ref} must not contain the shared default devcontainer home")


def validate_devcontainer_image(
    manifest: dict[str, Any],
    image_ref: str,
    *,
    expected_user: str,
) -> None:
    config_user = docker_image_config_user(image_ref)
    if config_user != expected_user:
        raise ToolingError(
            f"{image_ref} must set Config.User={expected_user!r}; got {config_user!r}"
        )
    assert_contains(
        docker_run_shell(image_ref, "whoami", user=expected_user),
        expected_user,
        label=f"{image_ref} whoami",
    )
    assert_contains(
        docker_run_shell(image_ref, 'printf "%s" "$HOME"', user=expected_user),
        f"/home/{expected_user}",
        label=f"{image_ref} HOME",
    )
    docker_run_shell(
        image_ref,
        "command -v ssh && command -v ssh-add && command -v smoke-reflection && "
        "sudo -n true && /usr/sbin/sshd -t",
        user=expected_user,
    )
    docker_run_shell(
        image_ref,
        "test -d ~/.cache/ccache && test -d ~/.local/share/mise && "
        "test -d ~/.config/gh && smoke-reflection",
        user=expected_user,
    )
    assert_contains(
        docker_run_shell(image_ref, "node --version", user=expected_user),
        f"v{version_of(manifest, 'node')}",
        label=f"{image_ref} node",
    )


def validate_docker_images(
    manifest: dict[str, Any],
    *,
    image_tag_value: str,
    dev_user: str | None,
) -> None:
    image_refs = cpp26_local_image_refs(manifest, image_tag_value)
    validate_repo_base_image(manifest, image_refs["repo_base"])
    validate_artifact_image(
        image_refs["clang"],
        ("opt/clang-p2996/bin/clang", "opt/clang-p2996/bin/clang++"),
    )
    validate_artifact_image(
        image_refs["gcc"],
        ("opt/gcc-reflection/bin/gcc", "opt/gcc-reflection/bin/g++"),
    )
    validate_final_base_image(manifest, image_refs["final_base"])
    if dev_user is not None:
        validate_devcontainer_image(manifest, image_refs["devcontainer"], expected_user=dev_user)


def latest_git_ref(repo: str, ref: str) -> str:
    output = run(["git", "ls-remote", repo, ref], capture=True)
    if not output:
        raise ToolingError(f"failed to discover ref {ref} from {repo}")
    return output.splitlines()[0].split()[0]


def cpp26_toolchain_refs(manifest: dict[str, Any]) -> tuple[str, str]:
    image_config = manifest["cpp26_dev_images"]
    latest_clang = latest_git_ref(image_config["clang_p2996_repo"], "refs/heads/p2996")
    latest_gcc = latest_git_ref(image_config["gcc_reflection_repo"], "refs/heads/reflection")
    return latest_clang, latest_gcc


def report_cpp26_toolchain_pins(manifest: dict[str, Any]) -> bool:
    image_config = manifest["cpp26_dev_images"]
    latest_clang, latest_gcc = cpp26_toolchain_refs(manifest)
    print(f"clang_p2996_ref current={image_config['clang_p2996_ref']} latest={latest_clang}")
    print(f"gcc_reflection_ref current={image_config['gcc_reflection_ref']} latest={latest_gcc}")
    pins_current = (
        image_config["clang_p2996_ref"] == latest_clang
        and image_config["gcc_reflection_ref"] == latest_gcc
    )
    print("Pins are up to date" if pins_current else "Pins are stale")
    return pins_current


def normalize_registry_prefix(registry_prefix: str) -> str:
    if not registry_prefix:
        return ""
    return f"{registry_prefix.rstrip('/')}/"


def cpp26_bake_env(
    *,
    platform_name: str,
    cpp26_image_tag: str,
    registry_prefix: str,
    extra_env: dict[str, str] | None = None,
) -> dict[str, str]:
    env = {
        "PLATFORM": platform_name,
        "CPP26_IMAGE_TAG": cpp26_image_tag,
        "CPP26_REGISTRY_PREFIX": normalize_registry_prefix(registry_prefix),
    }
    if extra_env:
        env.update(extra_env)
    return env


def render_command_preview(cmd: list[str], env: dict[str, str]) -> str:
    assignments = " ".join(f"{key}={shlex.quote(value)}" for key, value in env.items())
    return f"env {assignments} {shlex.join(cmd)}"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "phase0-review"


def normalize_chezmoi_source_part(part: str) -> str:
    normalized = part
    prefix_tokens = (
        "private_",
        "readonly_",
        "empty_",
        "encrypted_",
        "literal_",
        "symlink_",
        "create_",
        "exact_",
        "modify_",
        "executable_",
    )
    changed = True
    while changed:
        changed = False
        if normalized.startswith("dot_"):
            normalized = f".{normalized[4:]}"
            changed = True
            continue
        for prefix in prefix_tokens:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                changed = True
                break
    return normalized


def iter_chezmoi_target_paths() -> Iterator[Path]:
    if not CHEZMOI_SOURCE_ROOT.exists():
        return
    for path in sorted(CHEZMOI_SOURCE_ROOT.rglob("*")):
        if path.is_dir():
            continue
        relative = path.relative_to(CHEZMOI_SOURCE_ROOT)
        relative_text = relative.as_posix()
        if relative_text == ".chezmoi.toml.tmpl":
            continue
        if any(
            relative_text == prefix or relative_text.startswith(f"{prefix}/")
            for prefix in CHEZMOI_NON_TARGET_PATH_PREFIXES
        ):
            continue
        normalized_parts = [normalize_chezmoi_source_part(part) for part in relative.parts]
        if not normalized_parts:
            continue
        yield Path(*normalized_parts)


def repo_relative_to_home() -> Path | None:
    try:
        return REPO_ROOT.relative_to(Path.home())
    except ValueError:
        return None


def target_within_repo(target_path: Path) -> Path | None:
    repo_relative = repo_relative_to_home()
    if repo_relative is None:
        return None
    repo_parts = repo_relative.parts
    target_parts = target_path.parts
    if target_parts[: len(repo_parts)] != repo_parts:
        return None
    if len(target_parts) == len(repo_parts):
        return Path(".")
    return Path(*target_parts[len(repo_parts) :])


def path_overlaps_repo_generated_surface(repo_path: Path) -> bool:
    if repo_path in FORBIDDEN_REPO_GENERATED_PATHS:
        return True
    return any(
        repo_path == directory or directory in repo_path.parents
        for directory in FORBIDDEN_REPO_GENERATED_DIRS
    )


def validate_chezmoi_layout(manifest: dict[str, Any]) -> None:
    if not CHEZMOI_ROOT_FILE_PATH.exists():
        raise ToolingError(".chezmoiroot must exist")
    if not CHEZMOI_VERSION_FILE_PATH.exists():
        raise ToolingError(".chezmoiversion must exist")
    if CHEZMOI_ROOT_FILE_PATH.read_text().strip() != "home":
        raise ToolingError(".chezmoiroot must point at the host-scoped `home` source root")

    expected_chezmoi_version = version_of(manifest, "chezmoi")
    if CHEZMOI_VERSION_FILE_PATH.read_text().strip() != expected_chezmoi_version:
        raise ToolingError(
            f".chezmoiversion must pin chezmoi {expected_chezmoi_version!r}"
        )

    if not CHEZMOI_SOURCE_ROOT.is_dir():
        raise ToolingError("home/ must exist as the chezmoi source root")
    if not CHEZMOI_CONFIG_PATH.exists():
        raise ToolingError("home/.chezmoi.toml.tmpl must exist")
    if not CHEZMOI_SCRIPTS_DIR.is_dir():
        raise ToolingError("home/.chezmoiscripts/ must exist")

    misplaced_specials = sorted(
        path.name
        for path in REPO_ROOT.iterdir()
        if path.name.startswith(".chezmoi")
        and path.name not in {".chezmoiroot", ".chezmoiversion"}
    )
    if misplaced_specials:
        raise ToolingError(
            "all chezmoi special files other than .chezmoiroot/.chezmoiversion must live "
            f"under home/: {misplaced_specials}"
        )

    overlaps: list[str] = []
    for target_path in iter_chezmoi_target_paths():
        repo_target = target_within_repo(target_path)
        if repo_target is None or repo_target == Path("."):
            continue
        if path_overlaps_repo_generated_surface(repo_target):
            overlaps.append(f"{target_path.as_posix()} -> {repo_target.as_posix()}")
    if overlaps:
        raise ToolingError(
            "chezmoi must stay host-scoped and must not manage repo-generated surfaces: "
            f"{overlaps}"
        )


def phase0_output_dir(plan_path: Path, slug: str | None) -> Path:
    resolved_slug = slugify(slug or plan_path.stem)
    return PLAN_REVIEW_ROOT / resolved_slug


def phase0_required_skill_names(*, committee: bool) -> tuple[str, ...]:
    required = ("adversarial-thinking", "code-doubter")
    if committee:
        return (*required, "adversarial-committee")
    return required


def phase0_skill_candidate_paths(skill_name: str) -> tuple[Path, ...]:
    return (
        PROJECT_SKILLS_DIR / skill_name / "SKILL.md",
        CODEX_SKILLS_DIR / skill_name / "SKILL.md",
    )


def phase0_skill_path(skill_name: str) -> Path | None:
    for candidate in phase0_skill_candidate_paths(skill_name):
        if candidate.exists():
            return candidate
    return None


def phase0_missing_skill_names(*, committee: bool) -> list[str]:
    return [
        skill_name
        for skill_name in phase0_required_skill_names(committee=committee)
        if phase0_skill_path(skill_name) is None
    ]


def phase0_probe_install_tool(command: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return True, "available"
    detail = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
    return False, detail


def phase0_skill_readiness_markdown(*, committee: bool) -> str:
    skills_cli_ok, skills_cli_detail = phase0_probe_install_tool(
        ["npx", "-y", "skills", "--help"]
    )
    skillfish_ok, skillfish_detail = phase0_probe_install_tool(
        ["npx", "-y", "skillfish", "--help"]
    )

    lines = [
        "# Skill Rubric Readiness",
        "",
        "- Installer task: `mise run install-phase0-review-skills`",
        (
            f"- `npx skills`: "
            f"`{'available' if skills_cli_ok else 'unavailable'}` ({skills_cli_detail})"
        ),
        (
            f"- `npx skillfish`: "
            f"`{'available' if skillfish_ok else 'unavailable'}` ({skillfish_detail})"
        ),
        "",
        "## Local Rubric Installs",
        "",
    ]

    required = set(phase0_required_skill_names(committee=committee))
    for skill_name in PHASE0_SKILL_NAMES:
        spec = PHASE0_SKILL_SPECS[skill_name]
        skill_path = phase0_skill_path(skill_name)
        requirement = "required" if skill_name in required else "escalation-only"
        if skill_path is None:
            lines.append(
                f"- `{skill_name}` ({requirement}, {spec['purpose']}): "
                "`missing` from `.agents/skills` and `.codex/skills`"
            )
            continue
        try:
            relative_path = skill_path.relative_to(REPO_ROOT)
        except ValueError:
            relative_path = skill_path
        lines.append(
            f"- `{skill_name}` ({requirement}, {spec['purpose']}): "
            f"`{relative_path}` from `{spec['repo']}`"
        )
    return "\n".join(lines) + "\n"


def ensure_phase0_skill_install_tools() -> None:
    for command in (
        ["npx", "-y", "skills", "--help"],
        ["npx", "-y", "skillfish", "--help"],
    ):
        proc = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            detail = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
            raise ToolingError(
                "required Phase 0 install tool is unavailable: "
                f"{' '.join(command)} ({detail})"
            )


def install_phase0_review_skills() -> None:
    ensure_phase0_skill_install_tools()

    for skill_name in PHASE0_SKILL_NAMES:
        existing_path = phase0_skill_path(skill_name)
        if existing_path is not None:
            try:
                existing_relative = existing_path.relative_to(REPO_ROOT)
            except ValueError:
                existing_relative = existing_path
            print(f"Phase 0 rubric already installed: {skill_name} -> {existing_relative}")
            continue

        spec = PHASE0_SKILL_SPECS[skill_name]
        print(f"Installing Phase 0 rubric: {skill_name} from {spec['repo']}")
        run(
            [
                "npx",
                "-y",
                "skillfish",
                "add",
                str(spec["repo"]),
                skill_name,
                "--project",
                "-y",
            ],
            stream=True,
        )

    missing_after_install = phase0_missing_skill_names(committee=True)
    if missing_after_install:
        raise ToolingError(
            "Phase 0 rubric installation did not produce the expected local skill files: "
            f"{missing_after_install}"
        )

    installed_listing = json.loads(
        run(["npx", "-y", "skills", "list", "--json"], capture=True)
    )
    installed_names = {
        entry["name"]: entry
        for entry in installed_listing
        if entry["name"] in PHASE0_SKILL_NAMES
    }
    print("Installed Phase 0 review rubrics:")
    for skill_name in PHASE0_SKILL_NAMES:
        entry = installed_names.get(skill_name)
        if entry is not None:
            print(f"- {skill_name}: {entry['path']}")
            continue
        skill_path = phase0_skill_path(skill_name)
        assert skill_path is not None
        print(f"- {skill_name}: {skill_path}")


def strip_markdown_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    closing_index = text.find("\n---\n", 4)
    if closing_index == -1:
        return text
    return text[closing_index + len("\n---\n") :]


def extract_top_level_markdown_section(text: str, heading: str) -> str | None:
    prefix = f"## {heading}"
    lines = text.splitlines()
    capture = False
    section_lines: list[str] = []
    for line in lines:
        if line == prefix:
            capture = True
        elif capture and line.startswith("## "):
            break
        if capture:
            section_lines.append(line)
    if not section_lines:
        return None
    return "\n".join(section_lines).strip()


def phase0_skill_rubrics_markdown(*, committee: bool) -> str:
    rubric_names = phase0_required_skill_names(committee=committee)
    blocks: list[str] = []
    missing: list[str] = []

    for skill_name in rubric_names:
        skill_path = phase0_skill_path(skill_name)
        if skill_path is None:
            missing.append(skill_name)
            continue

        spec = PHASE0_SKILL_SPECS[skill_name]
        raw_text = skill_path.read_text()
        stripped_text = strip_markdown_frontmatter(raw_text).strip()
        selected_sections = [
            extract_top_level_markdown_section(stripped_text, heading)
            for heading in spec["sections"]
        ]
        section_text = "\n\n".join(section for section in selected_sections if section)
        if not section_text:
            section_text = stripped_text

        try:
            relative_path = skill_path.relative_to(REPO_ROOT)
        except ValueError:
            relative_path = skill_path
        blocks.append(
            "\n".join(
                [
                    f"## {skill_name}",
                    f"- Local file: `{relative_path}`",
                    f"- Upstream repo: `{spec['repo']}`",
                    f"- Intended use in this gate: {spec['purpose']}",
                    "",
                    section_text,
                ]
            ).strip()
        )

    if missing:
        blocks.append(
            textwrap.dedent(
                f"""\
                ## Missing Local Rubrics
                - Missing local skill installs: {", ".join(f"`{name}`" for name in missing)}
                - Install them first with `mise run install-phase0-review-skills`
                """
            ).strip()
        )

    return "\n\n".join(blocks).strip() + "\n"


def summarize_markdown_for_prompt(text: str, *, max_lines: int) -> str:
    summary_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("## ", "### ", "- ")) or (
            not summary_lines or summary_lines[-1].startswith(("## ", "### "))
        ):
            summary_lines.append(stripped)
        if len(summary_lines) >= max_lines:
            break
    return "\n".join(summary_lines).strip()


def phase0_skill_prompt_brief_markdown(*, committee: bool) -> str:
    rubric_names = phase0_required_skill_names(committee=committee)
    blocks: list[str] = []
    missing: list[str] = []

    for skill_name in rubric_names:
        skill_path = phase0_skill_path(skill_name)
        if skill_path is None:
            missing.append(skill_name)
            continue

        spec = PHASE0_SKILL_SPECS[skill_name]
        raw_text = skill_path.read_text()
        stripped_text = strip_markdown_frontmatter(raw_text).strip()
        selected_sections = [
            extract_top_level_markdown_section(stripped_text, heading)
            for heading in spec["sections"]
        ]
        section_text = "\n\n".join(section for section in selected_sections if section)
        if not section_text:
            section_text = stripped_text
        summary_text = summarize_markdown_for_prompt(section_text, max_lines=14)
        if not summary_text:
            summary_text = section_text.splitlines()[0].strip()

        blocks.append(
            "\n".join(
                [
                    f"## {skill_name}",
                    f"- Intended use: {spec['purpose']}",
                    summary_text,
                ]
            ).strip()
        )

    if missing:
        blocks.append(
            textwrap.dedent(
                f"""\
                ## Missing Local Rubrics
                - Missing local skill installs: {", ".join(f"`{name}`" for name in missing)}
                - Install them first with `mise run install-phase0-review-skills`
                """
            ).strip()
        )

    return "\n\n".join(blocks).strip() + "\n"


def model_cli_ready_markdown() -> str:
    claude_status_raw = run(["claude", "auth", "status"], capture=True)
    try:
        claude_status = json.loads(claude_status_raw)
    except json.JSONDecodeError as exc:
        raise ToolingError(f"claude auth status did not return valid JSON: {exc}") from exc
    if not claude_status.get("loggedIn"):
        raise ToolingError("claude auth status reports loggedIn=false")

    gemini_status = run(["gemini", "-l"], capture=True, strip=False)
    return textwrap.dedent(
        f"""\
        # Model Readiness

        - Claude logged in: `{claude_status.get("loggedIn")}`
        - Claude auth method: `{claude_status.get("authMethod")}`
        - Claude org: `{claude_status.get("orgName")}`
        - Gemini extension inventory command: `gemini -l`

        ## Raw Gemini Extension Output

        ```text
        {gemini_status.strip()}
        ```
        """
    )


def repo_review_context(manifest: dict[str, Any]) -> str:
    pixi_data = tomllib.loads(PIXI_TOML_PATH.read_text())
    pixi_tasks = sorted((pixi_data.get("tasks") or {}).keys())
    mise_data = tomllib.loads(MISE_TOML_PATH.read_text())
    mise_tools = sorted((mise_data.get("tools") or {}).keys())
    devcontainer = json.loads(DEVCONTAINER_JSON_PATH.read_text())

    return textwrap.dedent(
        f"""\
        # Repo Context

        - Repo root: `{REPO_ROOT}`
        - Repo path relative to `$HOME`: `{repo_relative_to_home() or "not-under-home"}`
        - Current public migration plan file: `{DEFAULT_PHASE0_PLAN_PATH.relative_to(REPO_ROOT)}`

        ## Current Ownership Model

        - Repo-generated files owned by the Python control plane:
          - `README.md`
          - `mise.toml`
          - `pixi.toml`
          - `CMakePresets.json`
          - `.devcontainer/devcontainer.json`
          - `.devcontainer/Dockerfile`
          - `docker-bake.hcl`
          - `tooling/cpp26-dev-images/*`
        - Current chezmoi source root target: `home/`
        - Current chezmoi pin: `{version_of(manifest, "chezmoi")}`

        ## Current CLI And Task Surfaces

        - Current mise tools: `{", ".join(mise_tools)}`
        - Current pixi tasks: `{", ".join(pixi_tasks)}`
        - Current public mise tasks expected after migration:
          `{", ".join(sorted(MISE_PUBLIC_TASKS))}`

        ## Current Devcontainer Wiring

        - `remoteUser`: `{devcontainer.get("remoteUser")}`
        - `postCreateCommand`: `{devcontainer.get("postCreateCommand")}`
        - `postStartCommand`: `{devcontainer.get("postStartCommand")}`
        - SSH publish arg required by validation: `{DEVCONTAINER_SSH_PUBLISH_ARG}`

        ## Current Validation Invariants

        - `mise.toml` must use native aliases such as `claude-code` and `gemini-cli`
        - `devcontainer.json` must keep `${{localEnv:USER}}` as the primary runtime user
        - repo-owned shell scripts for build or devcontainer flows are forbidden
        - Apple Silicon remains a non-authoritative proof path for Linux `amd64` TSan evidence
        """
    )


def build_initial_review_prompt(
    *,
    reviewer: str,
    findings_prefix: str,
    focus: str,
    plan_text: str,
    repo_context: str,
    skill_rubrics: str,
) -> str:
    return textwrap.dedent(
        f"""\
        You are running a Phase 0 adversarial review of a repository migration plan.

        Use the locally installed skill rubrics below as the review-lens source of truth.
        They are excerpts from repo-local skill installs, not a live external runtime.

        Reviewer role: {reviewer}
        Findings ID prefix: {findings_prefix}
        Focus: {focus}

        Ground the review in the supplied repo context. Do not invent current repo state.

        Local review rubrics:

        {skill_rubrics}

        Output exactly these sections:
        ## Goal Restatement
        ## What's Strong
        ## Findings
        ## Open Risks
        ## Recommended Plan Changes

        In `## Findings`, use numbered bullets and assign stable IDs like `{findings_prefix}-1`.
        For each finding, explain:
        - what is wrong
        - why it matters
        - the smallest correct adjustment

        Migration plan:

        ```markdown
        {plan_text}
        ```

        Repo context:

        ```markdown
        {repo_context}
        ```
        """
    )


def build_cross_examination_prompt(
    *,
    reviewer: str,
    counterpart: str,
    findings_prefix: str,
    plan_text: str,
    own_review: str,
    counterpart_review: str,
) -> str:
    return textwrap.dedent(
        f"""\
        You are {reviewer}. Re-review the migration plan after reading {counterpart}'s findings.

        Output exactly these sections:
        ## Dispositions
        ## Additional Risks

        In `## Dispositions`, evaluate every `{findings_prefix}-*` finding from {counterpart}.
        Use a flat numbered list with this exact shape:

        1. `{findings_prefix}-1` — `agree|partially agree|reject` —
           <rationale> — <required plan change or `none`>

        Only add `## Additional Risks` if reading the other review exposed something genuinely new.

        Migration plan:

        ```markdown
        {plan_text}
        ```

        Your original review:

        ```markdown
        {own_review}
        ```

        {counterpart}'s review:

        ```markdown
        {counterpart_review}
        ```
        """
    )


def build_committee_prompt(
    *,
    plan_text: str,
    claude_review: str,
    gemini_review: str,
    claude_on_gemini: str,
    gemini_on_claude: str,
    skill_rubrics: str,
) -> str:
    return textwrap.dedent(
        f"""\
        Use the locally installed committee rubric below as the arbitration source of truth.
        This is a repo-local skill excerpt, not a live external runtime.

        Local committee rubric:

        {skill_rubrics}

        Run a lightweight adversarial committee with three personas:
        - Skeptic: hunts hidden risk and rollback gaps
        - Maintainer: optimizes for long-term simplicity and ownership clarity
        - Operator: optimizes for bootstrap reliability and day-2 workflows

        Your job is to arbitrate only the high-impact disagreements between Claude and Gemini.

        Output exactly these sections:
        ## High-Impact Disagreements
        ## Committee Verdict
        ## Required Plan Changes

        Migration plan:

        ```markdown
        {plan_text}
        ```

        Claude initial review:

        ```markdown
        {claude_review}
        ```

        Gemini initial review:

        ```markdown
        {gemini_review}
        ```

        Claude cross-examination:

        ```markdown
        {claude_on_gemini}
        ```

        Gemini cross-examination:

        ```markdown
        {gemini_on_claude}
        ```
        """
    )


def build_synthesis_prompt(
    *,
    plan_text: str,
    claude_review: str,
    gemini_review: str,
    claude_on_gemini: str,
    gemini_on_claude: str,
    committee_review: str | None,
) -> str:
    committee_block = ""
    if committee_review is not None:
        committee_block = textwrap.dedent(
            f"""\

            Committee review:

            ```markdown
            {committee_review}
            ```
            """
        )

    return textwrap.dedent(
        f"""\
        Synthesize the Phase 0 adversarial review into a single merged artifact.

        Output exactly these top-level sections, in this exact order:
        # Phase 0 Adversarial Review
        ## Accepted Findings
        ## Rejected Findings
        ## Open Risks
        ## Required Plan Changes

        Rules:
        - accepted means the issue is real enough to change the plan now
        - rejected means the issue should not change the plan
        - open risks are unresolved items worth monitoring but not yet blocking
        - required plan changes must be concrete and implementation-relevant
        - reference finding IDs when possible
        - keep the synthesis specific to this repo and this migration plan

        Migration plan:

        ```markdown
        {plan_text}
        ```

        Claude initial review:

        ```markdown
        {claude_review}
        ```

        Gemini initial review:

        ```markdown
        {gemini_review}
        ```

        Claude cross-examination:

        ```markdown
        {claude_on_gemini}
        ```

        Gemini cross-examination:

        ```markdown
        {gemini_on_claude}
        ```{committee_block}
        """
    )


def run_model_prompt(cmd: list[str], *, timeout_seconds: int) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolingError(
            f"command timed out after {timeout_seconds}s: {' '.join(cmd[:3])}"
        ) from exc
    if proc.returncode != 0:
        error_text = proc.stderr.strip() or proc.stdout.strip()
        raise ToolingError(
            f"command failed ({proc.returncode}): {' '.join(cmd[:3])}\n{error_text}"
        )
    output = proc.stdout.strip()
    if not output:
        raise ToolingError(f"command returned no output: {' '.join(cmd[:3])}")
    return output


def execute_model_review(model: str, prompt: str, *, timeout_seconds: int) -> str:
    if model == "claude":
        return run_model_prompt(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                "sonnet",
                "--output-format",
                "text",
                "--permission-mode",
                "plan",
                "--disable-slash-commands",
                "--tools",
                "",
                "--no-session-persistence",
            ],
            timeout_seconds=timeout_seconds,
        )
    if model == "gemini":
        return run_model_prompt(
            [
                "gemini",
                "-m",
                "gemini-2.5-pro",
                "-p",
                prompt,
                "--output-format",
                "text",
                "--approval-mode",
                "plan",
                "-e",
                "code-review",
            ],
            timeout_seconds=timeout_seconds,
        )
    raise ToolingError(f"unsupported model reviewer: {model}")


def review_plan_phase0(
    plan_path: Path,
    *,
    slug: str | None,
    timeout_seconds: int,
    synth_model: str,
    committee: bool,
    dry_run: bool,
) -> Path:
    resolved_plan_path = plan_path if plan_path.is_absolute() else REPO_ROOT / plan_path
    if not resolved_plan_path.exists():
        raise ToolingError(f"plan path does not exist: {resolved_plan_path}")

    manifest = load_manifest()
    plan_text = resolved_plan_path.read_text()
    repo_context = repo_review_context(manifest)
    output_dir = phase0_output_dir(resolved_plan_path, slug)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "input-plan.md").write_text(plan_text)
    (output_dir / "repo-context.md").write_text(repo_context)
    (output_dir / "readiness.md").write_text(model_cli_ready_markdown())
    (output_dir / "skill-readiness.md").write_text(
        phase0_skill_readiness_markdown(committee=committee)
    )
    full_skill_rubrics = phase0_skill_rubrics_markdown(committee=committee)
    prompt_skill_brief = phase0_skill_prompt_brief_markdown(committee=committee)
    (output_dir / "skill-rubrics.md").write_text(full_skill_rubrics)
    (output_dir / "skill-prompt-brief.md").write_text(prompt_skill_brief)

    claude_prompt = build_initial_review_prompt(
        reviewer="Claude acting as a skeptical senior architect",
        findings_prefix="CLAUDE",
        focus="duplication boundaries, sequencing errors, rollback gaps, and simpler alternatives",
        plan_text=plan_text,
        repo_context=repo_context,
        skill_rubrics=prompt_skill_brief,
    )
    gemini_prompt = build_initial_review_prompt(
        reviewer="Gemini acting as an independent adversarial reviewer",
        findings_prefix="GEMINI",
        focus="repo-wide consistency, missing validation, and current-state cross-checking",
        plan_text=plan_text,
        repo_context=repo_context,
        skill_rubrics=prompt_skill_brief,
    )
    (output_dir / "claude-initial-prompt.md").write_text(claude_prompt)
    (output_dir / "gemini-initial-prompt.md").write_text(gemini_prompt)
    if dry_run:
        return output_dir

    missing_skills = phase0_missing_skill_names(committee=committee)
    if missing_skills:
        raise ToolingError(
            "Phase 0 local review rubrics are missing: "
            f"{missing_skills}. Run `mise run install-phase0-review-skills` first."
        )

    claude_review = execute_model_review("claude", claude_prompt, timeout_seconds=timeout_seconds)
    gemini_review = execute_model_review("gemini", gemini_prompt, timeout_seconds=timeout_seconds)
    (output_dir / "claude-initial-review.md").write_text(claude_review + "\n")
    (output_dir / "gemini-initial-review.md").write_text(gemini_review + "\n")

    claude_cross_prompt = build_cross_examination_prompt(
        reviewer="Claude",
        counterpart="Gemini",
        findings_prefix="GEMINI",
        plan_text=plan_text,
        own_review=claude_review,
        counterpart_review=gemini_review,
    )
    gemini_cross_prompt = build_cross_examination_prompt(
        reviewer="Gemini",
        counterpart="Claude",
        findings_prefix="CLAUDE",
        plan_text=plan_text,
        own_review=gemini_review,
        counterpart_review=claude_review,
    )
    (output_dir / "claude-cross-prompt.md").write_text(claude_cross_prompt)
    (output_dir / "gemini-cross-prompt.md").write_text(gemini_cross_prompt)

    claude_on_gemini = execute_model_review(
        "claude", claude_cross_prompt, timeout_seconds=timeout_seconds
    )
    gemini_on_claude = execute_model_review(
        "gemini", gemini_cross_prompt, timeout_seconds=timeout_seconds
    )
    (output_dir / "claude-on-gemini.md").write_text(claude_on_gemini + "\n")
    (output_dir / "gemini-on-claude.md").write_text(gemini_on_claude + "\n")

    committee_review: str | None = None
    if committee:
        committee_prompt = build_committee_prompt(
            plan_text=plan_text,
            claude_review=claude_review,
            gemini_review=gemini_review,
            claude_on_gemini=claude_on_gemini,
            gemini_on_claude=gemini_on_claude,
            skill_rubrics=prompt_skill_brief,
        )
        (output_dir / "committee-prompt.md").write_text(committee_prompt)
        committee_review = execute_model_review(
            synth_model, committee_prompt, timeout_seconds=timeout_seconds
        )
        (output_dir / "committee-review.md").write_text(committee_review + "\n")

    synthesis_prompt = build_synthesis_prompt(
        plan_text=plan_text,
        claude_review=claude_review,
        gemini_review=gemini_review,
        claude_on_gemini=claude_on_gemini,
        gemini_on_claude=gemini_on_claude,
        committee_review=committee_review,
    )
    (output_dir / "synthesis-prompt.md").write_text(synthesis_prompt)
    merged_review = execute_model_review(
        synth_model, synthesis_prompt, timeout_seconds=timeout_seconds
    )
    (output_dir / "merged-review.md").write_text(merged_review + "\n")
    return output_dir


def select_cpp26_build_targets(toolchain: str, flavor: str) -> list[str]:
    if toolchain not in {"clang", "gcc", "all"}:
        raise ToolingError(f"invalid toolchain: {toolchain}")
    if flavor not in {"core", "quantlib"}:
        raise ToolingError(f"invalid flavor: {flavor}")

    build_targets = ["repo_base"]
    if toolchain in {"clang", "all"}:
        build_targets.append("cpp26_clang_core")
        if flavor == "quantlib":
            build_targets.append("cpp26_clang_quantlib")
    if toolchain in {"gcc", "all"}:
        if flavor == "quantlib":
            print("quantlib flavor is clang-only; building gcc core instead")
        build_targets.append("cpp26_gcc_core")
    if toolchain == "all":
        build_targets.append("final_base")
    return build_targets


def build_cpp26_images(
    *,
    toolchain: str,
    flavor: str,
    platform_name: str | None = None,
    cpp26_image_tag: str | None = None,
    registry_prefix: str = "",
    dry_run: bool = False,
) -> None:
    manifest = load_manifest()
    image_config = manifest["cpp26_dev_images"]
    resolved_platform = platform_name or str(image_config.get("platform_default", "linux/amd64"))
    resolved_image_tag = cpp26_image_tag or image_tag(manifest, "cpp26_dev_clang")
    build_targets = select_cpp26_build_targets(toolchain, flavor)
    build_cpp26_targets(
        build_targets,
        platform_name=resolved_platform,
        cpp26_image_tag=resolved_image_tag,
        registry_prefix=registry_prefix,
        dry_run=dry_run,
    )
    if not dry_run and toolchain == "all":
        validate_docker_images(manifest, image_tag_value=resolved_image_tag, dev_user=None)


def build_cpp26_targets(
    build_targets: list[str],
    *,
    platform_name: str,
    cpp26_image_tag: str,
    registry_prefix: str,
    dry_run: bool = False,
) -> None:
    if not build_targets:
        raise ToolingError("no build targets selected")

    cmd = ["docker", "buildx", "bake", "-f", str(DOCKER_BAKE_PATH), "--load", *build_targets]
    env = cpp26_bake_env(
        platform_name=platform_name,
        cpp26_image_tag=cpp26_image_tag,
        registry_prefix=registry_prefix,
    )
    print(f"Building targets: {' '.join(build_targets)}")
    if dry_run:
        print(f"[dry-run] {render_command_preview(cmd, env)}")
        return
    run(cmd, env=env, stream=True)
    print("Build workflow completed")


def resolve_version(source: dict[str, str]) -> str:
    kind = source["kind"]
    if kind == "github_release":
        payload = json.loads(
            fetch_text(
                f"https://api.github.com/repos/{source['owner']}/{source['repo']}/releases/latest"
            )
        )
        tag_name = payload["tag_name"]
        prefix = source.get("tag_prefix", "")
        if prefix and tag_name.startswith(prefix):
            return tag_name[len(prefix) :]
        return tag_name
    if kind == "kernel_latest_stable":
        payload = json.loads(fetch_text("https://www.kernel.org/releases.json"))
        return payload["latest_stable"]["version"]
    if kind == "gnu_gcc_latest":
        html = fetch_text("https://ftp.gnu.org/gnu/gcc/")
        versions = sorted(
            {
                tuple(int(part) for part in match.split("."))
                for match in re.findall(r"gcc-(\d+\.\d+\.\d+)/", html)
            }
        )
        if not versions:
            raise ToolingError("failed to discover a GCC release from ftp.gnu.org")
        return ".".join(str(part) for part in versions[-1])
    if kind == "npm":
        output = run(
            ["npm", "view", source["package"], "version"],
            env={"MISE_DISABLE_TOOLS": "1"},
            capture=True,
        )
        return output.splitlines()[-1]
    if kind == "pixi_search":
        output = run(
            ["pixi", "search", source["package"], "--channel", "conda-forge"],
            capture=True,
        )
        match = re.search(r"^Version\s+(\S+)$", output, flags=re.MULTILINE)
        if not match:
            match = re.search(rf"{re.escape(source['package'])}-(\S+)-", output)
        if not match:
            raise ToolingError(f"failed to parse pixi search output for {source['package']}")
        return match.group(1)
    if kind == "pypi":
        payload = json.loads(fetch_text(f"https://pypi.org/pypi/{source['package']}/json"))
        return str(payload["info"]["version"])
    raise ToolingError(f"unsupported source kind: {kind}")


def latest_tool_versions() -> dict[str, str]:
    return {
        tool_name: resolve_version(source)
        for tool_name, source in UPSTREAM_TOOL_SOURCES.items()
    }


def render_docker_bake_hcl(manifest: dict[str, Any]) -> str:
    text = DOCKER_BAKE_PATH.read_text()
    replacements = (
        (
            r'(^variable "NODE_VERSION" \{\n\s+default = )".*?"(\n\})',
            version_of(manifest, "node"),
        ),
        (
            r'(^variable "NODE_MAJOR" \{\n\s+default = )".*?"(\n\})',
            node_major(manifest),
        ),
        (
            r'(^variable "MISE_VERSION" \{\n\s+default = )".*?"(\n\})',
            f"v{version_of(manifest, 'mise')}",
        ),
        (
            r'(^variable "UV_VERSION" \{\n\s+default = )".*?"(\n\})',
            version_of(manifest, "uv"),
        ),
        (
            r'(^variable "PIXI_VERSION" \{\n\s+default = )".*?"(\n\})',
            f"v{version_of(manifest, 'pixi')}",
        ),
        (
            r'(^variable "LLVM_VERSION" \{\n\s+default = )".*?"(\n\})',
            version_of(manifest, "llvm"),
        ),
    )
    for pattern, value in replacements:
        text = replace_quoted_setting(text, pattern, value, "docker-bake.hcl")
    return text


def render_devcontainer_json(manifest: dict[str, Any]) -> str:
    text = DEVCONTAINER_JSON_PATH.read_text()
    image_name = image_ref(manifest, "cpp_devcontainer")
    updated, count = re.subn(
        r'(^\s*"image": )".*?"(,)$',
        rf'\1"{image_name}"\2',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ToolingError("unable to update .devcontainer/devcontainer.json image ref in place")
    updated, _ = re.subn(
        r'\n\s*"CPP_PLAYGROUND_TOOL_VERSION_MANIFEST": ".*?",?',
        "",
        updated,
        flags=re.MULTILINE,
    )
    updated, _ = re.subn(r",\n(\s*})", r"\n\1", updated)
    return updated


def render_dockerfile(manifest: dict[str, Any]) -> str:
    text = DOCKERFILE_PATH.read_text()
    cpp26_images = manifest["cpp26_dev_images"]
    replacements = (
        (r"^ARG UBUNTU_VERSION=.*$", f"ARG UBUNTU_VERSION={cpp26_images['ubuntu_version']}"),
        (
            r"^ARG REPO_BASE_IMAGE=.*$",
            f"ARG REPO_BASE_IMAGE={image_ref(manifest, 'cpp_devcontainer_repo_base')}",
        ),
        (
            r"^ARG FINAL_BASE_IMAGE=.*$",
            f"ARG FINAL_BASE_IMAGE={image_ref(manifest, 'cpp_devcontainer_base')}",
        ),
        (r"^ARG CLANG_IMAGE=.*$", f"ARG CLANG_IMAGE={image_ref(manifest, 'cpp26_dev_clang')}"),
        (r"^ARG GCC_IMAGE=.*$", f"ARG GCC_IMAGE={image_ref(manifest, 'cpp26_dev_gcc')}"),
        (r"^ARG NODE_VERSION=.*$", f"ARG NODE_VERSION={version_of(manifest, 'node')}"),
        (r"^ARG NODE_MAJOR=.*$", f"ARG NODE_MAJOR={node_major(manifest)}"),
        (r"^ARG MISE_VERSION=.*$", f"ARG MISE_VERSION=v{version_of(manifest, 'mise')}"),
        (r"^ARG UV_VERSION=.*$", f"ARG UV_VERSION={version_of(manifest, 'uv')}"),
        (r"^ARG PIXI_VERSION=.*$", f"ARG PIXI_VERSION=v{version_of(manifest, 'pixi')}"),
        (r"^ARG LLVM_VERSION=.*$", f"ARG LLVM_VERSION={version_of(manifest, 'llvm')}"),
        (r"^ARG LLVM_ARCHIVE=.*$", f"ARG LLVM_ARCHIVE={llvm_archive_name(manifest)}"),
        (r"^ARG LLVM_DOWNLOAD_URL=.*$", f"ARG LLVM_DOWNLOAD_URL={llvm_download_url(manifest)}"),
        (r"^ARG VCPKG_BUNDLE_URL=.*$", f"ARG VCPKG_BUNDLE_URL={cpp26_images['vcpkg_bundle_url']}"),
    )
    for pattern, replacement in replacements:
        text = replace_required_line(text, pattern, replacement, ".devcontainer/Dockerfile")
    return text


def render_readme(manifest: dict[str, Any]) -> str:
    text = README_PATH.read_text()
    replacements = (
        (r"- Node `v[^`]+`", f"- Node `v{version_of(manifest, 'node')}`"),
        (r"- LLVM `[^`]+`", f"- LLVM `{version_of(manifest, 'llvm')}`"),
        (r"- GCC `[^`]+`", f"- GCC `{version_of(manifest, 'gcc')}`"),
        (r"- `mise` `[^`]+`", f"- `mise` `{version_of(manifest, 'mise')}`"),
        (r"- `uv` `[^`]+`", f"- `uv` `{version_of(manifest, 'uv')}`"),
        (r"- `pixi` `[^`]+`", f"- `pixi` `{version_of(manifest, 'pixi')}`"),
        (r"- GitHub CLI `[^`]+`", f"- GitHub CLI `{version_of(manifest, 'gh')}`"),
        (r"- Codex CLI `[^`]+`", f"- Codex CLI `{version_of(manifest, 'codex_cli')}`"),
        (r"- Claude Code `[^`]+`", f"- Claude Code `{version_of(manifest, 'claude_code')}`"),
        (r"- Gemini CLI `[^`]+`", f"- Gemini CLI `{version_of(manifest, 'gemini_cli')}`"),
        (r"- `just` `[^`]+`", f"- `just` `{version_of(manifest, 'just')}`"),
        (r"- `chezmoi` `[^`]+`", f"- `chezmoi` `{version_of(manifest, 'chezmoi')}`"),
        (r"- `watchexec` `[^`]+`", f"- `watchexec` `{version_of(manifest, 'watchexec')}`"),
        (
            r"- `include-what-you-use` `[^`]+` in the Linux `llvm-stable` pixi environment",
            (
                "- `include-what-you-use` "
                f"`{version_of(manifest, 'include_what_you_use')}` in the Linux "
                "`llvm-stable` pixi environment"
            ),
        ),
        (
            r"- `mise run sync-generated`: .*",
            (
                "- `mise run sync-generated`: synchronize derived cross-file pins from the "
                "native checked-in config without querying upstreams."
            ),
        ),
        (
            r"- `mise run validate-repo`: .*",
            (
                "- `mise run validate-repo`: verify committed config stays aligned with the "
                "native checked-in files and native tool metadata."
            ),
        ),
        (
            r"- `mise run validate-runtime`: .*",
            (
                "- `mise run validate-runtime`: run native tool verification commands first, "
                "then verify installed versions match the native checked-in pins."
            ),
        ),
        (
            r"- Repo-generated surfaces remain owned by the Python control plane.*",
            (
                "- The Python control plane validates and synchronizes derived values, "
                "but the checked-in native files remain the source of truth."
            ),
        ),
    )
    for pattern, replacement in replacements:
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
        if count == 0 and replacement in text:
            continue
        if count != 1:
            raise ToolingError(f"README.md is missing expected pattern {pattern!r}")
    return text


def sync_generated_files(manifest: dict[str, Any]) -> None:
    DOCKER_BAKE_PATH.write_text(render_docker_bake_hcl(manifest))
    DEVCONTAINER_JSON_PATH.write_text(render_devcontainer_json(manifest))
    DOCKERFILE_PATH.write_text(render_dockerfile(manifest))
    README_PATH.write_text(render_readme(manifest))


def validate_repo(manifest: dict[str, Any]) -> None:
    validate_chezmoi_layout(manifest)

    dockerfile = DOCKERFILE_PATH.read_text()
    mise_toml = MISE_TOML_PATH.read_text()
    docker_bake = DOCKER_BAKE_PATH.read_text()
    readme_text = README_PATH.read_text()
    pixi_data = load_toml(PIXI_TOML_PATH)
    pyproject_data = load_toml(PYPROJECT_TOML_PATH)
    for forbidden in ('"latest"', "=latest", "NODE_MAJOR=22", 'default = "22"'):
        if forbidden in dockerfile or forbidden in mise_toml or forbidden in docker_bake:
            raise ToolingError(f"forbidden stale or floating version token detected: {forbidden}")

    if "docker-buildx-plugin" not in dockerfile or "docker-ce-cli" not in dockerfile:
        raise ToolingError(
            "Dockerfile must explicitly install docker-ce-cli and docker-buildx-plugin"
        )
    if "linux-tools-generic" not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile base stage must install linux-tools-generic")
    bake_targets = {
        entry["name"]: entry
        for entry in run_json(
            [
                "docker",
                "buildx",
                "bake",
                "-f",
                str(DOCKER_BAKE_PATH),
                "--list=type=targets,format=json",
            ]
        )
    }
    for required_target_name in (
        "repo_base",
        "final_base",
        "dev",
        "cpp26_clang_core",
        "cpp26_gcc_core",
    ):
        if required_target_name not in bake_targets:
            raise ToolingError(f"docker-bake.hcl must expose target {required_target_name!r}")

    bake_graph = run_json(
        [
            "docker",
            "buildx",
            "bake",
            "-f",
            str(DOCKER_BAKE_PATH),
            "--print",
            "repo_base",
            "cpp26_clang_core",
            "cpp26_gcc_core",
            "final_base",
            "dev",
        ]
    )["target"]
    if bake_graph["cpp26_clang_core"].get("target") != "artifact":
        raise ToolingError("cpp26_clang_core must export the artifact stage")
    if bake_graph["cpp26_gcc_core"].get("target") != "artifact":
        raise ToolingError("cpp26_gcc_core must export the artifact stage")
    if bake_graph["repo_base"].get("target") != "repo_base":
        raise ToolingError("repo_base must export the repo_base stage")
    if bake_graph["final_base"].get("target") != "final_base":
        raise ToolingError("final_base must export the final_base stage")
    if bake_graph["dev"].get("target") != "devcontainer":
        raise ToolingError("dev must export the devcontainer stage")

    clang_contexts = bake_graph["cpp26_clang_core"].get("contexts") or {}
    gcc_contexts = bake_graph["cpp26_gcc_core"].get("contexts") or {}
    final_contexts = bake_graph["final_base"].get("contexts") or {}
    dev_contexts = bake_graph["dev"].get("contexts") or {}
    if clang_contexts.get("base") != "target:repo_base":
        raise ToolingError("cpp26_clang_core must inherit repo_base through Bake contexts")
    if gcc_contexts.get("base") != "target:repo_base":
        raise ToolingError("cpp26_gcc_core must inherit repo_base through Bake contexts")
    if final_contexts.get("repo_base") != "target:repo_base":
        raise ToolingError("final_base must inherit repo_base through Bake contexts")
    if final_contexts.get("clang_core") != "target:cpp26_clang_core":
        raise ToolingError("final_base must inherit clang_core through Bake contexts")
    if final_contexts.get("gcc_core") != "target:cpp26_gcc_core":
        raise ToolingError("final_base must inherit gcc_core through Bake contexts")
    if dev_contexts != {"final_base": "target:final_base"}:
        raise ToolingError("dev target must inherit only final_base through Bake contexts")

    for compiler_dockerfile in (
        CPP26_IMAGE_CLANG_DOCKERFILE_PATH,
        CPP26_IMAGE_GCC_DOCKERFILE_PATH,
    ):
        compiler_text = compiler_dockerfile.read_text()
        if "FROM ubuntu:" in compiler_text:
            raise ToolingError(
                f"{compiler_dockerfile.relative_to(REPO_ROOT)} must inherit from the shared "
                "base image instead of ubuntu directly"
            )
        if "FROM ${BASE_IMAGE}" not in compiler_text:
            raise ToolingError(
                f"{compiler_dockerfile.relative_to(REPO_ROOT)} must consume the shared BASE_IMAGE"
            )
        if "FROM scratch AS artifact" not in compiler_text:
            raise ToolingError(
                f"{compiler_dockerfile.relative_to(REPO_ROOT)} must end in an "
                "artifact-only scratch stage"
            )
        if "USER ${DEVCONTAINER_USERNAME}" in compiler_text:
            raise ToolingError(
                f"{compiler_dockerfile.relative_to(REPO_ROOT)} must not bake in the "
                "devcontainer user"
            )

    if "FROM ${REPO_BASE_IMAGE} AS final_base" not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile must materialize a final_base stage")
    if "FROM ${FINAL_BASE_IMAGE} AS devcontainer" not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile must materialize a devcontainer stage")
    if "RUN smoke-reflection" not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile final_base stage must run smoke-reflection")

    presets = json.loads(CMAKE_PRESETS_PATH.read_text())
    present = {preset["name"] for preset in presets["configurePresets"]}
    missing = EXPECTED_PRESETS - present
    if missing:
        raise ToolingError(f"CMakePresets.json is missing required presets: {sorted(missing)}")

    missing_sources = sorted(
        path.relative_to(REPO_ROOT) for path in REQUIRED_KERNEL_SOURCES if not path.exists()
    )
    if missing_sources:
        raise ToolingError(f"missing kernel source files: {missing_sources}")

    mise_data = load_toml(MISE_TOML_PATH)
    mise_tools = mise_data.get("tools")
    if not isinstance(mise_tools, dict):
        raise ToolingError("mise.toml must define a [tools] table")

    expected_mise_tools = {
        MISE_NATIVE_TOOL_ALIASES["node"]: version_of(manifest, "node"),
        MISE_NATIVE_TOOL_ALIASES["python"]: manifest_python_version(manifest),
        MISE_NATIVE_TOOL_ALIASES["uv"]: version_of(manifest, "uv"),
        MISE_NATIVE_TOOL_ALIASES["pixi"]: version_of(manifest, "pixi"),
        MISE_NATIVE_TOOL_ALIASES["gh"]: version_of(manifest, "gh"),
        MISE_NATIVE_TOOL_ALIASES["codex_cli"]: version_of(manifest, "codex_cli"),
        MISE_NATIVE_TOOL_ALIASES["claude_code"]: version_of(manifest, "claude_code"),
        MISE_NATIVE_TOOL_ALIASES["gemini_cli"]: version_of(manifest, "gemini_cli"),
        MISE_NATIVE_TOOL_ALIASES["just"]: version_of(manifest, "just"),
        MISE_NATIVE_TOOL_ALIASES["chezmoi"]: version_of(manifest, "chezmoi"),
        MISE_NATIVE_TOOL_ALIASES["watchexec"]: version_of(manifest, "watchexec"),
    }
    backend_qualified_keys = sorted(key for key in mise_tools if ":" in key)
    if backend_qualified_keys:
        raise ToolingError(
            "mise.toml must use native mise registry aliases before backend-qualified "
            f"selectors: {backend_qualified_keys}"
        )

    missing_mise_keys = sorted(set(expected_mise_tools) - set(mise_tools))
    unexpected_mise_keys = sorted(set(mise_tools) - set(expected_mise_tools))
    if missing_mise_keys or unexpected_mise_keys:
        raise ToolingError(
            "mise.toml tool aliases drifted from the native alias policy. "
            f"missing={missing_mise_keys} unexpected={unexpected_mise_keys}"
        )

    for alias, expected_version in expected_mise_tools.items():
        if str(mise_tools[alias]) != expected_version:
            raise ToolingError(
                f"mise.toml pins {alias}={mise_tools[alias]!r}; expected {expected_version!r}"
            )

    mise_tasks = {
        task["name"]: task
        for task in run_json(["mise", "tasks", "ls", "--json"])
        if Path(task["source"]) == MISE_TOML_PATH
    }
    missing_mise_tasks = sorted(set(MISE_PUBLIC_TASKS) - set(mise_tasks))
    if missing_mise_tasks:
        raise ToolingError(f"mise.toml is missing required public tasks: {missing_mise_tasks}")
    for task_name, expected_run in MISE_PUBLIC_TASKS.items():
        task_spec = mise_tasks[task_name]
        run_list = task_spec.get("run") or []
        if run_list != [expected_run]:
            raise ToolingError(
                f"mise task {task_name!r} must run {expected_run!r}; got {run_list!r}"
            )

    pixi_tasks: dict[str, str] = {}
    for environment in run_json(["pixi", "task", "list", "--json"]):
        for feature in environment.get("features", []):
            for task in feature.get("tasks", []):
                pixi_tasks.setdefault(task["name"], task["cmd"])
    missing_pixi_tasks = sorted(set(MISE_PUBLIC_TASKS) - set(pixi_tasks))
    if missing_pixi_tasks:
        raise ToolingError(f"pixi.toml is missing required public tasks: {missing_pixi_tasks}")
    for task_name, expected_run in MISE_PUBLIC_TASKS.items():
        if pixi_tasks[task_name] != expected_run:
            raise ToolingError(
                f"pixi task {task_name!r} must run {expected_run!r}; got {pixi_tasks[task_name]!r}"
            )

    if (
        str(pyproject_data["project"]["requires-python"])
        != f">={manifest_python_version(manifest)}"
    ):
        raise ToolingError("pyproject.toml requires-python must track the repo python pin")
    if pyproject_dev_dependency_version(pyproject_data, "ruff") != version_of(manifest, "ruff"):
        raise ToolingError("pyproject.toml must pin Ruff exactly and match the runtime checks")
    if pyproject_dev_dependency_version(pyproject_data, "ty") != version_of(manifest, "ty"):
        raise ToolingError("pyproject.toml must pin Ty exactly and match the runtime checks")

    if str(pixi_data["workspace"]["requires-pixi"]) != f">={version_of(manifest, 'pixi')}":
        raise ToolingError("pixi.toml requires-pixi must track the pinned pixi CLI version")
    if str(pixi_data["dependencies"]["python"]) != f"{manifest_python_version(manifest)}.*":
        raise ToolingError("pixi.toml python dependency must track the repo python pin")
    if (
        str(pixi_data["feature"]["llvm-stable"]["activation"]["env"]["LLVM_VERSION"])
        != version_of(manifest, "llvm")
    ):
        raise ToolingError("pixi llvm-stable activation env must track the pinned LLVM version")
    for env_key in ("CC", "CXX", "LLVM_HOME"):
        env_value = str(pixi_data["feature"]["llvm-stable"]["activation"]["env"][env_key])
        if version_of(manifest, "llvm") not in env_value:
            raise ToolingError(f"pixi llvm-stable {env_key} must embed the pinned LLVM version")
    if pixi_exact_dependency_version(pixi_data, "gcc-stable", "gcc_linux-64") != version_of(
        manifest, "gcc"
    ):
        raise ToolingError("pixi gcc_linux-64 pin must track the pinned GCC version")
    if pixi_exact_dependency_version(pixi_data, "gcc-stable", "gxx_linux-64") != version_of(
        manifest, "gcc"
    ):
        raise ToolingError("pixi gxx_linux-64 pin must track the pinned GCC version")
    if pixi_exact_dependency_version(
        pixi_data, "llvm-stable", "include-what-you-use"
    ) != version_of(manifest, "include_what_you_use"):
        raise ToolingError("pixi include-what-you-use pin must stay exact")

    if f'ARG NODE_VERSION={version_of(manifest, "node")}' not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile NODE_VERSION must track mise.toml")
    if f'ARG NODE_MAJOR={node_major(manifest)}' not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile NODE_MAJOR must track mise.toml")
    if f'ARG MISE_VERSION=v{version_of(manifest, "mise")}' not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile MISE_VERSION must track mise.toml")
    if f'ARG UV_VERSION={version_of(manifest, "uv")}' not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile UV_VERSION must track mise.toml")
    if f'ARG PIXI_VERSION=v{version_of(manifest, "pixi")}' not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile PIXI_VERSION must track mise.toml")
    if f'ARG LLVM_VERSION={version_of(manifest, "llvm")}' not in dockerfile:
        raise ToolingError(".devcontainer/Dockerfile LLVM_VERSION must track pixi.toml")
    if (
        version_of(manifest, "node") not in readme_text
        or version_of(manifest, "llvm") not in readme_text
    ):
        raise ToolingError("README.md baselines must reflect the pinned native tool versions")

    devcontainer = json.loads(DEVCONTAINER_JSON_PATH.read_text())
    if devcontainer.get("remoteUser") != "${localEnv:USER}":
        raise ToolingError("devcontainer.json remoteUser must track ${localEnv:USER}")

    gh_mount = "type=volume,src=gh-config,target=/home/${localEnv:USER}/.config/gh"
    mounts = devcontainer.get("mounts")
    if not isinstance(mounts, list) or gh_mount not in mounts:
        raise ToolingError("devcontainer.json must persist GitHub CLI auth in gh-config")

    devcontainer_text = DEVCONTAINER_JSON_PATH.read_text()
    for forbidden in (
        "${localEnv:OPENAI_API_KEY}",
        "${localEnv:ANTHROPIC_API_KEY}",
        "${localEnv:GOOGLE_API_KEY}",
        "${localEnv:GEMINI_API_KEY}",
    ):
        if forbidden in devcontainer_text:
            raise ToolingError(f"devcontainer.json must not pass through {forbidden}")

    if devcontainer.get("postCreateCommand") != DEVCONTAINER_POST_CREATE_COMMAND:
        raise ToolingError(
            "devcontainer.json postCreateCommand must invoke the Python control plane through "
            "`uv run -m tooling`"
        )
    if devcontainer.get("postStartCommand") != DEVCONTAINER_POST_START_COMMAND:
        raise ToolingError(
            "devcontainer.json postStartCommand must invoke the Python SSH control plane "
            "through `uv run -m tooling`"
        )
    run_args = devcontainer.get("runArgs")
    if not isinstance(run_args, list) or DEVCONTAINER_SSH_PUBLISH_ARG not in run_args:
        raise ToolingError(
            "devcontainer.json must publish host-local SSH access with "
            f"{DEVCONTAINER_SSH_PUBLISH_ARG}"
        )

    operational_shell_scripts: list[Path] = []
    for script_dir in OPERATIONAL_SHELL_SCRIPT_DIRS:
        if script_dir.exists():
            operational_shell_scripts.extend(sorted(script_dir.rglob("*.sh")))
    if operational_shell_scripts:
        shell_script_list = [path.relative_to(REPO_ROOT) for path in operational_shell_scripts]
        raise ToolingError(
            "repo-owned build/devcontainer shell scripts are forbidden; use `uv run -m tooling` "
            f"instead: {shell_script_list}"
        )

    ensure_repo_text_absent("vs" + "code")


def validate_runtime(manifest: dict[str, Any]) -> None:
    for cmd in NATIVE_VALIDATION_COMMANDS.values():
        run(cmd, capture=True)

    runtime_commands = dict(REQUIRED_RUNTIME_COMMANDS)
    checks = {
        "node": f"v{version_of(manifest, 'node')}",
        "mise": version_of(manifest, "mise"),
        "uv": version_of(manifest, "uv"),
        "pixi": version_of(manifest, "pixi"),
        "gh": version_of(manifest, "gh"),
        "codex": version_of(manifest, "codex_cli"),
        "claude": version_of(manifest, "claude_code"),
        "gemini": version_of(manifest, "gemini_cli"),
        "just": version_of(manifest, "just"),
        "chezmoi": version_of(manifest, "chezmoi"),
        "watchexec": version_of(manifest, "watchexec"),
    }
    if is_linux_x64():
        checks["iwyu"] = version_of(manifest, "include_what_you_use")
    else:
        runtime_commands.pop("iwyu", None)

    for name, cmd in runtime_commands.items():
        output = run(cmd, capture=True)
        expected = checks.get(name)
        if expected and expected not in output:
            raise ToolingError(f"{name} does not report the expected version {expected}: {output}")

    if is_linux_x64():
        clang_output = run(["clang", "--version"], capture=True)
        if version_of(manifest, "llvm") not in clang_output:
            raise ToolingError(f"clang does not report LLVM {version_of(manifest, 'llvm')}")

    ssh_bin = shutil.which("ssh")
    ssh_add_bin = shutil.which("ssh-add")
    if ssh_bin is None:
        raise ToolingError("ssh is unavailable in the runtime image")
    if ssh_add_bin is None:
        raise ToolingError("ssh-add is unavailable in the runtime image")

    ssh_proc = subprocess.run(
        [ssh_bin, "-V"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if ssh_proc.returncode != 0:
        raise ToolingError(f"ssh is unavailable: {ssh_proc.stderr.strip()}")
    if not Path(DEVCONTAINER_SSHD_BIN).exists():
        raise ToolingError(f"{DEVCONTAINER_SSHD_BIN} is missing from the runtime image")
    run(["sudo", "install", "-d", "-m", "755", "/run/sshd"])
    run(["sudo", DEVCONTAINER_SSHD_BIN, "-t"])


def bootstrap() -> None:
    pixi_args = ["pixi", "install"]
    if (REPO_ROOT / "pixi.lock").exists():
        pixi_args.append("--locked")
    run(pixi_args)
    run(["mise", "trust", str(REPO_ROOT)])
    with isolated_mise_environment() as mise_env:
        run(["mise", "install", "--locked"], env=mise_env)
        run(["mise", "reshim"], env=mise_env)
    run(["uv", "sync", "--locked", "--group", "dev"])
    python_version = manifest_python_version(load_manifest())
    run(["uv", "tool", "install", "--python", python_version, "--upgrade", "gcovr"])
    run(["uv", "tool", "install", "--python", python_version, "--upgrade", "cmakelang"])
    print("\nReady.")
    print("  mise run validate-all")
    print("  mise run prove-devcontainer")
    print("  smoke-reflection")
    print("  gh auth login --git-protocol ssh")
    print(f"  {DEVCONTAINER_SSH_SMOKE_COMMAND}")


def manifest_python_version(manifest: dict[str, Any]) -> str:
    return str(manifest["python_version"])


def update_mise_toml(latest_versions: dict[str, str]) -> None:
    text = MISE_TOML_PATH.read_text()
    replacements = (
        (r'^node = ".*"$', f'node = "{latest_versions["node"]}"'),
        (r'^uv = ".*"$', f'uv = "{latest_versions["uv"]}"'),
        (r'^pixi = ".*"$', f'pixi = "{latest_versions["pixi"]}"'),
        (r'^gh = ".*"$', f'gh = "{latest_versions["gh"]}"'),
        (r'^codex = ".*"$', f'codex = "{latest_versions["codex_cli"]}"'),
        (r'^claude-code = ".*"$', f'claude-code = "{latest_versions["claude_code"]}"'),
        (r'^gemini-cli = ".*"$', f'gemini-cli = "{latest_versions["gemini_cli"]}"'),
        (r'^just = ".*"$', f'just = "{latest_versions["just"]}"'),
        (r'^chezmoi = ".*"$', f'chezmoi = "{latest_versions["chezmoi"]}"'),
        (r'^watchexec = ".*"$', f'watchexec = "{latest_versions["watchexec"]}"'),
    )
    for pattern, replacement in replacements:
        text = replace_required_line(text, pattern, replacement, "mise.toml")
    MISE_TOML_PATH.write_text(text)


def update_pyproject_toml(latest_versions: dict[str, str]) -> None:
    text = PYPROJECT_TOML_PATH.read_text()
    replacements = (
        (r'"ruff==[^"]+"', f'"ruff=={latest_versions["ruff"]}"'),
        (r'"ty==[^"]+"', f'"ty=={latest_versions["ty"]}"'),
    )
    for pattern, replacement in replacements:
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count != 1:
            raise ToolingError(f"unable to update pyproject.toml pattern {pattern!r}")
        text = updated
    PYPROJECT_TOML_PATH.write_text(text)


def update_pixi_toml(latest_versions: dict[str, str]) -> None:
    text = PIXI_TOML_PATH.read_text()
    replacements = (
        (r'^requires-pixi = ">=.*"$', f'requires-pixi = ">={latest_versions["pixi"]}"'),
        (
            r'^CC = "/opt/llvm/[^"]+/bin/clang"$',
            f'CC = "/opt/llvm/{latest_versions["llvm"]}/bin/clang"',
        ),
        (
            r'^CXX = "/opt/llvm/[^"]+/bin/clang\+\+"$',
            f'CXX = "/opt/llvm/{latest_versions["llvm"]}/bin/clang++"',
        ),
        (r'^LLVM_HOME = "/opt/llvm/[^"]+"$', f'LLVM_HOME = "/opt/llvm/{latest_versions["llvm"]}"'),
        (r'^LLVM_VERSION = ".*"$', f'LLVM_VERSION = "{latest_versions["llvm"]}"'),
        (
            r'^include-what-you-use = "==.*"$',
            f'include-what-you-use = "=={latest_versions["include_what_you_use"]}"',
        ),
        (r'^gcc_linux-64 = "==.*"$', f'gcc_linux-64 = "=={latest_versions["gcc"]}"'),
        (r'^gxx_linux-64 = "==.*"$', f'gxx_linux-64 = "=={latest_versions["gcc"]}"'),
    )
    for pattern, replacement in replacements:
        text = replace_required_line(text, pattern, replacement, "pixi.toml")
    PIXI_TOML_PATH.write_text(text)


def update_cpp26_toolchain_refs(*, clang_ref: str, gcc_ref: str) -> None:
    clang_text = CPP26_IMAGE_CLANG_DOCKERFILE_PATH.read_text()
    clang_text = replace_required_line(
        clang_text,
        r"^ARG CLANG_P2996_REF=.*$",
        f"ARG CLANG_P2996_REF={clang_ref}",
        "tooling/cpp26-dev-images/Dockerfile.clang-p2996",
    )
    CPP26_IMAGE_CLANG_DOCKERFILE_PATH.write_text(clang_text)

    gcc_text = CPP26_IMAGE_GCC_DOCKERFILE_PATH.read_text()
    gcc_text = replace_required_line(
        gcc_text,
        r"^ARG GCC_REFLECTION_REF=.*$",
        f"ARG GCC_REFLECTION_REF={gcc_ref}",
        "tooling/cpp26-dev-images/Dockerfile.gcc-reflection",
    )
    CPP26_IMAGE_GCC_DOCKERFILE_PATH.write_text(gcc_text)


def host_short_username() -> str:
    username = os.environ.get("USER") or getpass.getuser()
    if not username:
        raise ToolingError("failed to determine the host short username")
    if username == "root":
        raise ToolingError("refusing to build a devcontainer image for the root user")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", username):
        raise ToolingError(
            "host short username contains unsupported characters for the devcontainer "
            f"user model: {username!r}"
        )
    return username


def update_lockfiles() -> None:
    run(["uv", "lock"])
    run(["pixi", "lock"])
    with isolated_mise_environment() as mise_env:
        run(["mise", "lock"], env=mise_env)


def current_kernel_release() -> str:
    return platform.release().split("-", maxsplit=1)[0]


def is_linux_x64() -> bool:
    return platform.system() == "Linux" and platform.machine() in {"x86_64", "amd64"}


def require_linux_x64_root(surface: str, manifest: dict[str, Any]) -> None:
    if platform.system() != "Linux":
        raise ToolingError(f"{surface} requires Linux, found {platform.system()}")
    if platform.machine() not in {"x86_64", "amd64"}:
        raise ToolingError(f"{surface} requires x86_64/amd64, found {platform.machine()}")
    if os.geteuid() != 0:
        raise ToolingError(f"{surface} requires root to run the eBPF validation suite")


def configure_build_and_test(
    preset: str,
    *,
    label: str | None = None,
    pixi_env: str | None = None,
) -> None:
    def wrap(cmd: list[str]) -> list[str]:
        if pixi_env is None:
            return cmd
        return ["pixi", "run", "-e", pixi_env, *cmd]

    run(wrap(["cmake", "--preset", preset]))
    run(wrap(["cmake", "--build", "--preset", preset]))
    ctest_cmd = ["ctest", "--test-dir", f"out/build/{preset}", "--output-on-failure"]
    if label:
        ctest_cmd.extend(["-L", label])
    run(wrap(ctest_cmd))


def prove(surface: str, manifest: dict[str, Any]) -> None:
    validate_repo(manifest)
    if surface == "devcontainer":
        validate_runtime(manifest)
        run(["pixi", "install", "--locked"])
        run(["uv", "sync", "--locked", "--group", "dev"])
        run(["pixi", "run", "ruff-check"])
        run(["pixi", "run", "ruff-format"])
        run(["pixi", "run", "ty-check"])
        # This matrix is the authoritative userspace proof for a Linux amd64
        # devcontainer. On Apple Silicon hosts, Docker Desktop may satisfy
        # linux/amd64 through emulation; if llvm-tsan dies before test logic
        # runs and the process maps /run/rosetta/rosetta, track that as the
        # upstream emulation caveat in issue #1 instead of weakening this lane.
        for preset in ("llvm-stable", "llvm-asan", "llvm-tsan", "llvm-msan"):
            configure_build_and_test(preset, label="toolchain", pixi_env="llvm-stable")
        configure_build_and_test("gcc-stable", label="toolchain", pixi_env="gcc-stable")
        configure_build_and_test("gcc-reflection", label="toolchain")
        configure_build_and_test("clang-p2996", label="toolchain")
        return

    if surface in {"latest-kernel-vm", "latest-kernel-ci"}:
        require_linux_x64_root(surface, manifest)
        run(["pixi", "install", "--locked"])
        configure_build_and_test("llvm-stable", pixi_env="llvm-stable")
        configure_build_and_test("gcc-stable", pixi_env="gcc-stable")
        return

    raise ToolingError(f"unknown prove surface: {surface}")


def sync_github_known_hosts() -> None:
    _, known_hosts_path = ensure_user_ssh_paths()
    known_hosts_entries: list[str] = []
    if known_hosts_path.exists():
        known_hosts_entries.extend(
            line.strip() for line in known_hosts_path.read_text().splitlines() if line.strip()
        )

    payload = json.loads(fetch_text(GITHUB_META_API))
    ssh_keys = payload.get("ssh_keys")
    if not isinstance(ssh_keys, list) or not ssh_keys:
        raise ToolingError("GitHub metadata API did not return any SSH host keys")

    merged_entries = known_hosts_entries[:]
    for key in ssh_keys:
        entry = f"github.com {key}"
        if entry not in merged_entries:
            merged_entries.append(entry)

    known_hosts_path.write_text("\n".join(merged_entries) + "\n")
    known_hosts_path.chmod(0o600)


def ensure_devcontainer_ssh() -> None:
    actual_user = current_username()
    home_dir = Path(os.environ.get("HOME", f"/home/{actual_user}"))
    ssh_dir = home_dir / ".ssh"
    ssh_auth_sock = ensure_user_access_to_socket(
        os.environ.get("SSH_AUTH_SOCK", ""),
        actual_user=actual_user,
        label="SSH_AUTH_SOCK",
    )
    run(
        [
            "sudo",
            "install",
            "-d",
            "-m",
            "755",
            "/run/sshd",
            str(DEVCONTAINER_SSHD_DROPIN_PATH.parent),
            str(DEVCONTAINER_SSH_AUTH_PROFILE_PATH.parent),
        ]
    )
    run(["sudo", "ssh-keygen", "-A"])

    sshd_dropin = "\n".join(
        [
            "# Managed by uv run -m tooling ensure-devcontainer-ssh",
            "Port 22",
            "PasswordAuthentication no",
            "KbdInteractiveAuthentication no",
            "PubkeyAuthentication yes",
            "PermitRootLogin no",
            "AuthorizedKeysFile .ssh/authorized_keys",
            f"AllowUsers {actual_user}",
            "",
        ]
    )
    sudo_install_text(DEVCONTAINER_SSHD_DROPIN_PATH, sshd_dropin, mode=0o644)

    if ssh_auth_sock:
        quoted_sock = shlex.quote(ssh_auth_sock)
        profile_script = "\n".join(
            [
                "#!/usr/bin/env bash",
                "# Managed by uv run -m tooling ensure-devcontainer-ssh",
                f"if [ -S {quoted_sock} ]; then",
                f"  export SSH_AUTH_SOCK={quoted_sock}",
                "fi",
                "",
            ]
        )
        sudo_install_text(
            DEVCONTAINER_SSH_AUTH_PROFILE_PATH,
            profile_script,
            mode=0o644,
        )

    public_keys = ssh_agent_public_keys(ssh_auth_sock)
    if public_keys:
        run(
            [
                "sudo",
                "install",
                "-d",
                "-o",
                actual_user,
                "-g",
                actual_user,
                "-m",
                "700",
                str(ssh_dir),
            ]
        )
        authorized_keys = "\n".join(public_keys) + "\n"
        sudo_install_text(
            ssh_dir / "authorized_keys",
            authorized_keys,
            mode=0o600,
            owner=actual_user,
            group=actual_user,
        )
        print(f"Synced {len(public_keys)} SSH public key(s) into {ssh_dir / 'authorized_keys'}")
    else:
        authorized_keys_path = ssh_dir / "authorized_keys"
        warning_suffix = (
            "; no authorized_keys file exists yet, so host-local SSH login will still fail"
            if not authorized_keys_path.exists()
            else ""
        )
        print(
            "warning: SSH_AUTH_SOCK was unavailable or had no identities; "
            f"keeping existing authorized_keys{warning_suffix}"
        )

    run(["sudo", DEVCONTAINER_SSHD_BIN, "-t"])
    if sshd_running():
        print("sshd: already running")
        return
    run(["sudo", DEVCONTAINER_SSHD_BIN])
    print(f"sshd: listening on port 22 for {actual_user}")


def ensure_devcontainer_home_state(actual_user: str) -> None:
    home_dir = Path(os.environ.get("HOME", f"/home/{actual_user}"))
    managed_directories = [
        home_dir / ".cache",
        home_dir / ".cache" / "mise",
        home_dir / ".cache" / "rattler",
        home_dir / ".claude",
        home_dir / ".codex",
        home_dir / ".config",
        home_dir / ".config" / "gh",
        home_dir / ".gemini",
        home_dir / ".local",
        home_dir / ".local" / "bin",
        home_dir / ".local" / "share",
        home_dir / ".local" / "share" / "mise",
        home_dir / ".local" / "state",
        home_dir / ".pixi",
        home_dir / ".ssh",
    ]
    run(
        [
            "sudo",
            "install",
            "-d",
            "-o",
            actual_user,
            "-g",
            actual_user,
            *(str(path) for path in managed_directories),
        ]
    )
    run(
        [
            "sudo",
            "chown",
            "-R",
            f"{actual_user}:{actual_user}",
            str(home_dir / ".cache"),
            str(home_dir / ".claude"),
            str(home_dir / ".codex"),
            str(home_dir / ".config"),
            str(home_dir / ".gemini"),
            str(home_dir / ".local"),
            str(home_dir / ".pixi"),
            str(home_dir / ".ssh"),
        ]
    )


def post_create() -> None:
    actual_user = current_username()
    expected_user = os.environ.get("CPP_PLAYGROUND_HOST_USER", actual_user)
    if actual_user != expected_user:
        raise ToolingError(
            f"expected primary devcontainer user {expected_user} but found {actual_user}. "
            "Rebuild the image with `mise run build-devcontainer-image` on the host, "
            "then recreate the devcontainer."
        )

    ensure_devcontainer_home_state(actual_user)
    sync_github_known_hosts()
    bootstrap()
    print("\nReady.")
    print("  smoke-reflection")
    print("  gh auth login --git-protocol ssh")
    print("  gh auth status")
    print(f"  {DEVCONTAINER_SSH_SMOKE_COMMAND}")
    print("  mise run sync-devcontainer-ssh-known-hosts")
    print(f"  ssh -p {DEVCONTAINER_SSH_PORT} {actual_user}@{DEVCONTAINER_SSH_HOST}")
    print("  codex")
    print("  claude")
    print("  gemini")


def smoke_ssh_git_gh_parity() -> None:
    actual_user = current_username()
    print(f"whoami: {actual_user}")

    ssh_auth_sock = os.environ.get("SSH_AUTH_SOCK")
    if not ssh_auth_sock:
        raise ToolingError("SSH_AUTH_SOCK is not set")
    ensure_socket(ssh_auth_sock, label="SSH_AUTH_SOCK")

    run(["ssh-add", "-l"])
    ssh_proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-T",
            "git@github.com",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    ssh_output = f"{ssh_proc.stdout}{ssh_proc.stderr}"
    print(ssh_output, end="")
    if ssh_proc.returncode not in {0, 1}:
        raise ToolingError(f"GitHub SSH handshake failed with exit code {ssh_proc.returncode}")
    if "successfully authenticated" not in ssh_output:
        raise ToolingError("GitHub SSH handshake did not report a successful authentication")

    run(["git", "ls-remote", "origin"])
    run(["gh", "auth", "status"])
    run(["mise", "env"], capture=True)
    print("mise env: ok")


def sync_devcontainer_ssh_known_hosts(*, wait: bool = True) -> None:
    _, known_hosts_path = ensure_user_ssh_paths()
    known_hosts_path.touch(mode=0o600, exist_ok=True)
    for host in DEVCONTAINER_SSH_KNOWN_HOSTS:
        remove_known_host_entry(known_hosts_path, host)
    existing_entries = [
        line.strip() for line in known_hosts_path.read_text().splitlines() if line.strip()
    ]
    existing_entries.extend(devcontainer_ssh_host_key_entries(wait=wait))
    deduped_entries = list(dict.fromkeys(existing_entries))
    known_hosts_path.write_text("\n".join(deduped_entries) + ("\n" if deduped_entries else ""))
    known_hosts_path.chmod(0o600)
    print(f"Synced devcontainer SSH host keys for {', '.join(DEVCONTAINER_SSH_KNOWN_HOSTS)}")


def smoke_ssh_into_devcontainer() -> None:
    sync_devcontainer_ssh_known_hosts()
    user = host_short_username()
    remote_script = 'whoami\nprintf "HOME=%s\\n" "$HOME"\n'
    proc = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-p",
            str(DEVCONTAINER_SSH_PORT),
            f"{user}@{DEVCONTAINER_SSH_HOST}",
            f"bash -lc {shlex.quote(remote_script)}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    ssh_output = f"{proc.stdout}{proc.stderr}"
    print(ssh_output, end="")
    if proc.returncode != 0:
        raise ToolingError(
            "host-to-devcontainer SSH login failed on "
            f"{DEVCONTAINER_SSH_HOST}:{DEVCONTAINER_SSH_PORT}"
        )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    expected_home = f"HOME=/home/{user}"
    if user not in lines:
        raise ToolingError(f"expected whoami output {user!r}; got {lines}")
    if expected_home not in lines:
        raise ToolingError(f"expected remote home {expected_home!r}; got {lines}")
    print("Host-to-devcontainer SSH login: ok")


def host_preflight_macos() -> None:
    if platform.system() != "Darwin":
        raise ToolingError("this preflight is macOS-only")

    docker_info = subprocess.run(
        ["docker", "info", "--format", "{{.OperatingSystem}}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    docker_os = docker_info.stdout.strip()
    if docker_info.returncode != 0 or not docker_os:
        raise ToolingError("Docker is not available. Start Docker Desktop first.")
    if "Docker Desktop" not in docker_os:
        raise ToolingError(f"expected Docker Desktop on macOS, found: {docker_os}")
    ensure_host_port_available(DEVCONTAINER_SSH_HOST, DEVCONTAINER_SSH_PORT)

    ssh_auth_sock = os.environ.get("SSH_AUTH_SOCK")
    if not ssh_auth_sock:
        raise ToolingError("SSH_AUTH_SOCK is not set on the host")
    ensure_socket(ssh_auth_sock, label="SSH_AUTH_SOCK")

    ssh_add = subprocess.run(
        ["ssh-add", "-l"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if ssh_add.returncode != 0:
        raise ToolingError("ssh-add -l failed. Load a key into the host SSH agent first.")

    origin_url = run(["git", "-C", str(REPO_ROOT), "remote", "get-url", "origin"], capture=True)
    if not (origin_url.startswith("git@") or origin_url.startswith("ssh://")):
        raise ToolingError(f"origin must use SSH. Found: {origin_url}")

    print(f"Docker: {docker_os}")
    print(f"Host user: {os.environ.get('USER', actual_user())}")
    print(f"Origin: {origin_url}")


def actual_user() -> str:
    return os.environ.get("USER") or current_username()


def devcontainer_up_macos(extra_args: list[str]) -> None:
    host_preflight_macos()
    ensure_local_devcontainer_image_user("cpp-devcontainer:dev", host_short_username())
    passthrough = extra_args[:]
    if passthrough[:1] == ["--"]:
        passthrough = passthrough[1:]
    run(
        [
            "devcontainer",
            "up",
            "--workspace-folder",
            str(REPO_ROOT),
            "--mount",
            "type=bind,source=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock",
            "--remote-env",
            "SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock",
            *passthrough,
        ]
    )
    sync_devcontainer_ssh_known_hosts()
    print(
        "SSH login: "
        f"ssh -p {DEVCONTAINER_SSH_PORT} {host_short_username()}@{DEVCONTAINER_SSH_HOST}"
    )


def build_devcontainer_image(image_tag: str) -> None:
    manifest = load_manifest()
    image_config = manifest["cpp26_dev_images"]
    platform_name = str(image_config.get("platform_default", "linux/amd64"))
    resolved_user = host_short_username()
    cmd = [
        "docker",
        "buildx",
        "bake",
        "-f",
        str(DOCKER_BAKE_PATH),
        "--load",
        "repo_base",
        "cpp26_clang_core",
        "cpp26_gcc_core",
        "final_base",
        "dev",
    ]
    env = cpp26_bake_env(
        platform_name=platform_name,
        cpp26_image_tag=image_tag,
        registry_prefix="",
        extra_env={
            "TAG": image_tag,
            "DEVCONTAINER_USERNAME": resolved_user,
        },
    )
    run(cmd, env=env, stream=True)
    validate_docker_images(manifest, image_tag_value=image_tag, dev_user=resolved_user)
    print(f"Built {image_repo(manifest, 'cpp_devcontainer')}:{image_tag}")


def print_devcontainer_env(image_ref: str) -> None:
    print(f"CPP_DEVCONTAINER_IMAGE={image_ref}")
    print(f"CPP_PLAYGROUND_DEVCONTAINER_USER={host_short_username()}")
    print("CPP_PLAYGROUND_SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock")
    print(f"CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT={DEVCONTAINER_SSH_PORT}")


def cmd_refresh(args: argparse.Namespace) -> None:
    latest_versions = latest_tool_versions()
    update_mise_toml(latest_versions)
    update_pyproject_toml(latest_versions)
    update_pixi_toml(latest_versions)
    sync_generated_files(load_manifest())
    if not args.skip_locks:
        update_lockfiles()
    validate_repo(load_manifest())


def cmd_sync_generated(_: argparse.Namespace) -> None:
    manifest = load_manifest()
    sync_generated_files(manifest)
    validate_repo(manifest)


def cmd_check_cpp26_toolchain_pins(_: argparse.Namespace) -> int:
    manifest = load_manifest()
    return 0 if report_cpp26_toolchain_pins(manifest) else 2


def cmd_bump_cpp26_toolchain_pins(_: argparse.Namespace) -> None:
    manifest = load_manifest()
    latest_clang, latest_gcc = cpp26_toolchain_refs(manifest)
    update_cpp26_toolchain_refs(clang_ref=latest_clang, gcc_ref=latest_gcc)
    sync_generated_files(load_manifest())
    validate_repo(load_manifest())
    print("Updated cpp26 toolchain refs in the compiler Dockerfiles")


def cmd_validate(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    if args.mode in {"repo", "all"}:
        validate_repo(manifest)
    if args.mode in {"runtime", "all"}:
        validate_runtime(manifest)


def cmd_prove(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    prove(args.surface, manifest)


def cmd_bootstrap(_: argparse.Namespace) -> None:
    bootstrap()


def cmd_build_cpp26_images(args: argparse.Namespace) -> None:
    build_cpp26_images(
        toolchain=args.toolchain,
        flavor=args.flavor,
        platform_name=args.platform,
        cpp26_image_tag=args.image_tag,
        registry_prefix=args.registry_prefix,
        dry_run=args.dry_run,
    )


def cmd_build_devcontainer_image(args: argparse.Namespace) -> None:
    build_devcontainer_image(args.image_tag)


def cmd_validate_docker_images(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    validate_docker_images(
        manifest,
        image_tag_value=args.image_tag,
        dev_user=args.dev_user,
    )


def cmd_print_devcontainer_env(args: argparse.Namespace) -> None:
    print_devcontainer_env(args.image_ref)


def cmd_sync_github_known_hosts(_: argparse.Namespace) -> None:
    sync_github_known_hosts()


def cmd_post_create(_: argparse.Namespace) -> None:
    post_create()


def cmd_ensure_devcontainer_ssh(_: argparse.Namespace) -> None:
    ensure_devcontainer_ssh()


def cmd_smoke_ssh_git_gh_parity(_: argparse.Namespace) -> None:
    smoke_ssh_git_gh_parity()


def cmd_sync_devcontainer_ssh_known_hosts(_: argparse.Namespace) -> None:
    sync_devcontainer_ssh_known_hosts()


def cmd_smoke_ssh_into_devcontainer(_: argparse.Namespace) -> None:
    smoke_ssh_into_devcontainer()


def cmd_host_preflight_macos(_: argparse.Namespace) -> None:
    host_preflight_macos()


def cmd_devcontainer_up_macos(args: argparse.Namespace) -> None:
    devcontainer_up_macos(args.args)


def cmd_install_phase0_review_skills(_: argparse.Namespace) -> None:
    install_phase0_review_skills()


def cmd_review_plan_phase0(args: argparse.Namespace) -> None:
    output_dir = review_plan_phase0(
        Path(args.plan_path),
        slug=args.slug,
        timeout_seconds=args.timeout_seconds,
        synth_model=args.synth_model,
        committee=args.committee,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        print(f"Wrote Phase 0 prompts and readiness checks to {output_dir}")
        return
    print(f"Wrote Phase 0 review artifacts to {output_dir}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="cpp-playground Python control plane")
    subparsers = root.add_subparsers(dest="command", required=True)

    refresh = subparsers.add_parser(
        "refresh",
        help="Query upstreams and rewrite exact version pins",
    )
    refresh.add_argument(
        "--skip-locks",
        action="store_true",
        help="Skip pixi/mise lockfile regeneration",
    )
    refresh.set_defaults(func=cmd_refresh)

    sync_generated = subparsers.add_parser(
        "sync-generated",
        help=(
            "Refresh derived cross-file pins from native checked-in config "
            "without querying upstreams"
        ),
    )
    sync_generated.set_defaults(func=cmd_sync_generated)

    check_cpp26_pins = subparsers.add_parser(
        "check-cpp26-toolchain-pins",
        help="Check whether the pinned clang/gcc reflection refs match upstream branch heads",
    )
    check_cpp26_pins.set_defaults(func=cmd_check_cpp26_toolchain_pins)

    bump_cpp26_pins = subparsers.add_parser(
        "bump-cpp26-toolchain-pins",
        help="Refresh the pinned clang/gcc reflection refs and regenerate derived files",
    )
    bump_cpp26_pins.set_defaults(func=cmd_bump_cpp26_toolchain_pins)

    validate = subparsers.add_parser("validate", help="Validate repo or runtime state")
    validate.add_argument(
        "--mode",
        choices=("repo", "runtime", "all"),
        default="repo",
        help="Validation scope",
    )
    validate.set_defaults(func=cmd_validate)

    prove = subparsers.add_parser(
        "prove",
        help="Run end-to-end validation for a specific surface",
    )
    prove.add_argument(
        "--surface",
        choices=("devcontainer", "latest-kernel-vm", "latest-kernel-ci"),
        required=True,
        help="Execution surface to verify",
    )
    prove.set_defaults(func=cmd_prove)

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Install locked dev tools after devcontainer creation",
    )
    bootstrap_parser.set_defaults(func=cmd_bootstrap)

    build_cpp26 = subparsers.add_parser(
        "build-cpp26-images",
        help="Build cpp26 compiler images from the unified root docker-bake.hcl",
    )
    build_cpp26.add_argument("--toolchain", choices=("clang", "gcc", "all"), default="all")
    build_cpp26.add_argument("--flavor", choices=("core", "quantlib"), default="core")
    build_cpp26.add_argument("--platform", default=None)
    build_cpp26.add_argument("--image-tag", default=None)
    build_cpp26.add_argument("--registry-prefix", default="")
    build_cpp26.add_argument("--dry-run", action="store_true")
    build_cpp26.set_defaults(func=cmd_build_cpp26_images)

    build_image = subparsers.add_parser(
        "build-devcontainer-image",
        help="Build the wrapper devcontainer image",
    )
    build_image.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", "dev"))
    build_image.set_defaults(func=cmd_build_devcontainer_image)

    validate_docker_images_parser = subparsers.add_parser(
        "validate-docker-images",
        help=(
            "Validate the locally built repo_base, compiler artifact, final_base, "
            "and devcontainer images"
        ),
    )
    validate_docker_images_parser.add_argument(
        "--image-tag",
        default=os.environ.get("IMAGE_TAG", "dev"),
    )
    validate_docker_images_parser.add_argument(
        "--dev-user",
        default=os.environ.get("USER", DEVCONTAINER_DEFAULT_USER),
    )
    validate_docker_images_parser.set_defaults(func=cmd_validate_docker_images)

    env_parser = subparsers.add_parser(
        "print-devcontainer-env",
        help="Print a .env template for the devcontainer image",
    )
    env_parser.add_argument("image_ref", nargs="?", default="cpp-devcontainer:dev")
    env_parser.set_defaults(func=cmd_print_devcontainer_env)

    sync_known_hosts = subparsers.add_parser(
        "sync-github-known-hosts",
        help="Seed ~/.ssh/known_hosts with GitHub's published SSH host keys",
    )
    sync_known_hosts.set_defaults(func=cmd_sync_github_known_hosts)

    post_create_parser = subparsers.add_parser(
        "post-create",
        help="Run the devcontainer post-create bootstrap directly from Python",
    )
    post_create_parser.set_defaults(func=cmd_post_create)

    ensure_devcontainer_ssh_parser = subparsers.add_parser(
        "ensure-devcontainer-ssh",
        help="Configure and start the in-container SSH server for the current devcontainer user",
    )
    ensure_devcontainer_ssh_parser.set_defaults(func=cmd_ensure_devcontainer_ssh)

    smoke_parser = subparsers.add_parser(
        "smoke-ssh-git-gh-parity",
        help="Run the in-container SSH, git, gh, and mise parity smoke checks",
    )
    smoke_parser.set_defaults(func=cmd_smoke_ssh_git_gh_parity)

    sync_devcontainer_ssh = subparsers.add_parser(
        "sync-devcontainer-ssh-known-hosts",
        help="Seed the host known_hosts file with the current devcontainer SSH host keys",
    )
    sync_devcontainer_ssh.set_defaults(func=cmd_sync_devcontainer_ssh_known_hosts)

    smoke_devcontainer_ssh = subparsers.add_parser(
        "smoke-ssh-into-devcontainer",
        help="Verify host-to-devcontainer SSH login over localhost",
    )
    smoke_devcontainer_ssh.set_defaults(func=cmd_smoke_ssh_into_devcontainer)

    macos_preflight = subparsers.add_parser(
        "host-preflight-macos",
        help="Validate the macOS host prerequisites for devcontainer CLI usage",
    )
    macos_preflight.set_defaults(func=cmd_host_preflight_macos)

    macos_up = subparsers.add_parser(
        "devcontainer-up-macos",
        help="Run devcontainer up on macOS with the Docker Desktop SSH agent mount",
    )
    macos_up.add_argument("args", nargs=argparse.REMAINDER)
    macos_up.set_defaults(func=cmd_devcontainer_up_macos)

    install_phase0_skills = subparsers.add_parser(
        "install-phase0-review-skills",
        help="Install the local adversarial review rubrics used by the Phase 0 gate",
    )
    install_phase0_skills.set_defaults(func=cmd_install_phase0_review_skills)

    review_plan = subparsers.add_parser(
        "review-plan-phase0",
        help="Run the Phase 0 adversarial review gate against a migration plan",
    )
    review_plan.add_argument(
        "plan_path",
        nargs="?",
        default=str(DEFAULT_PHASE0_PLAN_PATH.relative_to(REPO_ROOT)),
        help="Path to the migration plan markdown file",
    )
    review_plan.add_argument("--slug", default=None, help="Output directory slug override")
    review_plan.add_argument(
        "--timeout-seconds",
        type=int,
        default=PHASE0_DEFAULT_TIMEOUT_SECONDS,
        help="Timeout for each model invocation",
    )
    review_plan.add_argument(
        "--synth-model",
        choices=("claude", "gemini"),
        default="claude",
        help="Model to use for synthesis and optional committee arbitration",
    )
    review_plan.add_argument(
        "--committee",
        action="store_true",
        help="Run an additional committee-style arbitration pass before synthesis",
    )
    review_plan.add_argument(
        "--dry-run",
        action="store_true",
        help="Write prompts and readiness artifacts without invoking Claude or Gemini",
    )
    review_plan.set_defaults(func=cmd_review_plan_phase0)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.func(args)
    except ToolingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if isinstance(result, int):
        return result
    return 0
