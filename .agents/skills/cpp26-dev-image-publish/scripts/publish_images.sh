#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
DEFAULT_PUBLISH_REGISTRIES="ghcr.io/ray-manaloto,docker.io/raymanaloto"

TOOLCHAIN="all"
FLAVOR="core"
IMAGE_TAG=""
LATEST_TAG="latest"
PUBLISH_REGISTRIES="${PUBLISH_REGISTRIES:-$DEFAULT_PUBLISH_REGISTRIES}"
DRY_RUN=false

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME --image-tag <tag> [options]

Options:
  --toolchain clang|gcc|all   Toolchain set to publish (default: all)
  --flavor core|quantlib      Flavor to publish (default: core)
  --image-tag <tag>           Source and destination tag (required)
  --latest-tag <tag>          Additional rolling tag (default: latest, empty disables)
  --dry-run                   Print commands without executing
  -h, --help                  Show this help

Environment:
  PUBLISH_REGISTRIES  Comma-separated registry prefixes.
                      Default: ghcr.io/ray-manaloto,docker.io/raymanaloto
USAGE
}

die() {
  echo "Error: $*" >&2
  exit 1
}

run_cmd() {
  if "$DRY_RUN"; then
    printf '[dry-run]'; printf ' %q' "$@"; printf '\n'
    return 0
  fi
  "$@"
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --toolchain) TOOLCHAIN="$2"; shift 2 ;;
      --toolchain=*) TOOLCHAIN="${1#*=}"; shift ;;
      --flavor) FLAVOR="$2"; shift 2 ;;
      --flavor=*) FLAVOR="${1#*=}"; shift ;;
      --image-tag) IMAGE_TAG="$2"; shift 2 ;;
      --image-tag=*) IMAGE_TAG="${1#*=}"; shift ;;
      --latest-tag) LATEST_TAG="$2"; shift 2 ;;
      --latest-tag=*) LATEST_TAG="${1#*=}"; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1" ;;
    esac
  done
}

local_images_for() {
  local tc="$1"
  local fl="$2"
  if [[ "$tc" == "clang" && "$fl" == "quantlib" ]]; then
    printf 'cpp26-dev-clang-quantlib\n'
    return 0
  fi
  if [[ "$tc" == "clang" ]]; then
    printf 'cpp26-dev-clang\n'
    return 0
  fi
  if [[ "$tc" == "gcc" ]]; then
    printf 'cpp26-dev-gcc\n'
    return 0
  fi
  if [[ "$tc" == "all" && "$fl" == "quantlib" ]]; then
    printf 'cpp26-dev-clang-quantlib\n'
    printf 'cpp26-dev-gcc\n'
    return 0
  fi
  printf 'cpp26-dev-clang\n'
  printf 'cpp26-dev-gcc\n'
}

main() {
  parse_args "$@"

  [[ -n "$(trim "$IMAGE_TAG")" ]] || die "--image-tag is required"
  case "$TOOLCHAIN" in clang|gcc|all) ;; *) die "--toolchain must be clang, gcc, or all" ;; esac
  case "$FLAVOR" in core|quantlib) ;; *) die "--flavor must be core or quantlib" ;; esac

  command -v docker >/dev/null 2>&1 || die "docker is required"

  local -a regs=()
  local -a raw=()
  IFS=',' read -r -a raw <<< "$PUBLISH_REGISTRIES"
  for entry in "${raw[@]}"; do
    entry="$(trim "$entry")"
    [[ -n "$entry" ]] && regs+=("$entry")
  done
  [[ ${#regs[@]} -gt 0 ]] || die "No registries in PUBLISH_REGISTRIES"

  local -a local_images=()
  while IFS= read -r img; do
    [[ -n "$img" ]] && local_images+=("$img")
  done < <(local_images_for "$TOOLCHAIN" "$FLAVOR")

  if ! "$DRY_RUN"; then
    for local_image in "${local_images[@]}"; do
      docker image inspect "${local_image}:${IMAGE_TAG}" >/dev/null 2>&1 || die "Missing local image: ${local_image}:${IMAGE_TAG}"
    done
  fi

  for local_image in "${local_images[@]}"; do
    local src_ref="${local_image}:${IMAGE_TAG}"
    for reg in "${regs[@]}"; do
      local dst_ref="${reg}/${local_image}:${IMAGE_TAG}"
      run_cmd docker tag "$src_ref" "$dst_ref"
      run_cmd docker push "$dst_ref"

      if [[ -n "$LATEST_TAG" ]]; then
        local latest_ref="${reg}/${local_image}:${LATEST_TAG}"
        run_cmd docker tag "$src_ref" "$latest_ref"
        run_cmd docker push "$latest_ref"
      fi
    done
  done

  echo "Publish complete"
}

main "$@"
