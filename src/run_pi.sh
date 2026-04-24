#!/usr/bin/env bash
set -euo pipefail

# One-command launcher for Raspberry Pi testing.
# Starts:
# - .NET backend (Kestrel)
# - Python motor control service (FastAPI/uvicorn)
# - Python UI (Tk)
#
# Usage (from repo root):  ./src/run_pi.sh
# Or (from src/):         ./run_pi.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Bind Kestrel to all interfaces on the Pi so the UI (local or remote) can reach it.
: "${ASPNETCORE_URLS:=http://0.0.0.0:5000}"

# The base URL that run_all.py uses for readiness checks and that the UI uses to talk to the backend.
# If you are running the UI on another machine, set this to the Pi's LAN IP, e.g.:
#   BIOREACTOR_BACKEND_BASE_URL="http://192.168.1.50:5000"
: "${BIOREACTOR_BACKEND_BASE_URL:=http://127.0.0.1:5000}"

export ASPNETCORE_URLS
export BIOREACTOR_BACKEND_BASE_URL

exec python3 "${SCRIPT_DIR}/run_all.py"
