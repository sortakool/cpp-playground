from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "tooling" / "tool-version-manifest.json"
TEMPLATES_DIR = REPO_ROOT / "tooling" / "templates"
README_PATH = REPO_ROOT / "README.md"
MISE_TOML_PATH = REPO_ROOT / "mise.toml"
PIXI_TOML_PATH = REPO_ROOT / "pixi.toml"
DOCKERFILE_PATH = REPO_ROOT / ".devcontainer" / "Dockerfile"
DEVCONTAINER_JSON_PATH = REPO_ROOT / ".devcontainer" / "devcontainer.json"
DOCKER_BAKE_PATH = REPO_ROOT / "docker-bake.hcl"
CMAKE_PRESETS_PATH = REPO_ROOT / "CMakePresets.json"
CPP26_IMAGE_DIR = REPO_ROOT / "tooling" / "cpp26-dev-images"
CPP26_IMAGE_DOCKER_BAKE_PATH = CPP26_IMAGE_DIR / "docker-bake.hcl"
CPP26_IMAGE_CLANG_DOCKERFILE_PATH = CPP26_IMAGE_DIR / "Dockerfile.clang-p2996"
CPP26_IMAGE_CLANG_QUANTLIB_DOCKERFILE_PATH = CPP26_IMAGE_DIR / "Dockerfile.clang-p2996-quantlib"
CPP26_IMAGE_GCC_DOCKERFILE_PATH = CPP26_IMAGE_DIR / "Dockerfile.gcc-reflection"

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
    "codex_cli": "codex",
    "claude_code": "claude-code",
    "gemini_cli": "gemini-cli",
    "just": "just",
    "chezmoi": "chezmoi",
    "watchexec": "watchexec",
}

MISE_GLOBAL_CONFIG_PATH = Path.home() / ".config" / "mise"


class ToolingError(RuntimeError):
    """Raised when control-plane actions fail."""


class BaseImageSpec(TypedDict):
    image_ref: str
    dockerfile: Path
    build_args: dict[str, str]


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text())


def save_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n")


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


def template_context(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "tooling": {
            "channels": manifest["channels"],
            "pythonVersion": manifest["python_version"],
            "images": {
                key: {
                    **value,
                    "defaultRef": f"{value['repository']}:{value['default_tag']}",
                }
                for key, value in manifest["images"].items()
            },
            "cpp26DevImages": manifest["cpp26_dev_images"],
            "tools": manifest["tools"],
            "derived": {
                "nodeMajor": node_major(manifest),
                "llvmArchive": llvm_archive_name(manifest),
                "llvmDownloadUrl": llvm_download_url(manifest),
            },
        }
    }


def render_template(template_name: str, manifest: dict[str, Any]) -> str:
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise ToolingError(f"missing template: {template_path.relative_to(REPO_ROOT)}")

    with TemporaryDirectory(prefix="cpp-playground-chezmoi-") as temp_dir:
        source_dir = Path(temp_dir)
        data_dir = source_dir / ".chezmoidata"
        data_dir.mkdir(parents=True, exist_ok=True)
        tooling_data = json.dumps(template_context(manifest), indent=2) + "\n"
        (data_dir / "tooling.json").write_text(tooling_data)

        render_target = source_dir / template_name
        render_target.parent.mkdir(parents=True, exist_ok=True)
        render_target.write_text(template_path.read_text())

        return run(
            [
                "chezmoi",
                "execute-template",
                "--source",
                str(source_dir),
                "--file",
                str(render_target),
            ],
            capture=True,
            strip=False,
        )


def run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    capture: bool = False,
    strip: bool = True,
) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
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


def resolve_version(spec: dict[str, Any]) -> str:
    kind = spec["source"]["kind"]
    source = spec["source"]
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
    raise ToolingError(f"unsupported source kind: {kind}")


def refresh_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    updated = json.loads(json.dumps(manifest))
    for _tool_name, spec in updated["tools"].items():
        spec["version"] = resolve_version(spec)
    return updated


def render_mise_toml(manifest: dict[str, Any]) -> str:
    return render_template("mise.toml.tmpl", manifest)


def render_docker_bake_hcl(manifest: dict[str, Any]) -> str:
    return render_template("docker-bake.hcl.tmpl", manifest)


def render_devcontainer_json(manifest: dict[str, Any]) -> str:
    return render_template("devcontainer.json.tmpl", manifest)


def render_pixi_toml(manifest: dict[str, Any]) -> str:
    return render_template("pixi.toml.tmpl", manifest)


def render_cmake_presets(_: dict[str, Any]) -> str:
    return render_template("CMakePresets.json.tmpl", _)


def render_dockerfile(manifest: dict[str, Any]) -> str:
    return render_template("Dockerfile.tmpl", manifest)


def render_readme(manifest: dict[str, Any]) -> str:
    return render_template("README.md.tmpl", manifest)


def render_cpp26_image_docker_bake(manifest: dict[str, Any]) -> str:
    return render_template("cpp26-dev-images/docker-bake.hcl.tmpl", manifest)


def render_cpp26_image_clang_dockerfile(manifest: dict[str, Any]) -> str:
    return render_template("cpp26-dev-images/Dockerfile.clang-p2996.tmpl", manifest)


