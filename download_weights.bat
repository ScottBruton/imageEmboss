@echo off
echo Downloading Model Weights for ImageEmboss...
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

:: Check if required packages are installed
echo Checking required packages...
python -c "import segmentation_models_pytorch" 2>nul
if errorlevel 1 (
    echo segmentation-models-pytorch not found! Installing...
    pip install segmentation-models-pytorch==0.3.3
    if errorlevel 1 (
        echo Failed to install segmentation-models-pytorch!
        pause
        exit /b 1
    )
)

:: Run the downloader
echo Starting model weights downloader...
python download_model_weights.py

:: Keep window open
pause
