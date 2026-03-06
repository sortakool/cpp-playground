#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SOURCE_SKILLS_ROOT="${SOURCE_SKILLS_ROOT:-/Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills}"
DEST_SKILLS_ROOT="${DEST_SKILLS_ROOT:-$HOME/.codex/skills}"
DRY_RUN=false

SKILLS=(
  "cpp26-dev-image-build"
  "cpp26-dev-image-publish"
  "cpp26-dev-image-validate"
)

TEMP_ROOT=""
BACKUP_STAMP="$(date +%Y%m%d%H%M%S)"

die() {
  echo "Error: $*" >&2
  exit 1
}

usage() {
  cat <<USAGE
Usage:
  $SCRIPT_NAME [--dry-run]

Options:
  --dry-run   Show planned sync actions without writing files.
  -h, --help  Show this help message.

Environment overrides:
  SOURCE_SKILLS_ROOT  Source repo skill directory.
                      Default: /Users/rmanaloto/dev/github/ray-manaloto/cpp-playground/.agents/skills
  DEST_SKILLS_ROOT    Target Codex skills directory.
                      Default: ~/.codex/skills

Safe copy behavior:
  - Stages copies in a temp directory first.
  - Backs up existing destination skill directories with a timestamp suffix.
  - Replaces only the 3 cpp26 image skill directories.
USAGE
}

run_cmd() {
  if "$DRY_RUN"; then
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

cleanup() {
  if ! "$DRY_RUN" && [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
    rm -rf "$TEMP_ROOT"
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown option: $1"
        ;;
    esac
  done
}

stage_skills() {
  local skill
  for skill in "${SKILLS[@]}"; do
    local src
    src="${SOURCE_SKILLS_ROOT}/${skill}"
    [[ -d "$src" ]] || die "Missing source skill directory: $src"

    local staged
    staged="${TEMP_ROOT}/${skill}"

    if "$DRY_RUN"; then
      echo "[dry-run] stage $src -> $staged"
      continue
    fi

    mkdir -p "$staged"
    rsync -a --delete "$src/" "$staged/"
  done
}

install_skills() {
  local skill
  for skill in "${SKILLS[@]}"; do
    local dest
    dest="${DEST_SKILLS_ROOT}/${skill}"

    if [[ -e "$dest" ]]; then
      local backup
      backup="${dest}.bak.${BACKUP_STAMP}"
      run_cmd mv "$dest" "$backup"
      echo "Backed up existing skill: $backup"
    fi

    if "$DRY_RUN"; then
      echo "[dry-run] install ${TEMP_ROOT}/${skill} -> $dest"
    else
      mv "${TEMP_ROOT}/${skill}" "$dest"
      echo "Installed skill: $dest"
    fi
  done
}

main() {
  parse_args "$@"

  command -v rsync >/dev/null 2>&1 || die "rsync is required"

  if "$DRY_RUN"; then
    TEMP_ROOT="${DEST_SKILLS_ROOT}/.cpp26-skill-sync.dry-run"
  else
    mkdir -p "$DEST_SKILLS_ROOT"
    TEMP_ROOT="$(mktemp -d "${DEST_SKILLS_ROOT}/.cpp26-skill-sync.XXXXXX")"
    trap cleanup EXIT
  fi

  stage_skills
  install_skills

  if ! "$DRY_RUN"; then
    rmdir "$TEMP_ROOT" 2>/dev/null || true
    TEMP_ROOT=""
  fi

  echo "Sync complete."
}

main "$@"
