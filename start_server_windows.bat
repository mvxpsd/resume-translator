@echo off
cd /d "%~dp0"
echo.
echo ========================================
echo   Resume Translator - Web Server
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from python.org
    pause
    exit /b
)

:: Check if virtual environment exists
if not exist "venv_win" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup_windows.bat first.
    pause
    exit /b
)

:: Activate virtual environment and start Flask server
echo [INFO] Starting Flask development server...
echo [INFO] Web app available at: http://localhost:5000
echo.
echo Press CTRL+C to stop the server
echo.

call venv_win\Scripts\activate && python app.py
