# cpp-playground

Latest-tool and latest-kernel C++ development environment with a Linux `amd64` devcontainer, a root `Dockerfile`, and `docker buildx bake` as the build interface.

## Architecture

- One root `Dockerfile` with stages: `base`, `clang`, `gcc`, `final`, and `devcontainer`.
- `docker buildx bake` is the build and composition interface.
- `clang` and `gcc` images build in parallel from `base`.
- `devcontainer` is a thin wrapper over `final` and does not install tools.
- `final` and `devcontainer` carry both repo toolchains on `PATH`: `clang-p2996` and `gcc-reflection`.
- Dynamic username parity and SSH helper behavior remain enabled for devcontainer runtime.
- Root image defaults are snapshot-pinned `Ubuntu 25.10`; `Debian 13` is the alternate base option.

## Runtime Surfaces

- `devcontainer`: daily Linux `amd64` userspace and toolchain surface.
- `latest-kernel-vm`: local Linux `amd64` VM for kernel-sensitive evidence.
- `latest-kernel-ci`: self-hosted Linux `amd64` runner on the same latest-kernel policy.

## Command Surface

- `./install.sh` is the only checked-in shell bootstrap exception.
- `cpp-playground` is the canonical repo automation entrypoint:
  - `cpp-playground bootstrap ...`
  - `cpp-playground devcontainer ...`
  - `cpp-playground image ...`
  - `cpp-playground gha-fix-loop ...`
  - `cpp-playground verify run`
- `pixi` is retained for locked environments and leaf checks only.
- `mise` remains the exact CLI pin layer, not the repo orchestration layer.

## Bootstrap And Verify

1. Build the image graph through Bake:

   ```bash
   docker buildx bake -f docker-bake.hcl devcontainer --load
   ```
2. Open or rebuild the devcontainer using the built `devcontainer` image.

   For the repo-owned SSH runtime path, prefer:

   ```bash
   uv run cpp-playground devcontainer up --json
   ```

   This defaults to host port `3333`, removes prior repo-owned devcontainer instances first, and can be overridden with `--ssh-port`, `CPP_PLAYGROUND_DEVCONTAINER_SSH_PORT`, or `.devcontainer/devcontainer.env`.

3. Run bootstrap finalization:

   ```bash
   uv run cpp-playground bootstrap finalize
   ```

4. Run repository verification:

   ```bash
   uv run cpp-playground verify run
   ```

For kernel-sensitive work, follow [docs/latest-kernel-testing.md](docs/latest-kernel-testing.md).

## SSH Access

- SSH into the running devcontainer with `ssh -p 3333 ${USER}@127.0.0.1`.
- If your current host username already matches the devcontainer user, `ssh -p 3333 127.0.0.1` is equivalent.
- The host Mac SSH identities are used for authentication, but the SSH username still selects the Linux account inside the container.

## Authoritative Smoke And Benchmark Surface

- Hosted candidate publication and promotion live in:
  - `.github/workflows/devcontainer-build-hosted.yml`
- Required self-hosted source-build proof workflow:
  - `.github/workflows/devcontainer-authoritative-smoke.yml`
  - Runner contract: `self-hosted`, `Linux`, `X64`, `latest-kernel`
  - Required checks: bake build, published-image or source-build smoke, `uv run cpp-playground verify run`
- Repo-owned smoke entrypoint:

  ```bash
  uv run cpp-playground image smoke
  ```

- Devcontainer benchmark entrypoints:

  ```bash
  uv run cpp-playground image benchmark --scenario cold
  uv run cpp-playground image report-size --json
  ```

- Equivalent `pixi` leaf tasks:

  ```bash
  pixi run smoke-devcontainer-image
  pixi run benchmark-devcontainer-build -- --scenario cold
  pixi run report-devcontainer-size
  ```

- Benchmark artifacts are written against `benchmarks/devcontainer/schema.json`.

## Apple Silicon Caveat

- The authoritative devcontainer proof surface is Linux `amd64`, not Linux `arm64`.
- On Apple Silicon, Docker Desktop may execute `linux/amd64` under emulation.
- If the `llvm-tsan` lane fails with `ThreadSanitizer: memory layout is incompatible` and process maps contain `/run/rosetta/rosetta`, treat that as the known emulation caveat from [issue #1](https://github.com/sortakool/cpp-playground/issues/1), not as native Linux `amd64` regression evidence.
- Use a native Linux `amd64` Docker host or VM for authoritative devcontainer proof.

## Host Bootstrap Ownership

- `home/` is the `chezmoi` source root and uses `dot_` naming for managed targets.
- `chezmoi` owns host bootstrap state only; repo-generated artifacts remain outside host dotfile management.

## Historical Artifacts

- Archived multi-agent prompts, results, and notes live under `docs/agent-runs/`.
- Archived plan reviews live under `docs/plan-reviews/`.
- Archived superseded specs and plans live under `docs/archive/`.
