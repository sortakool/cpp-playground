# Latest-Kernel Testing

The devcontainer is the daily userspace surface. Kernel-sensitive proof must run on a native Linux `amd64` host or VM whose kernel matches the required release exactly.

## Apple Silicon And Emulation

The checked-in devcontainer surface is still `linux/amd64`. On Apple Silicon, Docker Desktop may provide that surface through emulation instead of a native Linux `amd64` host. That is not an authoritative proof path for sanitizer or kernel evidence in this repo.

If the devcontainer `llvm-tsan` lane fails with `ThreadSanitizer: memory layout is incompatible` and the process memory map contains `/run/rosetta/rosetta`, treat that as the Apple Silicon emulation caveat tracked in [issue #1](https://github.com/sortakool/cpp-playground/issues/1). Use a native Linux `amd64` Docker host or VM when you need authoritative devcontainer proof.

## Required Host Contract

- architecture: `x86_64` / `amd64`
- operating system: Linux
- kernel release: `6.19.9`
- privileges: root for the eBPF lane
- repo state: checked out, `mise install --locked` completed, and `pixi install --locked` completed

## Local VM Lane

1. Provision a Linux `amd64` VM and boot the exact stable kernel required by the repo.
2. Clone the repo inside the VM.
3. Install the pinned CLIs and locked helper environment:

   ```bash
   ./install.sh
   pixi install --locked
   ```

4. Configure and build the host kernel lane with the Pixi-managed GCC surface:

   ```bash
   pixi run -e gcc-stable cmake --preset gcc-stable
   pixi run -e gcc-stable cmake --build --preset gcc-stable
   ```

5. Verify the kernel:

   ```bash
   uname -r
   ```

6. Run the kernel-labeled tests as root:

   ```bash
   pixi run -e gcc-stable sudo --preserve-env=PATH,HOME ctest --test-dir out/build/gcc-stable --output-on-failure -L kernel
   ```

## CI Lane

The GitHub workflow targets a self-hosted runner labeled `latest-kernel`. GitHub-hosted runners are not suitable because they do not let this repo enforce the exact kernel release.

Runner requirements:

- labels: `self-hosted`, `Linux`, `X64`, `latest-kernel`
- root access for the workflow job
- kernel pinned to `6.19.9`
- `pixi install --locked` must succeed on the runner host

## What Gets Tested

- `shared_memory_smoke`: `memfd` and POSIX `shm`
- `epoll_smoke`: readiness notification using `eventfd`
- `io_uring_smoke`: raw `io_uring_setup` / `io_uring_enter`
- `ebpf_smoke`: eBPF map create/update/lookup through `bpf(2)`

Each test prints numeric metrics and exits non-zero on unsupported or misconfigured behavior.
