# cpp-playground

Latest-tool and latest-kernel C++ development environment with a Python control plane, a Linux `amd64` devcontainer, and explicit low-level kernel validation lanes.

## Baselines

- Node `v25.8.1` on the current/latest release channel
- Linux stable kernel `6.19.9`
- LLVM `22.1.1`
- GCC `15.2.0`
- `mise` `2026.3.10`
- `uv` `0.10.12`
- `pixi` `0.66.0`
- Codex CLI `0.116.0`
- Claude Code `2.1.81`
- Gemini CLI `0.34.0`
- `just` `1.47.1`
- `chezmoi` `2.70.0`
- `watchexec` `2.5.0`
- `include-what-you-use` `0.25` in the Linux `llvm-stable` pixi environment

## Execution Surfaces

- `devcontainer`: daily Linux `amd64` userspace environment with exact tool pins and reflection lanes.
- `latest-kernel-vm`: local interactive Linux VM pinned to the latest stable kernel for low-level validation.
- `latest-kernel-ci`: self-hosted Linux `amd64` CI runner pinned to the same kernel policy.

## Apple Silicon Host Caveat

- The repo's devcontainer proof path is pinned to `linux/amd64`; it is not a first-class `linux/arm64` surface today.
- On Apple Silicon, Docker Desktop reaches `linux/amd64` through emulation. That path is not a supported proof surface for the `llvm-tsan` lane because ThreadSanitizer can fail under emulation before repo code runs.
- If `pixi run prove-devcontainer` fails with `ThreadSanitizer: memory layout is incompatible` and the failing process maps `/run/rosetta/rosetta`, treat that as the Apple Silicon emulation caveat tracked in [issue #1](https://github.com/sortakool/cpp-playground/issues/1), not as evidence that the repo's native Linux `amd64` TSan lane is broken.
- For end-to-end devcontainer proof, prefer a native Linux `amd64` Docker host or VM.

## Control Plane

- `python3 -m tooling refresh`: query upstreams, rewrite exact pins, and refresh lockfiles.
- `python3 -m tooling sync-generated`: re-render generated files from the checked-in manifest without refreshing upstream pins.
- `python3 -m tooling bootstrap`: install the locked pixi environment, install repo-pinned `mise` tools without loading host-global `mise` config, sync the uv-managed Python dev environment, and install repo-managed helper CLIs.
- `python3 -m tooling validate --mode repo`: verify committed config stays aligned with the manifest.
- `python3 -m tooling validate --mode runtime`: run native tool verification commands first, then verify installed versions match the manifest.
- `python3 -m tooling prove --surface devcontainer`: run the locked userspace/toolchain matrix.
- `python3 -m tooling prove --surface latest-kernel-vm`: run the latest-kernel validation suite locally.
- `python3 -m tooling prove --surface latest-kernel-ci`: run the same kernel-sensitive suite on the CI runner.

## Validation Policy

- Prefer each tool's native validation or inspection command before repo-specific checks.
- `python3 -m tooling validate --mode runtime` starts with `mise doctor`, `pixi info`, `uv tool list`, and `docker buildx inspect`.
- Python quality gates run through `uv run` inside the project; pixi tasks are wrappers around the repo-owned uv environment.
- Prefer existing `mise` registry aliases such as `claude-code` and `gemini-cli` before backend-qualified selectors like `npm:` or `github:`.
- Repo control-plane `mise` operations isolate themselves from `~/.config/mise` so repo lock refreshes do not rewrite the host-global `mise.lock` or inherit host hooks by default.

## Tooling Split

- Python control plane owns upstream resolution, validation, and orchestration.
- chezmoi templates own the checked-in config file shapes.
- `mise` manages exact fast-moving CLIs.
- `pixi` owns the stable helper environments: `llvm-stable`, `gcc-stable`, and `toolchains-stable`.
- Image-managed exceptions are limited to `gcc-reflection` and `clang-p2996`.

## Kernel Coverage

The Linux kernel validation surface includes dedicated tests for:

- shared memory via `memfd` and POSIX `shm`
- `epoll`
- `io_uring`
- eBPF map operations

Each test prints numeric evidence and returns non-zero on unsupported or misconfigured host behavior.

## Bootstrap

1. Build or refresh the wrapper image:

   ```bash
   python3 -m tooling build-devcontainer-image
   ```

2. Open the repo as a devcontainer.

3. Bootstrap the locked user-space tools:

   ```bash
   python3 -m tooling bootstrap
   ```

4. Validate the checked-in state:

   ```bash
   python3 -m tooling validate --mode all
   ```

5. For kernel-sensitive work, use the VM/runner flow documented in [docs/latest-kernel-testing.md](docs/latest-kernel-testing.md).
