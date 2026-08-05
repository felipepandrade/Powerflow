@echo off
chcp 65001 > nul
echo ============================================================
echo   Powerflow — Inicializando Servidores e Aplicação
echo ============================================================
echo.

:: 1. Verificar se o venv existe
if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual .venv não encontrado.
    echo Por favor, execute 'setup_env.bat' primeiro para instalar o sistema.
    pause
    exit /b 1
)

:: 2. Ativar o venv
call .venv\Scripts\activate.bat

:: 3. Iniciar o Servidor Backend (FastAPI + Uvicorn)
echo [1/3] Iniciando Servidor Backend (API em http://127.0.0.1:8000)...
start "Powerflow Backend (API)" /min cmd /c ".venv\Scripts\python.exe -m uvicorn taskflow.main:app --host 127.0.0.1 --port 8000 --reload"

:: 4. Iniciar o Servidor Frontend (Vite)
echo [2/3] Iniciando Servidor Frontend (UI em http://localhost:5173)...
start "Powerflow Frontend (UI)" /min cmd /c "npm --prefix frontend run dev"

:: 5. Aguardar 3 segundos para inicialização dos serviços
echo [3/3] Aguardando inicialização dos serviços...
timeout /t 3 /nobreak > nul

:: 6. Abrir a aplicação no navegador padrão
echo.
echo ============================================================
echo   [OK] Servidores ativos! Abrindo o Powerflow no navegador...
echo   Frontend UI: http://localhost:5173
echo   Backend API: http://127.0.0.1:8000/docs
echo   Para encerrar, feche as janelas dos servidores em segundo plano.
echo ============================================================
echo.

start http://localhost:5173
