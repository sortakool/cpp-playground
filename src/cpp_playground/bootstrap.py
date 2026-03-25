from __future__ import annotations

import argparse
import os
import platform
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from shutil import which

from .common import CppPlaygroundError, print_json, repo_root, run, run_in_pty

CHEZMOI_VERSION_FILE = ".chezmoiversion"
HOME_SOURCE_DIR = "home"
MISE_TEMPLATE = "home/.chezmoitemplates/mise-bootstrap.sh.tmpl"


def default_bin_dir() -> Path:
    if os.environ.get("BIN_DIR"):
        return Path(os.environ["BIN_DIR"])
    if os.access("/usr/local/bin", os.W_OK) or (
        not Path("/usr/local/bin").exists() and os.access("/usr/local", os.W_OK)
    ):
        return Path("/usr/local/bin")
    return Path.home() / ".local" / "bin"


def install_env() -> dict[str, str]:
    bin_dir = default_bin_dir()
    bin_dir.mkdir(parents=True, exist_ok=True)
    path_entries = os.environ.get("PATH", "").split(":")
    if str(bin_dir) not in path_entries:
        path_entries = [str(bin_dir), *filter(None, path_entries)]
    env = os.environ.copy()
    env["PATH"] = ":".join(path_entries)
    env["CPP_PLAYGROUND_REPO_ROOT"] = str(repo_root())
    return env


def managed_env() -> dict[str, str]:
    env = install_env()
    env.setdefault("MISE_IGNORED_CONFIG_PATHS", str(Path.home() / ".config" / "mise"))
    if "MISE_GLOBAL_CONFIG_FILE" not in env:
        if env.get("MISE_STATE_DIR"):
            state_dir = Path(env["MISE_STATE_DIR"])
        elif env.get("XDG_STATE_HOME"):
            state_dir = Path(env["XDG_STATE_HOME"]) / "cpp-playground-mise"
        else:
            state_dir = Path.home() / ".local" / "state" / "cpp-playground-mise"
        state_dir.mkdir(parents=True, exist_ok=True)
        global_config = state_dir / "global-config.toml"
        global_config.touch(exist_ok=True)
        env["MISE_GLOBAL_CONFIG_FILE"] = str(global_config)
    return env


def command_available(name: str, env: dict[str, str]) -> bool:
    return which(name, path=env.get("PATH")) is not None


def resolve_command(name: str, env: dict[str, str]) -> Path | None:
    resolved = which(name, path=env.get("PATH"))
    return Path(resolved) if resolved else None


def resolve_hk_binary(env: dict[str, str]) -> str:
    resolved = run(["mise", "which", "hk"], env=env, check=False).stdout.strip()
    return resolved or "hk"


def install_hk_hooks(env: dict[str, str]) -> None:
    run_in_pty([resolve_hk_binary(env), "--no-progress", "install", "--mise"], env=env)


def git_worktree_available() -> bool:
    child = run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root(),
        check=False,
    )
    return child.returncode == 0


