#!/usr/bin/env bash
# Creates a backup of the project before code-purge modifications.
# Usage: backup.sh [project_root] [--tar-only|--git-only]
# Output: prints backup location(s) to stdout

set -euo pipefail

PROJECT_ROOT="${1:-.}"
MODE="${2:-auto}"
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${PROJECT_ROOT}/.code-purge-backups"

cd "$PROJECT_ROOT"

mkdir -p "$BACKUP_DIR"

# ── Git stash backup ───────────────────────────────────────────────────────────
do_git_backup() {
  if git rev-parse --is-inside-work-tree &>/dev/null; then
    STASH_MSG="code-purge-backup-${TS}"
    # Stage everything so untracked files are included in the stash
    git add -A
    if git stash push --include-untracked -m "$STASH_MSG" 2>/dev/null; then
      STASH_REF=$(git stash list | grep "$STASH_MSG" | head -1 | cut -d: -f1)
      echo "git:${STASH_REF} (${STASH_MSG})"
      return 0
    fi
  fi
  return 1
}

# ── Tar backup ────────────────────────────────────────────────────────────────
do_tar_backup() {
  ARCHIVE="${BACKUP_DIR}/backup_${TS}.tar.gz"
  # Exclude common noise directories
  tar -czf "$ARCHIVE" \
    --exclude="./.git" \
    --exclude="./node_modules" \
    --exclude="./__pycache__" \
    --exclude="./.venv" \
    --exclude="./venv" \
    --exclude="./.code-purge-backups" \
    --exclude="./dist" \
    --exclude="./build" \
    -C "$(dirname "$PROJECT_ROOT")" \
    "$(basename "$PROJECT_ROOT")" 2>/dev/null || \
  tar -czf "$ARCHIVE" \
    --exclude=".git" \
    --exclude="node_modules" \
    --exclude="__pycache__" \
    --exclude=".venv" \
    --exclude="venv" \
    --exclude=".code-purge-backups" \
    --exclude="dist" \
    --exclude="build" \
    . 2>/dev/null
  echo "tar:${ARCHIVE}"
}

case "$MODE" in
  --git-only)  do_git_backup || { echo "ERROR: Not a git repo"; exit 1; } ;;
  --tar-only)  do_tar_backup ;;
  auto)
    # Prefer git stash; always also create tar as hard backup
    do_git_backup || true
    do_tar_backup
    ;;
esac
