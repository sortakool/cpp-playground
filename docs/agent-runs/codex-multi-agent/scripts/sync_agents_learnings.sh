#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MA_DIR="$ROOT_DIR/.codex/multi-agent"
RESULTS_DIR="$MA_DIR/results"
TARGET_FILE="$MA_DIR/AGENTS.md"
START_MARKER="<!-- BEGIN AUTO-LEARNINGS -->"
END_MARKER="<!-- END AUTO-LEARNINGS -->"

if [[ ! -f "$TARGET_FILE" ]]; then
  echo "missing target file: $TARGET_FILE" >&2
  exit 1
fi

learn_lines=()
shopt -s nullglob
for rf in "$RESULTS_DIR"/MA-*-result.md; do
  thread="$(basename "$rf" | sed -E 's/-result\.md$//')"
  section="$(awk '
    /^## Learnings[[:space:]]*$/ {in_section=1; next}
    /^## / && in_section {exit}
    in_section {print}
  ' "$rf")"

  if [[ -n "${section//[[:space:]]/}" ]]; then
    while IFS= read -r raw; do
      line="$(sed -E 's/^[[:space:]]+//' <<<"$raw")"
      [[ -z "$line" ]] && continue
      [[ "$line" == -* ]] || continue
      bullet="${line#- }"
      learn_lines+=("- [$thread] $bullet")
    done <<< "$section"
  fi
done

if [[ ${#learn_lines[@]} -eq 0 ]]; then
  learn_lines=("- No thread learnings captured yet.")
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

awk -v start="$START_MARKER" -v end="$END_MARKER" '
  $0 == start {print; in_block=1; next}
  $0 == end {in_block=0; print; next}
  !in_block {print}
' "$TARGET_FILE" > "$tmp_file"

# Rebuild with generated block content.
python3 - <<'PY' "$tmp_file" "$TARGET_FILE" "$START_MARKER" "$END_MARKER" "${learn_lines[@]}"
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text()
target = pathlib.Path(sys.argv[2])
start = sys.argv[3]
end = sys.argv[4]
lines = sys.argv[5:]

if start not in source or end not in source:
    raise SystemExit("missing auto-learning markers")

prefix, rest = source.split(start, 1)
_, suffix = rest.split(end, 1)
block = start + "\n" + "\n".join(lines) + "\n" + end

out = prefix + block + suffix
# normalize trailing newline
if not out.endswith("\n"):
    out += "\n"

target.write_text(out)
PY

echo "updated $TARGET_FILE"
