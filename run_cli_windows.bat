@echo off
setlocal enabledelayedexpansion

:: Check for environment
if not exist "venv_win" (
    echo ❌ Virtual environment not found. Please run setup_windows.bat first.
    pause
    exit /b
)

:: Get file path
if "%~1"=="" (
    echo.
    echo 📄 Drag and drop your French DOCX file here or type its path:
    set /p "source_file=Path: "
) else (
    set "source_file=%~1"
)

:: Clean quotes if user dragged and dropped
set "source_file=%source_file:"=%"

:: Run translation
echo.
echo ⏳ Starting translation...
venv_win\Scripts\python.exe run_translation_pipeline.py "!source_file!"

echo.
echo ✅ Process finished.
pause
