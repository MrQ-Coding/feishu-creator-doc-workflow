#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="feishu-creator-doc-workflow"
REPO_SLUG="MrQ-Coding/feishu-creator-doc-workflow"
DEFAULT_REF="main"

DEST_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
DEST_DIR="$DEST_ROOT/$SKILL_NAME"
TMP_DIR=""

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}

trap cleanup EXIT

download_and_extract() {
  local ref="$1"
  TMP_DIR="$(mktemp -d)"
  local archive="$TMP_DIR/skill.tar.gz"
  local source_dir="$TMP_DIR/source"

  mkdir -p "$source_dir"
  curl -fsSL "https://github.com/$REPO_SLUG/archive/refs/heads/$ref.tar.gz" -o "$archive"
  tar -xzf "$archive" -C "$source_dir"
  printf '%s\n' "$source_dir/$(basename "$REPO_SLUG")-$ref"
}

resolve_source_dir() {
  local script_dir=""
  script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  local local_root
  local_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"

  if [[ -f "$local_root/SKILL.md" ]]; then
    printf '%s\n' "$local_root"
    return
  fi

  download_and_extract "${1:-$DEFAULT_REF}"
}

main() {
  local ref="${1:-$DEFAULT_REF}"
  local source_dir
  source_dir="$(resolve_source_dir "$ref")"

  mkdir -p "$DEST_ROOT"
  rm -rf "$DEST_DIR"
  mkdir -p "$DEST_DIR"
  cp -R "$source_dir"/. "$DEST_DIR"/
  rm -rf "$DEST_DIR/.git"
  rm -f "$DEST_DIR/README.md"

  printf 'Installed %s to %s\n' "$SKILL_NAME" "$DEST_DIR"
  printf 'Restart Codex to pick up the updated skill.\n'
}

main "$@"
