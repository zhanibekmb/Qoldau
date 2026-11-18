#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO_HOME="${HOME}/.cache/qoldau-sprint5-demo"
mkdir -p "$DEMO_HOME"

if /usr/sbin/lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1 || \
   /usr/sbin/lsof -nP -iTCP:3000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Ports 8000 or 3000 are already in use. Close the running Qoldau servers and retry."
  exit 1
fi

if [ -x "${HOME}/.local/node22/bin/node" ]; then
  export PATH="${HOME}/.local/node22/bin:$PATH"
fi
if [ -x "${HOME}/.local/bin/python3.12" ]; then
  PYTHON="${HOME}/.local/bin/python3.12"
else
  PYTHON="$(command -v python3.12 || true)"
fi
if [ -z "$PYTHON" ] || ! command -v node >/dev/null 2>&1; then
  echo "Python 3.12 and Node 22 are required. See README.md for setup."
  exit 1
fi

if [ ! -x "$DEMO_HOME/venv/bin/python" ]; then
  "$PYTHON" -m venv "$DEMO_HOME/venv"
fi
if [ ! -f "$DEMO_HOME/requirements-ready" ]; then
  "$DEMO_HOME/venv/bin/python" -m pip install -r "$ROOT/backend/requirements.txt"
  touch "$DEMO_HOME/requirements-ready"
fi
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm ci)
fi

export QOLDAU_DATABASE_URL="sqlite:///$DEMO_HOME/demo.db"
export QOLDAU_SCHEDULER_ENABLED=false
export QOLDAU_JOBS_INLINE=true
export QOLDAU_UPLOAD_DIR="$DEMO_HOME/uploads"
export QOLDAU_EXPORT_DIR="$DEMO_HOME/exports"
export QOLDAU_MODEL_DIR="$DEMO_HOME/models"
export NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

echo "Preparing isolated Sprint 5 demo data..."
(cd "$ROOT/backend" && "$DEMO_HOME/venv/bin/python" -m app.seed --reset --demo)

BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [ -z "$FRONTEND_PID" ] || kill "$FRONTEND_PID" 2>/dev/null || true
  [ -z "$BACKEND_PID" ] || kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$ROOT/backend" && exec "$DEMO_HOME/venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning --no-access-log) > "$DEMO_HOME/backend.log" 2>&1 &
BACKEND_PID=$!
for _ in $(seq 1 45); do
  if curl -fsS http://127.0.0.1:8000/api/ready >/dev/null 2>&1; then break; fi
  sleep 1
done
if ! curl -fsS http://127.0.0.1:8000/api/ready >/dev/null; then
  cat "$DEMO_HOME/backend.log"
  exit 1
fi

(cd "$ROOT/frontend" && exec npm run dev -- --hostname 127.0.0.1) > "$DEMO_HOME/frontend.log" 2>&1 &
FRONTEND_PID=$!
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:3000/login >/dev/null 2>&1; then break; fi
  sleep 1
done
if ! curl -fsS http://127.0.0.1:3000/login >/dev/null; then
  cat "$DEMO_HOME/frontend.log"
  exit 1
fi

echo "Qoldau Sprint 5 demo is ready at http://127.0.0.1:3000/login"
echo "Use the demo accounts listed in README.md. Keep this Terminal window open."
echo "Press Control-C after the presentation to stop both servers."
open http://127.0.0.1:3000/login
wait
