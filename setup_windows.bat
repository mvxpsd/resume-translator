@echo off
echo 🚀 Initializing Resume Translator for Windows...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH. Please install Python from python.org
    pause
    exit /b
)

:: Create Virtual Environment
if not exist "venv_win" (
    echo 📦 Creating virtual environment...
    python -m venv venv_win
)

:: Activate Virtual Environment and Install Dependencies
echo ⬇️ Installing dependencies...
call venv_win\Scripts\activate

if exist "requirements.txt" (
    pip install -r requirements.txt
) else (
    echo ⚠️ requirements.txt not found. Creating default...
    (
        echo flask
        echo werkzeug
        echo deep-translator
        echo gunicorn
    ) > requirements.txt
    pip install -r requirements.txt
)

echo.
echo ✅ Setup complete! 
echo You can now use run_cli_windows.bat to translate files.
pause