def render_cpp26_image_clang_quantlib_dockerfile(manifest: dict[str, Any]) -> str:
    return render_template("cpp26-dev-images/Dockerfile.clang-p2996-quantlib.tmpl", manifest)


def render_cpp26_image_gcc_dockerfile(manifest: dict[str, Any]) -> str:
    return render_template("cpp26-dev-images/Dockerfile.gcc-reflection.tmpl", manifest)


def sync_generated_files(manifest: dict[str, Any]) -> None:
    MISE_TOML_PATH.write_text(render_mise_toml(manifest))
    DOCKER_BAKE_PATH.write_text(render_docker_bake_hcl(manifest))
    DEVCONTAINER_JSON_PATH.write_text(render_devcontainer_json(manifest))
    PIXI_TOML_PATH.write_text(render_pixi_toml(manifest))
    CMAKE_PRESETS_PATH.write_text(render_cmake_presets(manifest))
    DOCKERFILE_PATH.write_text(render_dockerfile(manifest))
    README_PATH.write_text(render_readme(manifest))
    CPP26_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    CPP26_IMAGE_DOCKER_BAKE_PATH.write_text(render_cpp26_image_docker_bake(manifest))
    CPP26_IMAGE_CLANG_DOCKERFILE_PATH.write_text(render_cpp26_image_clang_dockerfile(manifest))
    CPP26_IMAGE_CLANG_QUANTLIB_DOCKERFILE_PATH.write_text(
        render_cpp26_image_clang_quantlib_dockerfile(manifest)
    )
    CPP26_IMAGE_GCC_DOCKERFILE_PATH.write_text(render_cpp26_image_gcc_dockerfile(manifest))


def ensure_file_matches(path: Path, expected: str) -> None:
    actual = path.read_text()
    if actual != expected:
        raise ToolingError(f"{path.relative_to(REPO_ROOT)} is out of sync with the control plane")


