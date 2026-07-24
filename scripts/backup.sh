#!/usr/bin/env bash
# Creates a backup of the project before code-purge modifications.
# Usage: backup.sh [project_root]
# Output: prints backup location(s) to stdout

set -euo pipefail

PROJECT_ROOT=$(realpath "${1:-.}")
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="${CODE_PURGE_BACKUP_ROOT:-${XDG_STATE_HOME:-${HOME}/.local/state}/code-purge}"
PROJECT_ID=$(printf '%s' "$PROJECT_ROOT" | sha256sum | cut -c1-12)
BACKUP_DIR="${BACKUP_ROOT}/$(basename "$PROJECT_ROOT")_${PROJECT_ID}_${TS}"
mkdir -p "$BACKUP_DIR"

# ── Tar backup ────────────────────────────────────────────────────────────────
do_tar_backup() {
  ARCHIVE="${BACKUP_DIR}/project.tar.gz"
  # Exclude common noise directories
  tar -czf "$ARCHIVE" \
    --exclude="./.git" \
    --exclude="./node_modules" \
    --exclude="./__pycache__" \
    --exclude="./.venv" \
    --exclude="./venv" \
    --exclude="./dist" \
    --exclude="./build" \
    -C "$PROJECT_ROOT" \
    .
  echo "tar:${ARCHIVE}"
}

do_git_metadata_backup() {
  if git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree &>/dev/null; then
    git -C "$PROJECT_ROOT" status --short >"${BACKUP_DIR}/status.txt"
    git -C "$PROJECT_ROOT" diff --binary >"${BACKUP_DIR}/working.patch"
    git -C "$PROJECT_ROOT" diff --cached --binary >"${BACKUP_DIR}/staged.patch"
    echo "git-metadata:${BACKUP_DIR}"
  fi
}

do_git_metadata_backup
do_tar_backup
