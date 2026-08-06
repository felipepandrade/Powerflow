@echo off
setlocal
chcp 65001 > nul

python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.12 or newer is required.
    exit /b 1
)

if not exist ".venv" python -m venv .venv
if errorlevel 1 exit /b 1

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if errorlevel 1 exit /b 1

node --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 22 or newer is required.
    exit /b 1
)

call npm --prefix frontend ci
if errorlevel 1 exit /b 1

python -m alembic upgrade head
if errorlevel 1 exit /b 1

echo Powerflow environment is ready. Run start_powerflow.bat.
endlocal
