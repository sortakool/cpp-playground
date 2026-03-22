# Apple Silicon Devcontainer `amd64` Emulation Caveat

This repository's devcontainer proof surface is Linux `amd64`.

On Apple Silicon hosts, Docker Desktop may satisfy that requirement through `linux/amd64` emulation instead of a native Linux `amd64` Docker host. That path is not a reliable proof surface for the `llvm-tsan` lane.

## Failure Signature

If the devcontainer toolchain proof fails with:

```text
ThreadSanitizer: memory layout is incompatible
```

and the failing process memory map contains:

```text
/run/rosetta/rosetta
```

treat that as the Apple Silicon Docker Desktop emulation caveat tracked in [issue #1](https://github.com/sortakool/cpp-playground/issues/1), not as evidence that the repo's native Linux `amd64` ThreadSanitizer lane is broken.

## What To Do

- Prefer a native Linux `amd64` Docker host or VM for authoritative devcontainer proof.
- Do not relax or remove the `llvm-tsan` lane just because Docker Desktop emulation on Apple Silicon fails.
- Do not assume first-class `linux/arm64` support exists in this repo unless it is explicitly added and documented.

## Why This Is Narrow

- The current repo contract is still `linux/amd64` for the devcontainer proof surface.
- Docker documents Rosetta as the Apple Silicon `amd64` emulation path.
- Docker also documents Intel containers on Apple Silicon as best-effort under emulation and recommends native `arm64` when possible.
- The current blocker is therefore an upstream execution-surface caveat, not a proven repo-local sanitizer defect.
