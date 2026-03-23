# cpp-playground

Latest-tool and latest-kernel C++ development environment with a Linux `amd64` devcontainer, a root `Dockerfile`, and `docker buildx bake` as the build interface.

## Architecture

- One root `Dockerfile` with stages: `base`, `clang`, `gcc`, `final`, and `devcontainer`.
- `docker buildx bake` is the build and composition interface.
- `clang` and `gcc` images build in parallel from `base`.
- `devcontainer` is a thin wrapper over `final` and does not install tools.
- Dynamic username parity and SSH helper behavior remain enabled for devcontainer runtime.
- Root image defaults are snapshot-pinned `Ubuntu 25.10`; `Debian 13` is the alternate base option.

## Runtime Surfaces

- `devcontainer`: daily Linux `amd64` userspace and toolchain surface.
- `latest-kernel-vm`: local Linux `amd64` VM for kernel-sensitive evidence.
- `latest-kernel-ci`: self-hosted Linux `amd64` runner on the same latest-kernel policy.

## Command Surface

- `./install.sh` is the only checked-in shell bootstrap exception.
- Python helpers are intentionally minimal:
  - `finalize-bootstrap`
  - `verify run`
  - devcontainer runtime helpers (user/SSH lifecycle)
- The legacy Python orchestration layer is removed and not part of supported workflows.
- `pixi` is retained for locked environments and leaf checks only.
- `mise` remains the exact CLI pin layer, not the repo orchestration layer.

## Bootstrap And Verify

1. Build the image graph through Bake:

   ```bash
   docker buildx bake -f docker-bake.hcl devcontainer --load
   ```
2. Open or rebuild the devcontainer using the built `devcontainer` image.
3. Run bootstrap finalization:

   ```bash
   uv run finalize-bootstrap
   ```

4. Run repository verification:

   ```bash
   uv run verify run
   ```

For kernel-sensitive work, follow [docs/latest-kernel-testing.md](docs/latest-kernel-testing.md).

## Apple Silicon Caveat

- The authoritative devcontainer proof surface is Linux `amd64`, not Linux `arm64`.
- On Apple Silicon, Docker Desktop may execute `linux/amd64` under emulation.
- If the `llvm-tsan` lane fails with `ThreadSanitizer: memory layout is incompatible` and process maps contain `/run/rosetta/rosetta`, treat that as the known emulation caveat from [issue #1](https://github.com/sortakool/cpp-playground/issues/1), not as native Linux `amd64` regression evidence.
- Use a native Linux `amd64` Docker host or VM for authoritative devcontainer proof.

## Host Bootstrap Ownership

- `home/` is the `chezmoi` source root and uses `dot_` naming for managed targets.
- `chezmoi` owns host bootstrap state only; repo-generated artifacts remain outside host dotfile management.
