#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIO=""
OUTPUT_PATH=""
IMAGE_REF=""
PLATFORM="linux/amd64"

default_image_ref() {
  python3 - <<'PY'
import json
from pathlib import Path

cfg = json.loads(Path(".devcontainer/devcontainer.json").read_text())
print(cfg["image"])
PY
}

epoch_seconds() {
  python3 - <<'PY'
import time
print(time.time())
PY
}

usage() {
  cat <<USAGE
Usage: $0 --scenario <name> [--output <path>] [--image-ref <image>] [--platform <platform>]

Options:
  --scenario <name>    Benchmark scenario: cold | warm-repo-change | warm-devcontainer-change
  --output <path>      Output JSON path (default: benchmarks/devcontainer/runs/<run_id>.json)
  --image-ref <image>  Image tag to benchmark (default: .devcontainer/devcontainer.json image)
  --platform <value>   Build/smoke platform metadata (default: linux/amd64)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario)
      SCENARIO="${2:-}"
      shift 2
      ;;
    --output)
      OUTPUT_PATH="${2:-}"
      shift 2
      ;;
    --image-ref)
      IMAGE_REF="${2:-}"
      shift 2
      ;;
    --platform)
      PLATFORM="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$SCENARIO" ]]; then
  echo "--scenario is required" >&2
  usage
  exit 2
fi

case "$SCENARIO" in
  cold|warm-repo-change|warm-devcontainer-change) ;;
  *)
    echo "unsupported scenario: $SCENARIO" >&2
    usage
    exit 2
    ;;
esac

cd "$ROOT_DIR"

if [[ -z "$IMAGE_REF" ]]; then
  IMAGE_REF="$(default_image_ref)"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${SCENARIO}"
if [[ -z "$OUTPUT_PATH" ]]; then
  OUTPUT_PATH="benchmarks/devcontainer/runs/${RUN_ID}.json"
fi
mkdir -p "$(dirname "$OUTPUT_PATH")"

BUILD_START="$(epoch_seconds)"
docker buildx bake -f docker-bake.hcl devcontainer --load
BUILD_END="$(epoch_seconds)"

SIZE_START="$(epoch_seconds)"
SIZE_REPORT_JSON="$(./scripts/report-devcontainer-size.sh --image-ref "$IMAGE_REF" --platform "$PLATFORM")"
SIZE_END="$(epoch_seconds)"

if git diff --quiet && git diff --cached --quiet; then
  GIT_DIRTY="false"
else
  GIT_DIRTY="true"
fi

GIT_SHA="$(git rev-parse HEAD)"
RUNNER_NAME="${RUNNER_NAME:-${HOSTNAME:-unknown}}"
RUNNER_LABELS="${RUNNER_LABELS:-}"
DOCKER_VERSION="$(docker version --format '{{.Server.Version}}')"
BUILDX_VERSION="$(docker buildx version | awk '{print $2}')"

export RUN_ID GIT_SHA GIT_DIRTY RUNNER_NAME RUNNER_LABELS DOCKER_VERSION BUILDX_VERSION
export SCENARIO PLATFORM IMAGE_REF BUILD_START BUILD_END SIZE_START SIZE_END SIZE_REPORT_JSON OUTPUT_PATH

python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path


def float_seconds(start: str, end: str) -> float:
    return round(float(end) - float(start), 6)


runner_labels_raw = os.environ["RUNNER_LABELS"].strip()
runner_labels = [label for label in runner_labels_raw.split(",") if label]

size_report = json.loads(os.environ["SIZE_REPORT_JSON"])
timings = {
    "build_wall": float_seconds(os.environ["BUILD_START"], os.environ["BUILD_END"]),
    "size_report_wall": float_seconds(os.environ["SIZE_START"], os.environ["SIZE_END"]),
}

payload = {
    "schema_version": 1,
    "run_id": os.environ["RUN_ID"],
    "git_sha": os.environ["GIT_SHA"],
    "git_dirty": os.environ["GIT_DIRTY"] == "true",
    "runner_name": os.environ["RUNNER_NAME"],
    "runner_labels": runner_labels,
    "docker_version": os.environ["DOCKER_VERSION"],
    "buildx_version": os.environ["BUILDX_VERSION"],
    "scenario": os.environ["SCENARIO"],
    "platform": os.environ["PLATFORM"],
    "image_ref": os.environ["IMAGE_REF"],
    "timings_s": timings,
    "image_size_bytes": size_report["image_size_bytes"],
    "compressed_size_bytes": size_report["compressed_size_bytes"],
    "top_layers": size_report["top_layers"],
    "filesystem_sizes": size_report["filesystem_sizes"],
    "result": "pass",
}

output_path = Path(os.environ["OUTPUT_PATH"])
output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
print(str(output_path))
PY

