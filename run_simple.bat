@echo off
echo Starting ImageEmboss Simplified...
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo Starting simplified version...
python main_simple.py

pause
