@echo off
echo Starting ImageEmboss...
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing packages...
    python install_packages.py
)

echo.
echo Starting ImageEmboss application...
python main.py

pause
