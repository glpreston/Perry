@echo off
REM run-app.bat - Activate venv and start the Streamlit app
REM Usage: run-app.bat [port]

SETLOCAL ENABLEDELAYEDEXPANSION

REM Default port
SET PORT=2000
IF NOT "%~1"=="" SET PORT=%~1

echo Starting Peacemaker Guild (Streamlit) on port %PORT%

REM If venv activation script exists, use it; otherwise create a venv
IF EXIST ".venv\Scripts\activate.bat" (
    echo Activating virtual environment .venv
    call ".venv\Scripts\activate.bat"
) ELSE (
    echo Virtual environment not found at .venv - creating one now
    python -m venv .venv
    echo Activating new virtual environment
    call ".venv\Scripts\activate.bat"
    echo Upgrading pip and installing requirements (if present)
    python -m pip install --upgrade pip
    IF EXIST "requirements.txt" (
        python -m pip install -r requirements.txt
    ) ELSE (
        echo requirements.txt not found - skipping dependency install
    )
)

REM Start Streamlit; this will run in the foreground until stopped
echo Running: python -m streamlit run app.py --server.port %PORT%
python -m streamlit run app.py --server.port %PORT%

ENDLOCAL

echo Streamlit exited. Press any key to close this window.
pause >nul
