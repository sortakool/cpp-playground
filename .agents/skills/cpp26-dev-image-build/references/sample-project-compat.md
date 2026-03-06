# Sample Project Compatibility Notes

## mirror_bridge

- Works best with `clang-p2996` + libc++ reflection support.
- GCC reflection support is evolving and may fail on advanced splice/pack patterns.

## merton-market-maker

- Includes a dedicated Docker workflow in `cpp/` and a QuantLib dependency.
- Use `Dockerfile.clang-p2996-quantlib` variant when validating this workload.

## simdjson/p2996

- Uses pinned `clang-p2996` workflows and scripts in `p2996/`.
- Prefer exact lock pin updates over branch-head builds for reproducibility.
