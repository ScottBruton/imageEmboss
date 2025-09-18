@echo off
echo Starting ImageEmboss Fixed Version...
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo Starting fixed version...
python main_fixed.py

pause
