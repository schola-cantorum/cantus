#!/usr/bin/env bash
# check_no_dev_paths.sh — repo-hygiene guard against dev-environment paths.
#
# Enforces the cantus-distribution requirement "CI enforces no
# development-environment path leakage": scans every git-tracked file for an
# absolute home path and fails if any are present.
#
#   macOS home : /Users/<name>   (a letter follows the final slash)
#   Linux home : /home/<name>    (a letter follows the final slash)
#
# The detection pattern requires an ALPHABETIC character immediately after
# "/Users/" or "/home/". This deliberately ignores the spec's own definitional
# tokens — the placeholder "/Users/<name>" (a "<" follows the slash) and the
# documented command grep -rn "/Users/" (a quote follows the slash) — so the
# guard never flags the documentation that defines it.
#
# Usage:
#   ./scripts/check_no_dev_paths.sh        # scan git-tracked files (no args)
#
# Wire into pre-commit / pre-push:
#   handled by .pre-commit-config.yaml and .github/workflows/repo-hygiene.yml
#
# Exit codes:
#   0  clean — no development-environment path in tracked files
#   1  one or more leaks found (each printed as file:line)
#   2  usage / environment error (e.g. not inside a git work tree)

set -euo pipefail

PATTERN='/Users/[A-Za-z]|/home/[A-Za-z]'

# The scan covers tracked files only, so it must run inside a git work tree.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[check_no_dev_paths] not inside a git work tree; nothing to scan" >&2
    exit 2
fi

# git grep exit codes: 0 = match found, 1 = no match, >1 = real error.
# A clean tree (no match) returns 1, which is our SUCCESS case — so we must
# capture the status explicitly rather than let `set -e` abort on it.
set +e
MATCHES="$(git grep -nE "${PATTERN}" -- .)"
STATUS=$?
set -e

if [ "${STATUS}" -gt 1 ]; then
    echo "[check_no_dev_paths] git grep failed (exit ${STATUS})" >&2
    exit 2
fi

if [ -n "${MATCHES}" ]; then
    echo "[check_no_dev_paths] DEVELOPMENT-ENVIRONMENT PATH(S) FOUND in tracked files:" >&2
    printf '%s\n' "${MATCHES}" >&2
    echo "" >&2
    echo "Remove absolute home paths (/Users/<name>, /home/<name>) before committing." >&2
    exit 1
fi

echo "[check_no_dev_paths] clean: no development-environment paths in tracked files"
exit 0
