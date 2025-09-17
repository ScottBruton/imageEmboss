@echo off
echo 🚀 Starting ImageEmboss with FreeCAD Integration
echo ================================================
echo.
echo Using Python 3.11.9 virtual environment with FreeCAD 1.0 support
echo.

REM Activate virtual environment and run the application
venv_freecad\Scripts\python.exe main.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Application failed to start. Please check the error messages above.
    pause
)
