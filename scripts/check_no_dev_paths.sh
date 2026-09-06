#!/usr/bin/env bash
# check_no_dev_paths.sh — repo-hygiene guard against dev-environment paths.
#
# Enforces the cantus-distribution requirement "CI enforces no
# development-environment path leakage": scans every git-tracked file for an
# absolute home path and fails if any are present.
#
# It carries a second, narrower group for ADR-0003: credential shapes inside the
# documentation site. A page's expected-output block is committed stdout, so a
# reader who pastes a real session into one would commit the token with it.
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
#   0  clean — no development-environment path, and no credential shape in the
#      documentation site, in tracked files
#   1  one or more leaks found (each printed as file:line)
#   2  usage / environment error (e.g. not inside a git work tree)

set -euo pipefail

PATTERN='/Users/[A-Za-z]|/home/[A-Za-z]'

# Second group (ADR-0003), applied ONLY to SITE_PATHS. Each shape is
# entropy-qualified — a length floor on the random part — so the bare prefixes
# that documentation legitimately names ("send an `sk-` prefixed key",
# "Authorization: Bearer <token>") are not findings.
#
# The scope is load-bearing. Fake tokens live on purpose in this repository's
# own fixtures (tests/test_audit_cassettes.py) and in archived planning
# documents; a repo-wide credential scan would fail on them, and a guard that
# fails on legitimate content is a guard someone switches off.
#
# Two known limits, deliberate rather than overlooked. The shapes are the ones
# the design fixed, and widening them is a decision with its own trade-off:
#   - Prefixed variants escape: sk-proj-..., sk-ant-api03-... and github_pat_...
#     all break the alphanumeric run right after the prefix. Catching them means
#     admitting a hyphen into the run, which widens the false-positive surface.
#   - A named placeholder can be a false positive: "Bearer YOUR_SERVE_TOKEN" is
#     24 characters from the class and would be reported. Write a placeholder as
#     "Bearer <token>" or "Bearer $VAR", the way the pages that document bearer
#     authentication already do.
TOKEN_PATTERN='sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{36}|Bearer [A-Za-z0-9._-]{20,}'
# An array, so adding a second directory stays two pathspecs rather than
# silently becoming one pathspec that matches nothing.
SITE_PATHS=(docs/site)

# The scan covers tracked files only, so it must run inside a git work tree.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[check_no_dev_paths] not inside a git work tree; nothing to scan" >&2
    exit 2
fi

# git grep exit codes: 0 = match found, 1 = no match, >1 = real error.
# A clean tree (no match) returns 1, which is our SUCCESS case — so we must
# capture the status explicitly rather than let `set -e` abort on it. An
# unmatched pathspec is also just "no match", so the site group is silent in a
# checkout that has no documentation site.
#
# Args: $1 the extended regex, $2... the pathspecs to scan.
# Leaves the matches in SCAN_RESULT; exits 2 if git grep itself failed.
#
# The result travels in a global rather than on stdout on purpose. Reading it
# through "$(scan ...)" would run the function in a subshell, where the `exit 2`
# below could only end that subshell — the git-grep-failure contract would then
# hold by accident, through `set -e` tripping on the assignment, and would
# disappear the moment a caller wrapped the call in an `if`.
SCAN_RESULT=""
scan() {
    local pattern="$1"
    shift
    local status
    set +e
    SCAN_RESULT="$(git grep -nE "${pattern}" -- "$@")"
    status=$?
    set -e
    if [ "${status}" -gt 1 ]; then
        echo "[check_no_dev_paths] git grep failed (exit ${status})" >&2
        exit 2
    fi
}

scan "${PATTERN}" .
PATH_MATCHES="${SCAN_RESULT}"
scan "${TOKEN_PATTERN}" "${SITE_PATHS[@]}"
TOKEN_MATCHES="${SCAN_RESULT}"

if [ -n "${PATH_MATCHES}" ]; then
    echo "[check_no_dev_paths] DEVELOPMENT-ENVIRONMENT PATH(S) FOUND in tracked files:" >&2
    printf '%s\n' "${PATH_MATCHES}" >&2
    echo "" >&2
    echo "Remove absolute home paths (/Users/<name>, /home/<name>) before committing." >&2
fi

if [ -n "${TOKEN_MATCHES}" ]; then
    echo "[check_no_dev_paths] CREDENTIAL SHAPE(S) FOUND under ${SITE_PATHS}/:" >&2
    printf '%s\n' "${TOKEN_MATCHES}" >&2
    echo "" >&2
    echo "A documentation page must not carry a real key, token or bearer value." >&2
    echo "Replace it with a placeholder before committing." >&2
fi

if [ -n "${PATH_MATCHES}" ] || [ -n "${TOKEN_MATCHES}" ]; then
    exit 1
fi

echo "[check_no_dev_paths] clean: no development-environment paths in tracked files,"
echo "[check_no_dev_paths] and no credential shapes under ${SITE_PATHS[*]}/"
exit 0
