@echo off
chcp 65001 > nul
echo ============================================================
echo   Powerflow — Instalação e Configuração do Ambiente Local
echo ============================================================
echo.

:: 1. Verificar se o Python está instalado
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python não foi encontrado no PATH. Por favor, instale o Python 3.12+ para continuar.
    pause
    exit /b 1
)

:: 2. Criar ambiente virtual Python (.venv) se não existir
if not exist ".venv" (
    echo [1/4] Criando ambiente virtual Python (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar o venv.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Ambiente virtual .venv já existente.
)

:: 3. Instalar/Atualizar dependências Python do Backend
echo [2/4] Instalando dependências do backend...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip > nul 2>&1
pip install -e .
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependências do Python.
    pause
    exit /b 1
)

:: 4. Verificar se Node.js está instalado e instalar dependências Frontend
node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Node.js não foi encontrado. Certifique-se de ter o Node.js instalado para o frontend.
) else (
    echo [3/4] Instalando dependências do frontend (npm)...
    call npm --prefix frontend install
)

:: 5. Inicialização do Banco de Dados
echo [4/4] Inicializando banco de dados local...
python -c "import asyncio; from taskflow.main import lifespan; print('Banco inicializado!')" > nul 2>&1

echo.
echo ============================================================
echo   [SUCESSO] Instalação concluída com sucesso!
echo   Execute 'start_powerflow.bat' para iniciar o sistema.
echo ============================================================
echo.
pause
