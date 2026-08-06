@echo off
setlocal
chcp 65001 > nul

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Run setup_env.bat before starting Powerflow.
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m alembic upgrade head
if errorlevel 1 exit /b 1

start "Powerflow API" /min cmd /c ".venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8080 --reload"
start "Powerflow Worker" /min cmd /c ".venv\Scripts\python.exe -m apps.worker.main"
start "Powerflow Scheduler" /min cmd /c ".venv\Scripts\python.exe -m apps.worker.scheduler"
start "Powerflow Frontend" /min cmd /c "npm --prefix frontend run dev"

timeout /t 3 /nobreak > nul
echo Powerflow UI: http://localhost:5173
echo Powerflow API: http://127.0.0.1:8080/docs
start "" http://localhost:5173
endlocal
