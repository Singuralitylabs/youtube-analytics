#!/usr/bin/env bash
# Commit a generated report to a dedicated branch and open (or reuse) a PR.
#
# main is protected by a ruleset ("Changes must be made through a pull request"),
# so the bot cannot push to it directly. Instead we push report/<kind>-<label>
# and open a PR against the base branch. A human merges it.
#
# Order (do not rearrange):
#   1) git add
#   2) git commit   (only when staged diff exists)
#   3) git push     (branch, force: reruns overwrite the same report branch)
#   4) gh pr create (skipped when an open PR for the branch already exists)
#
# usage: commit-report-pr.sh <monthly|weekly> <label> <pathspec> [base-branch]
# env:   GH_TOKEN (required for gh), GITHUB_OUTPUT (optional)
set -euo pipefail

KIND="${1:?usage: commit-report-pr.sh <monthly|weekly> <label> <pathspec> [base]}"
LABEL="${2:?label required (YYYY-MM or YYYY-Www)}"
PATHSPEC="${3:?pathspec required (e.g. reports/*.md)}"
BASE="${4:-${GITHUB_REF_NAME:-main}}"
OUTPUT_VAR="${GITHUB_OUTPUT:-/dev/null}"
BRANCH="report/${KIND}-${LABEL}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# shellcheck disable=SC2086  # PATHSPEC is an intentional glob
git add ${PATHSPEC}

if git diff --staged --quiet; then
  echo "changed=false" >> "$OUTPUT_VAR"
  echo "コミット対象の変更なし"
  exit 0
fi

git checkout -B "${BRANCH}"
git commit -m "Add ${KIND} insight report ${LABEL}"
git push --force origin "${BRANCH}"

if [ -z "$(gh pr list --head "${BRANCH}" --base "${BASE}" --state open --json number --jq '.[0].number')" ]; then
  gh pr create \
    --head "${BRANCH}" \
    --base "${BASE}" \
    --title "Add ${KIND} insight report ${LABEL}" \
    --body "自動生成された ${KIND} レポート（${LABEL}）です。内容を確認してマージしてください。"
else
  echo "既存の open PR があるため作成をスキップ"
fi

echo "changed=true" >> "$OUTPUT_VAR"
echo "branch=${BRANCH}" >> "$OUTPUT_VAR"
