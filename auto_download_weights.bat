@echo off
echo Auto-downloading Model Weights...
echo This will download all model weights in advance for faster loading.
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

:: Run the auto downloader
echo Starting automatic weight download...
python auto_download_weights.py

echo.
echo Download complete! Press any key to exit...
pause >nul