def validate_repo(manifest: dict[str, Any]) -> None:
    ensure_file_matches(MISE_TOML_PATH, render_mise_toml(manifest))
    ensure_file_matches(DOCKER_BAKE_PATH, render_docker_bake_hcl(manifest))
    ensure_file_matches(DEVCONTAINER_JSON_PATH, render_devcontainer_json(manifest))
    ensure_file_matches(PIXI_TOML_PATH, render_pixi_toml(manifest))
    ensure_file_matches(CMAKE_PRESETS_PATH, render_cmake_presets(manifest))
    ensure_file_matches(DOCKERFILE_PATH, render_dockerfile(manifest))
    ensure_file_matches(README_PATH, render_readme(manifest))
    ensure_file_matches(CPP26_IMAGE_DOCKER_BAKE_PATH, render_cpp26_image_docker_bake(manifest))
    ensure_file_matches(
        CPP26_IMAGE_CLANG_DOCKERFILE_PATH, render_cpp26_image_clang_dockerfile(manifest)
    )
    ensure_file_matches(
        CPP26_IMAGE_CLANG_QUANTLIB_DOCKERFILE_PATH,
        render_cpp26_image_clang_quantlib_dockerfile(manifest),
    )
    ensure_file_matches(
        CPP26_IMAGE_GCC_DOCKERFILE_PATH, render_cpp26_image_gcc_dockerfile(manifest)
    )

    dockerfile = DOCKERFILE_PATH.read_text()
    mise_toml = MISE_TOML_PATH.read_text()
    docker_bake = DOCKER_BAKE_PATH.read_text()
    for forbidden in ('"latest"', "=latest", "NODE_MAJOR=22", 'default = "22"'):
        if forbidden in dockerfile or forbidden in mise_toml or forbidden in docker_bake:
            raise ToolingError(f"forbidden stale or floating version token detected: {forbidden}")

    if "docker-buildx-plugin" not in dockerfile or "docker-ce-cli" not in dockerfile:
        raise ToolingError(
            "Dockerfile must explicitly install docker-ce-cli and docker-buildx-plugin"
        )
    if "linux-tools-generic" not in dockerfile:
        raise ToolingError("Dockerfile must explicitly install linux-tools-generic")

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

    mise_data = tomllib.loads(MISE_TOML_PATH.read_text())
    mise_tools = mise_data.get("tools")
    if not isinstance(mise_tools, dict):
        raise ToolingError("mise.toml must define a [tools] table")

    expected_mise_tools = {
        MISE_NATIVE_TOOL_ALIASES["node"]: version_of(manifest, "node"),
        MISE_NATIVE_TOOL_ALIASES["python"]: manifest_python_version(manifest),
        MISE_NATIVE_TOOL_ALIASES["uv"]: version_of(manifest, "uv"),
        MISE_NATIVE_TOOL_ALIASES["pixi"]: version_of(manifest, "pixi"),
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


def validate_runtime(manifest: dict[str, Any]) -> None:
    for cmd in NATIVE_VALIDATION_COMMANDS.values():
        run(cmd, capture=True)

    runtime_commands = dict(REQUIRED_RUNTIME_COMMANDS)
    checks = {
        "node": f"v{version_of(manifest, 'node')}",
        "mise": version_of(manifest, "mise"),
        "uv": version_of(manifest, "uv"),
        "pixi": version_of(manifest, "pixi"),
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
    print("  python3 -m tooling validate --mode all")
    print("  pixi run prove-devcontainer")
    print("  smoke-reflection")


def manifest_python_version(manifest: dict[str, Any]) -> str:
    return str(manifest["python_version"])


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
    if current_kernel_release() != version_of(manifest, "linux_kernel"):
        raise ToolingError(
            f"{surface} requires kernel {version_of(manifest, 'linux_kernel')}, "
            f"found {current_kernel_release()}"
        )
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


def build_devcontainer_image(image_tag: str) -> None:
    manifest = load_manifest()
    image_config = manifest["cpp26_dev_images"]
    platform_name = str(image_config.get("platform_default", "linux/amd64"))
    base_images: dict[str, BaseImageSpec] = {
        "clang": {
            "image_ref": f"{image_repo(manifest, 'cpp26_dev_clang')}:{image_tag}",
            "dockerfile": CPP26_IMAGE_CLANG_DOCKERFILE_PATH,
            "build_args": {
                "UBUNTU_VERSION": image_config["ubuntu_version"],
                "CLANG_P2996_REPO": image_config["clang_p2996_repo"],
                "CLANG_P2996_REF": image_config["clang_p2996_ref"],
                "VCPKG_BUNDLE_URL": image_config["vcpkg_bundle_url"],
            },
        },
        "gcc": {
            "image_ref": f"{image_repo(manifest, 'cpp26_dev_gcc')}:{image_tag}",
            "dockerfile": CPP26_IMAGE_GCC_DOCKERFILE_PATH,
            "build_args": {
                "UBUNTU_VERSION": image_config["ubuntu_version"],
                "GCC_REFLECTION_REPO": image_config["gcc_reflection_repo"],
                "GCC_REFLECTION_REF": image_config["gcc_reflection_ref"],
                "VCPKG_BUNDLE_URL": image_config["vcpkg_bundle_url"],
            },
        },
    }

    for spec in base_images.values():
        image_ref = spec["image_ref"]
        dockerfile = spec["dockerfile"]
        build_args = spec["build_args"]
        inspect = subprocess.run(
            ["docker", "image", "inspect", image_ref],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if inspect.returncode == 0:
            continue

        cmd = [
            "docker",
            "buildx",
            "build",
            "--platform",
            platform_name,
            "--load",
            "-f",
            str(dockerfile),
        ]
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])
        cmd.extend(["-t", image_ref, str(CPP26_IMAGE_DIR)])
        run(cmd)

    env = {
        "TAG": image_tag,
        "CLANG_BASE_IMAGE": f"{image_repo(manifest, 'cpp26_dev_clang')}:{image_tag}",
        "GCC_BASE_IMAGE": f"{image_repo(manifest, 'cpp26_dev_gcc')}:{image_tag}",
    }
    run(
        [
            "docker",
            "buildx",
            "bake",
            "dev",
            "--set",
            "dev.output=type=docker",
            "--set",
            "dev.cache-from=",
            "--set",
            "dev.cache-to=",
        ],
        env=env,
    )
    print(f"Built {image_repo(manifest, 'cpp_devcontainer')}:{image_tag}")


def print_devcontainer_env(image_ref: str) -> None:
    print(f"CPP_DEVCONTAINER_IMAGE={image_ref}")
    print("OPENAI_API_KEY=")
    print("ANTHROPIC_API_KEY=")
    print("GOOGLE_API_KEY=")
    print("GEMINI_API_KEY=")


def cmd_refresh(args: argparse.Namespace) -> None:
    manifest = load_manifest()
    refreshed = refresh_manifest(manifest)
    save_manifest(refreshed)
    sync_generated_files(refreshed)
    if not args.skip_locks:
        update_lockfiles()
    validate_repo(refreshed)


def cmd_sync_generated(_: argparse.Namespace) -> None:
    manifest = load_manifest()
    sync_generated_files(manifest)
    validate_repo(manifest)


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


def cmd_build_devcontainer_image(args: argparse.Namespace) -> None:
    build_devcontainer_image(args.image_tag)


def cmd_print_devcontainer_env(args: argparse.Namespace) -> None:
    print_devcontainer_env(args.image_ref)


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
        help="Re-render generated files from the checked-in manifest without refreshing pins",
    )
    sync_generated.set_defaults(func=cmd_sync_generated)

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

    build_image = subparsers.add_parser(
        "build-devcontainer-image",
        help="Build the wrapper devcontainer image",
    )
    build_image.add_argument("--image-tag", default=os.environ.get("IMAGE_TAG", "dev"))
    build_image.set_defaults(func=cmd_build_devcontainer_image)

    env_parser = subparsers.add_parser(
        "print-devcontainer-env",
        help="Print a .env template for the devcontainer image",
    )
    env_parser.add_argument("image_ref", nargs="?", default="cpp-devcontainer:dev")
    env_parser.set_defaults(func=cmd_print_devcontainer_env)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except ToolingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
