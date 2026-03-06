#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  test_images.sh [options]

Options:
  --toolchain clang|gcc|all   Toolchain set to validate (default: all)
  --flavor core|quantlib      Image flavor (default: core)
  --image-tag <tag>           Image tag (default: dev)
  --registry-prefix <prefix>  Optional prefix, e.g. ghcr.io/ray-manaloto
  --dry-run                   Print commands without execution
  -h, --help                  Show this help
USAGE
}

log() { printf '[%s] %s\n' "$1" "$2"; }
fail() { log FAIL "$1"; exit 1; }

TOOLCHAIN="all"
FLAVOR="core"
IMAGE_TAG="dev"
REGISTRY_PREFIX=""
DRY_RUN=0
PASS_COUNT=0
FAIL_COUNT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --toolchain) TOOLCHAIN="$2"; shift 2 ;;
    --toolchain=*) TOOLCHAIN="${1#*=}"; shift ;;
    --flavor) FLAVOR="$2"; shift 2 ;;
    --flavor=*) FLAVOR="${1#*=}"; shift ;;
    --image-tag) IMAGE_TAG="$2"; shift 2 ;;
    --image-tag=*) IMAGE_TAG="${1#*=}"; shift ;;
    --registry-prefix) REGISTRY_PREFIX="$2"; shift 2 ;;
    --registry-prefix=*) REGISTRY_PREFIX="${1#*=}"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1" ;;
  esac
done

case "$TOOLCHAIN" in clang|gcc|all) ;; *) fail "--toolchain must be clang, gcc, or all" ;; esac
case "$FLAVOR" in core|quantlib) ;; *) fail "--flavor must be core or quantlib" ;; esac

if [[ "$DRY_RUN" -eq 0 ]]; then
  command -v docker >/dev/null 2>&1 || fail "docker is required"
fi

image_ref() {
  local name="$1"
  if [[ -n "$REGISTRY_PREFIX" ]]; then
    printf '%s/%s:%s' "$REGISTRY_PREFIX" "$name" "$IMAGE_TAG"
  else
    printf '%s:%s' "$name" "$IMAGE_TAG"
  fi
}

run_step() {
  local label="$1"; shift
  log INFO "RUN  ${label}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log INFO "DRY  $*"
    PASS_COUNT=$((PASS_COUNT + 1))
    return 0
  fi
  if "$@"; then
    log PASS "$label"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    log FAIL "$label"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

run_in_container() {
  local label="$1"
  local image="$2"
  local payload="$3"
  run_step "$label" docker run --rm --pull=never "$image" /usr/bin/env bash -lc "$payload"
}

reflection_payload() {
  local compile_cmd="$1"
  cat <<PAY
set -euo pipefail
cat >/tmp/reflection.cpp <<'CPP'
#include <meta>
int main() { return 0; }
CPP
${compile_cmd} /tmp/reflection.cpp -fsyntax-only
PAY
}

sanitizer_payload() {
  local compile_cmd="$1"
  cat <<PAY
set -euo pipefail
cat >/tmp/sanitizer.cpp <<'CPP'
#include <cstdint>
int main() {
  volatile int x = 42;
  volatile int y = 2;
  volatile int z = static_cast<int>(x / y);
  (void)z;
  return 0;
}
CPP
if ! ${compile_cmd} /tmp/sanitizer.cpp -fsyntax-only >/dev/null 2>&1; then
  echo "SKIP: sanitizer flags unavailable for this compiler"
  exit 0
fi
${compile_cmd} /tmp/sanitizer.cpp -o /tmp/sanitizer
/tmp/sanitizer
PAY
}

run_clang_checks() {
  local image_name="cpp26-dev-clang"
  if [[ "$FLAVOR" == "quantlib" ]]; then
    image_name="cpp26-dev-clang-quantlib"
  fi
  local image
  image="$(image_ref "$image_name")"
  log INFO "Image clang: $image"

  run_in_container \
    "clang reflection smoke (<meta>, -std=c++2c, -freflection, -freflection-latest)" \
    "$image" \
    "$(reflection_payload 'clang++ -std=c++2c -freflection -freflection-latest')"

  run_in_container \
    "clang sanitizer smoke (asan+ubsan)" \
    "$image" \
    "$(sanitizer_payload 'clang++ -std=c++2c -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer')"
}

run_gcc_checks() {
  if [[ "$FLAVOR" == "quantlib" ]]; then
    log INFO "quantlib flavor is clang-only; validating gcc core image"
  fi
  local image
  image="$(image_ref "cpp26-dev-gcc")"
  log INFO "Image gcc: $image"

  run_in_container \
    "gcc reflection smoke (<meta>, -std=c++26, -freflection)" \
    "$image" \
    "$(reflection_payload 'g++ -std=c++26 -freflection')"

  run_in_container \
    "gcc sanitizer smoke (asan+ubsan)" \
    "$image" \
    "$(sanitizer_payload 'g++ -std=c++26 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer')"
}

log INFO "toolchain=${TOOLCHAIN} flavor=${FLAVOR} image_tag=${IMAGE_TAG} registry_prefix=${REGISTRY_PREFIX:-<local>} dry_run=${DRY_RUN}"

if [[ "$TOOLCHAIN" == "clang" || "$TOOLCHAIN" == "all" ]]; then
  run_clang_checks
fi

if [[ "$TOOLCHAIN" == "gcc" || "$TOOLCHAIN" == "all" ]]; then
  run_gcc_checks
fi

log INFO "Summary: passed=${PASS_COUNT} failed=${FAIL_COUNT}"
[[ "$FAIL_COUNT" -eq 0 ]] || exit 1
log PASS "All selected checks passed"
