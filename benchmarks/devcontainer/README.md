# Devcontainer Benchmark Surface

This directory defines the V1 benchmark artifact contract for build/image measurements.

## Schema

- Schema file: `benchmarks/devcontainer/schema.json`
- Required fields include run metadata, timings, image sizes, top layers, filesystem footprints, and result status.

## Scripts

- Build benchmark runner:
  - `./scripts/benchmark-devcontainer-build.sh --scenario <cold|warm-repo-change|warm-devcontainer-change>`
- Size report only:
  - `./scripts/report-devcontainer-size.sh`

## Pixi Entry Points

- `pixi run benchmark-devcontainer-build -- --scenario cold`
- `pixi run report-devcontainer-size`

## Scenario Guidance

- `cold`: run after cache/builder reset for cold-path timing.
- `warm-repo-change`: warm-cache rebuild after a repo-only source change.
- `warm-devcontainer-change`: warm-cache rebuild after a `.devcontainer`-only change.

The benchmark script records exactly one scenario per run artifact under `benchmarks/devcontainer/runs/`.

## Decision Rule Reminder

Use paired runs on the same runner class and compare medians:

- Performance acceptance: at least `10%` or `300s` improvement, with no protected secondary metric regression greater than `5%`.
- Size acceptance: at least `5%` size improvement, with no build-time regression greater than `5%`.

If metadata differs across comparisons, discard the comparison as invalid.

