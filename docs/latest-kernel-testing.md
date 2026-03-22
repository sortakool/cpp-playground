# Latest-Kernel Testing

The devcontainer is the daily userspace environment. It does not own the kernel. Kernel-sensitive tests must run on a Linux `amd64` host or VM whose kernel matches the manifest exactly.

## Apple Silicon And Emulation

The repo's devcontainer surface is still `linux/amd64`. On Apple Silicon, Docker Desktop may provide that surface through emulation instead of a native Linux `amd64` host. That is not a supported proof path for sanitizer evidence in this repo.

If the devcontainer `llvm-tsan` lane fails with `ThreadSanitizer: memory layout is incompatible` and the process memory map contains `/run/rosetta/rosetta`, treat that as the Apple Silicon emulation caveat tracked in [issue #1](https://github.com/sortakool/cpp-playground/issues/1). Use a native Linux `amd64` Docker host or VM when you need authoritative `pixi run prove-devcontainer` proof.

## Required Host Contract

- architecture: `x86_64` / `amd64`
- operating system: Linux
- kernel release: `6.19.9`
- privileges: root for the eBPF lane
- repo state: checked-out repo with `mise`, `pixi`, and `chezmoi` installed

## Local VM Lane

1. Provision a Linux `amd64` VM and boot the exact stable kernel required by `tooling/tool-version-manifest.json`.
2. Clone the repo inside the VM.
3. Install the repo-managed tools:

   ```bash
   python3 -m tooling bootstrap
   python3 -m tooling validate --mode all
   ```

4. Verify the kernel:

   ```bash
   uname -r
   ```

5. Run the kernel suite as root:

   ```bash
   sudo python3 -m tooling prove --surface latest-kernel-vm
   ```

## CI Lane

The GitHub workflow targets a self-hosted runner labeled `latest-kernel`. GitHub-hosted runners are not suitable because they do not let this repo enforce the exact kernel release.

Runner requirements:

- labels: `self-hosted`, `Linux`, `X64`, `latest-kernel`
- root access for the workflow job
- kernel pinned to `6.19.9`
- Docker not required for the kernel suite

## What Gets Tested

- `shared_memory_smoke`: `memfd` and POSIX `shm`
- `epoll_smoke`: readiness notification using `eventfd`
- `io_uring_smoke`: raw `io_uring_setup` / `io_uring_enter`
- `ebpf_smoke`: eBPF map create/update/lookup through `bpf(2)`

Each test prints numeric metrics and exits non-zero on unsupported or misconfigured behavior.
