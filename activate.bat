@echo off
echo ====================================
echo Activating Virtual Environment
echo ====================================

:: Check if venv directory exists
if not exist "venv" (
    echo ERROR: Virtual environment directory 'venv' not found!
    echo Please run SetupEnvironment.bat first to create the virtual environment.
    echo.
    pause
    exit /b 1
)

:: Check if activation script exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment activation script not found!
    echo The virtual environment may be corrupted.
    echo Please delete the 'venv' folder and run SetupEnvironment.bat again.
    echo.
    pause
    exit /b 1
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Verify activation
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo.
    pause
    exit /b 1
)

echo.
echo ====================================
echo Virtual Environment Activated!
echo ====================================
echo.
echo You are now in the virtual environment.
echo Python path: %VIRTUAL_ENV%\Scripts\python.exe
echo.
echo To deactivate, type: deactivate
echo To check packages, run: python check_installations.py
echo.
echo Ready to use Segmentation Models PyTorch!
echo.

:: Keep the command prompt open
cmd /k
