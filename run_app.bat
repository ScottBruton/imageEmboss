@echo off
echo Starting ImageEmboss Application...
echo.

:: Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found!
    echo Please run SetupEnvironment.bat first to create the environment.
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Check if PySide6 is installed
echo Checking PySide6 installation...
python -c "import PySide6" 2>nul
if errorlevel 1 (
    echo PySide6 not found! Installing...
    pip install "PySide6>=6.5.0"
    if errorlevel 1 (
        echo Failed to install PySide6!
        pause
        exit /b 1
    )
)

:: Run the application
echo Starting ImageEmboss...
python main.py

:: Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
