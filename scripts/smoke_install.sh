#!/usr/bin/env bash
# scripts/smoke_install.sh — tri-platform install smoke for cantus-agent.
#
# Reproduces the GitHub Actions cross-platform-install.yml job locally so
# contributors and students can verify install behaviour on their own machine
# (Linux / macOS / Windows via Git Bash or WSL).
#
# Usage:
#   bash scripts/smoke_install.sh              # install from the local working tree (uv pip install .)
#   bash scripts/smoke_install.sh 0.4.3        # install cantus-agent==0.4.3 from PyPI
#
# Exits non-zero on the first failing sub-step.

set -euo pipefail

VERSION="${1:-}"

if [ -n "$VERSION" ]; then
  CORE_SPEC="cantus-agent==${VERSION}"
  SERVE_OPENAI_SPEC="cantus-agent[serve,openai]==${VERSION}"
  RUNTIME_SPEC="cantus-agent[runtime]==${VERSION}"
else
  CORE_SPEC="."
  SERVE_OPENAI_SPEC=".[serve,openai]"
  RUNTIME_SPEC=".[runtime]"
fi

echo "==> Step 1: uv pip install --system ${CORE_SPEC}"
uv pip install --system "${CORE_SPEC}"

echo "==> Step 2: python -c \"from cantus import skill, Agent, load_chat_model\""
python -c "from cantus import skill, Agent, load_chat_model"

echo "==> Step 3: uv pip install --system ${SERVE_OPENAI_SPEC}"
uv pip install --system "${SERVE_OPENAI_SPEC}"

echo "==> Step 4: uv pip install --system ${RUNTIME_SPEC}"
uv pip install --system "${RUNTIME_SPEC}"

echo "==> Step 5: bitsandbytes presence assertion"
case "$(uname -s)" in
  Linux*)
    if ! uv pip list 2>/dev/null | grep -i '^bitsandbytes' > /dev/null; then
      echo "FAIL: bitsandbytes missing on Linux runtime extras" >&2
      exit 1
    fi
    echo "ok: bitsandbytes present on Linux"
    ;;
  Darwin*|MINGW*|MSYS*|CYGWIN*)
    if uv pip list 2>/dev/null | grep -i '^bitsandbytes' > /dev/null; then
      echo "FAIL: bitsandbytes unexpectedly present on $(uname -s)" >&2
      exit 1
    fi
    echo "ok: bitsandbytes absent on $(uname -s)"
    ;;
  *)
    echo "warn: skipping bitsandbytes assertion on unrecognised OS $(uname -s)"
    ;;
esac

echo "==> Smoke install OK"
