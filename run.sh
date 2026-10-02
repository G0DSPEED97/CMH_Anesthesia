#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) exec cmd.exe /d /s /c "call \"$(cygpath -w "$PROJECT_DIR/RUN_WINDOWS.bat")\"" ;;
esac

BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
PORT=8200

command -v npm >/dev/null 2>&1 || { echo "Node.js LTS and npm are required."; exit 1; }
PYTHON_BIN="$(command -v python3.12 || command -v python3.11 || command -v python3)"
"$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' || { echo "Python 3.11+ is required."; exit 1; }
"$PYTHON_BIN" "$PROJECT_DIR/scripts/bootstrap_env.py"
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

ensure_postgres() {
  if command -v pg_isready >/dev/null 2>&1 && pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1; then return; fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    command -v brew >/dev/null 2>&1 || { echo "Install Homebrew to provision PostgreSQL."; exit 1; }
    brew list --versions postgresql@17 >/dev/null 2>&1 || HOMEBREW_NO_AUTO_UPDATE=1 brew install postgresql@17
    export PATH="$(brew --prefix postgresql@17)/bin:$PATH"
    brew services start postgresql@17 >/dev/null
  elif [[ "$(uname -s)" == "Linux" ]]; then
    if ! command -v psql >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y postgresql postgresql-contrib; fi
    sudo systemctl enable --now postgresql
  else
    echo "Use RUN_WINDOWS.bat on Windows."; exit 1
  fi
  for _ in {1..40}; do pg_isready -h 127.0.0.1 -p 5432 >/dev/null 2>&1 && return; sleep 1; done
  echo "PostgreSQL did not become ready."; exit 1
}

admin_psql() { if [[ "$(uname -s)" == "Linux" ]]; then sudo -u postgres psql "$@"; else psql postgres "$@"; fi; }
ensure_postgres
admin_psql -v ON_ERROR_STOP=1 -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='cmh_anesthesia') THEN CREATE ROLE cmh_anesthesia LOGIN PASSWORD '$CMH_ANESTHESIA_POSTGRES_PASSWORD'; END IF; END \$\$;" >/dev/null
if ! admin_psql -tAc "SELECT 1 FROM pg_database WHERE datname='cmh_anesthesia'" | grep -q 1; then
  if [[ "$(uname -s)" == "Linux" ]]; then sudo -u postgres createdb -O cmh_anesthesia cmh_anesthesia; else createdb -O cmh_anesthesia cmh_anesthesia; fi
fi

[[ -x "$VENV_DIR/bin/python" ]] || "$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"
(cd "$FRONTEND_DIR" && npm ci && npm run build)
(cd "$BACKEND_DIR" && "$VENV_DIR/bin/alembic" upgrade head && "$VENV_DIR/bin/python" -m app.seed)

echo "CMH Anaesthesia: http://127.0.0.1:$PORT"
exec "$VENV_DIR/bin/uvicorn" app.main:app --app-dir "$BACKEND_DIR" --host 0.0.0.0 --port "$PORT"