def download(url: str, output: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        output.write_bytes(response.read())


def chezmoi_platform() -> tuple[str, str]:
    os_name = platform.system()
    if os_name != "Linux":
        raise CppPlaygroundError(f"unsupported operating system: {os_name}")
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "linux", "amd64"
    if machine in {"aarch64", "arm64"}:
        return "linux", "arm64"
    raise CppPlaygroundError(f"unsupported architecture: {platform.machine()}")


def chezmoi_version() -> str:
    version = (repo_root() / CHEZMOI_VERSION_FILE).read_text(encoding="utf-8").strip()
    if not version:
        raise CppPlaygroundError("empty chezmoi version pin")
    return version


def install_chezmoi(env: dict[str, str], temp_dir: Path) -> Path:
    bin_dir = Path(env["PATH"].split(":")[0])
    destination = bin_dir / "chezmoi"
    version = chezmoi_version()
    os_name, arch = chezmoi_platform()
    archive_path = temp_dir / "chezmoi.tar.gz"
    url = (
        "https://github.com/twpayne/chezmoi/releases/download/"
        f"v{version}/chezmoi_{version}_{os_name}_{arch}.tar.gz"
    )
    download(url, archive_path)
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extract("chezmoi", path=temp_dir)
    extracted = temp_dir / "chezmoi"
    extracted.chmod(0o755)
    destination.write_bytes(extracted.read_bytes())
    destination.chmod(0o755)
    return destination


def render_mise_bootstrap(chezmoi_bin: Path, env: dict[str, str], temp_dir: Path) -> Path:
    output_path = temp_dir / "mise-bootstrap.sh"
    template_path = repo_root() / MISE_TEMPLATE
    child = run(
        [str(chezmoi_bin), "execute-template"],
        cwd=repo_root(),
        env=env,
        input=template_path.read_text(encoding="utf-8"),
    )
    output_path.write_text(child.stdout, encoding="utf-8")
    output_path.chmod(0o755)
    return output_path


def apply_chezmoi(chezmoi_bin: Path, env: dict[str, str]) -> None:
    run(
        [
            str(chezmoi_bin),
            "init",
            "--apply",
            f"--source={repo_root() / HOME_SOURCE_DIR}",
        ],
        env=env,
    )


def finalize_bootstrap() -> dict[str, str]:
    env = managed_env()
    run(["mise", "trust", "."], env=env)
    pixi_args = ["pixi", "install"]
    if (repo_root() / "pixi.lock").exists():
        pixi_args.append("--locked")
    run(pixi_args, env=env)
    uv_args = ["uv", "sync", "--group", "dev"]
    if (repo_root() / "uv.lock").exists():
        uv_args.insert(2, "--locked")
    run(uv_args, env=env)
    hooks_installed = False
    if command_available("hk", env) and git_worktree_available():
        install_hk_hooks(env)
        hooks_installed = True
    return {
        "repo_root": str(repo_root()),
        "pixi_lock": str((repo_root() / "pixi.lock").exists()).lower(),
        "uv_lock": str((repo_root() / "uv.lock").exists()).lower(),
        "hooks_installed": str(hooks_installed).lower(),
    }


def install_dotfiles() -> dict[str, str]:
    if "HOME" not in os.environ:
        raise CppPlaygroundError("HOME must be set")
    required_paths = [
        repo_root() / CHEZMOI_VERSION_FILE,
        repo_root() / "docker-bake.hcl",
        repo_root() / MISE_TEMPLATE,
    ]
    for path in required_paths:
        if not path.exists():
            raise CppPlaygroundError(f"missing required bootstrap path: {path}")

    env = install_env()
    with tempfile.TemporaryDirectory(prefix="cpp-playground-install.") as temp_root:
        temp_dir = Path(temp_root)
        chezmoi_bin = resolve_command("chezmoi", env)
        if chezmoi_bin is None or not command_available("mise", env):
            temp_chezmoi = install_chezmoi(env, temp_dir)
            mise_script = render_mise_bootstrap(temp_chezmoi, env, temp_dir)
            run([str(mise_script)], env=env)
            chezmoi_bin = resolve_command("chezmoi", env) or temp_chezmoi
        apply_chezmoi(chezmoi_bin, env)
    return finalize_bootstrap()


def install_hooks() -> dict[str, str]:
    env = managed_env()
    run(["mise", "trust", "."], env=env)
    if not git_worktree_available():
        raise CppPlaygroundError("git worktree is required to install hooks")
    if not command_available("hk", env):
        raise CppPlaygroundError("hk is required to install hooks")
    install_hk_hooks(env)
    return {"status": "installed"}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Bootstrap helpers for cpp-playground.")
    subparsers = root.add_subparsers(dest="command", required=True)

    install_dotfiles_parser = subparsers.add_parser(
        "install-dotfiles", help="Install chezmoi-managed dotfiles and finalize bootstrap."
    )
    install_dotfiles_parser.set_defaults(func=lambda _args: install_dotfiles())

    finalize_parser = subparsers.add_parser(
        "finalize", help="Install repo tools, Python envs, and hooks."
    )
    finalize_parser.set_defaults(func=lambda _args: finalize_bootstrap())

    hooks_parser = subparsers.add_parser("install-hooks", help="Install git hooks via hk.")
    hooks_parser.set_defaults(func=lambda _args: install_hooks())

    root.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = args.func(args)
    except CppPlaygroundError as exc:
        raise SystemExit(f"error: {exc}") from exc
    if args.json:
        print_json(result)
    else:
        print(f"bootstrap.{args.command}: ok")
    return 0
