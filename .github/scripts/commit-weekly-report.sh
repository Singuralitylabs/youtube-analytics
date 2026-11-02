#!/usr/bin/env bash
# Commit a regenerated weekly report with a safe git order.
#
# Order (do not rearrange):
#   1) git add
#   2) git commit   (only when staged diff exists)
#   3) git pull --rebase
#   4) git push
#
# Pulling before add/commit fails when an already-tracked
# reports/weekly/YYYY-Www.md is overwritten (unstaged changes).
set -euo pipefail

TARGET_WEEK="${1:?usage: commit-weekly-report.sh YYYY-Www}"
REF_NAME="${2:-${GITHUB_REF_NAME:-main}}"
OUTPUT_VAR="${GITHUB_OUTPUT:-/dev/null}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

mkdir -p reports/weekly
git add reports/weekly/*.md

if git diff --staged --quiet; then
  echo "changed=false" >> "$OUTPUT_VAR"
  echo "コミット対象の変更なし"
  exit 0
fi

git commit -m "Add weekly insight report ${TARGET_WEEK}"
git pull --rebase origin "${REF_NAME}"
git push origin "HEAD:${REF_NAME}"
echo "changed=true" >> "$OUTPUT_VAR"
