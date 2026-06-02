#!/usr/bin/env bash
# Regenerate TS types from the backend's OpenAPI schema.
#
# Usage:  pnpm gen:types
#
# Strategy: prefer a running backend on $MERCURY_PORT (default 8000). If none is
# reachable, boot uvicorn in the background for the duration of this script.

set -euo pipefail

PORT="${MERCURY_PORT:-8000}"
URL="http://127.0.0.1:${PORT}/openapi.json"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="${REPO_ROOT}/packages/shared-types/src/generated.ts"
BACKEND_DIR="${REPO_ROOT}/backend"
OPENAPI_CLI="$(echo "${REPO_ROOT}"/node_modules/.pnpm/openapi-typescript@*/node_modules/openapi-typescript/bin/cli.js)"

find_python() {
  if command -v uv >/dev/null 2>&1; then
    echo "uv"
    return
  fi
  if command -v py >/dev/null 2>&1; then
    echo "py"
    return
  fi
  if [[ -x "/mnt/c/Windows/py.exe" ]]; then
    echo "/mnt/c/Windows/py.exe"
    return
  fi
  echo "python"
}

find_node() {
  if command -v node >/dev/null 2>&1; then
    command -v node
    return
  fi
  if [[ -x "/mnt/d/Program Files/nodejs/node.exe" ]]; then
    echo "/mnt/d/Program Files/nodejs/node.exe"
    return
  fi
  if [[ -x "/mnt/c/Program Files/nodejs/node.exe" ]]; then
    echo "/mnt/c/Program Files/nodejs/node.exe"
    return
  fi
  echo "node"
}

to_host_path() {
  local value="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "${value}"
    return
  fi
  echo "${value}"
}

cleanup() {
  if [[ -n "${UVICORN_PID:-}" ]]; then
    kill "${UVICORN_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if ! curl -fsS "${URL}" > /dev/null 2>&1; then
  echo "No backend detected on :${PORT}; starting uvicorn temporarily..."
  PYTHON_CMD="$(find_python)"
  if [[ "${PYTHON_CMD}" == "uv" ]]; then
    (cd "${BACKEND_DIR}" && uv run uvicorn app.main:app --host 127.0.0.1 --port "${PORT}") &
  else
    (cd "${BACKEND_DIR}" && "${PYTHON_CMD}" -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}") &
  fi
  UVICORN_PID=$!
  for _ in $(seq 1 30); do
    sleep 0.5
    curl -fsS "${URL}" > /dev/null 2>&1 && break
  done
fi

echo "Fetching schema from ${URL}"
"$(find_node)" "$(to_host_path "${OPENAPI_CLI}")" "${URL}" -o "$(to_host_path "${OUT}")"
echo "Wrote ${OUT}"
