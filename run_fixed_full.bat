@echo off
echo Starting ImageEmboss Fixed Full Version...
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo Starting fixed full version...
python main_fixed_full.py

pause
