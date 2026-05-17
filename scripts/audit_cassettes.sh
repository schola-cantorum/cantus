#!/usr/bin/env bash
# audit_cassettes.sh — secret-pattern scan for provider VCR cassettes.
#
# Extends the cantus-distribution Pre-push security audit (v0.2.0 follow-up
# scope) to cover the v0.2.1 cassette directory. Exits non-zero if any
# cassette under `tests/providers/cassettes/` contains a known
# authorization-material pattern.
#
# Usage:
#   ./scripts/audit_cassettes.sh            # scan default cassette glob
#   ./scripts/audit_cassettes.sh path/...   # scan a custom path
#
# Wire into pre-push:
#   cp scripts/audit_cassettes.sh .git/hooks/pre-push  (or call from existing hook)
#
# This script intentionally uses POSIX grep with -E so it runs on any platform
# without bash-specific assumptions beyond the shebang.

set -u

# Resolve the cassette root. Argument 1 wins; otherwise default to the canonical
# path used by the conftest fixture.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
DEFAULT_ROOT="${SCRIPT_DIR}/../tests/providers/cassettes"
ROOT="${1:-${DEFAULT_ROOT}}"

if [ ! -d "${ROOT}" ]; then
    # Cassette directory does not exist yet — clean exit. The pre-push hook
    # should not block when there is nothing to scan.
    echo "[audit_cassettes] no cassette directory at ${ROOT}; nothing to scan"
    exit 0
fi

# Patterns to block. Each pattern is a single ERE alternation member; they are
# joined with `|` below for one grep invocation.
PATTERNS=(
    'Authorization:'
    'Bearer '
    'x-api-key:'
    'api-key:'
    'x-goog-api-key:'
    'sk-[A-Za-z0-9]{20,}'
    'hf_[A-Za-z0-9]+'
    'ghp_[A-Za-z0-9]+'
    'AIza[A-Za-z0-9_-]{35}'
    'AKIA[A-Z0-9]{16}'
)

JOINED=""
for pat in "${PATTERNS[@]}"; do
    if [ -z "${JOINED}" ]; then
        JOINED="${pat}"
    else
        JOINED="${JOINED}|${pat}"
    fi
done

# Find all YAML cassettes recursively. -print0 + xargs -0 keeps spaces in paths
# safe, even though we don't expect any.
MATCHES="$(
    find "${ROOT}" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0 \
        | xargs -0 -r grep -EnH "${JOINED}" 2>/dev/null
)"

if [ -n "${MATCHES}" ]; then
    echo "[audit_cassettes] SECRET PATTERN(S) FOUND in cassette files:" >&2
    printf '%s\n' "${MATCHES}" >&2
    echo "" >&2
    echo "Re-record the offending cassettes with filter_headers configured" >&2
    echo "(see tests/providers/conftest.py). Push BLOCKED." >&2
    exit 1
fi

echo "[audit_cassettes] clean: no secret patterns found under ${ROOT}"
exit 0
