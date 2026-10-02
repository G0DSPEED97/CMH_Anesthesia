@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title CMH Anaesthesia Setup and Server

where py >nul 2>&1 || (
  where winget >nul 2>&1 || (echo Python 3.11+ is required. & pause & exit /b 1)
  winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
)
where node >nul 2>&1 || (
  where winget >nul 2>&1 || (echo Node.js LTS is required. & pause & exit /b 1)
  winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements
  set "PATH=%ProgramFiles%\nodejs;%PATH%"
)

py -3 scripts\bootstrap_env.py || goto :error
if not exist backend\.venv\Scripts\python.exe py -3 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt || goto :error
backend\.venv\Scripts\python.exe scripts\windows_postgres.py --setup || goto :error
for /f "usebackq tokens=1,* delims==" %%A in (".env") do if not "%%A"=="" if /I not "%%A"=="CMH_ANESTHESIA_DATABASE_URL" if /I not "%%A"=="CMH_ANESTHESIA_POSTGRES_PASSWORD" set "%%A=%%B"

pushd frontend
call npm ci || (popd & goto :error)
call npm run build || (popd & goto :error)
popd

backend\.venv\Scripts\python.exe scripts\windows_postgres.py alembic upgrade head || goto :error
backend\.venv\Scripts\python.exe scripts\windows_postgres.py app.seed || goto :error

echo.
echo CMH Anaesthesia is available on this PC at http://127.0.0.1:8200
echo Other approved LAN PCs should use http://SERVER-PC-IP:8200
echo Keep this window open while the system is in use.
backend\.venv\Scripts\python.exe scripts\windows_postgres.py uvicorn app.main:app --host 0.0.0.0 --port 8200
exit /b %ERRORLEVEL%

:error
echo.
echo Setup stopped because a required step failed. Existing data was not deleted.
pause
exit /b 1
