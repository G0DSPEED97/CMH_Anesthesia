#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -x "$PROJECT_DIR/backend/.venv/bin/python" ]] || python3 -m venv "$PROJECT_DIR/backend/.venv"
"$PROJECT_DIR/backend/.venv/bin/pip" install -q -r "$PROJECT_DIR/backend/requirements-dev.txt"
"$PROJECT_DIR/backend/.venv/bin/python" "$PROJECT_DIR/scripts/bootstrap_env.py"
set -a; source "$PROJECT_DIR/.env"; set +a
(cd "$PROJECT_DIR/frontend" && npm ci && npm run build)
(cd "$PROJECT_DIR/backend" && .venv/bin/alembic upgrade head && .venv/bin/python -m app.seed)
exec "$PROJECT_DIR/backend/.venv/bin/uvicorn" app.main:app --app-dir "$PROJECT_DIR/backend" --host 127.0.0.1 --port 8200 --reload
