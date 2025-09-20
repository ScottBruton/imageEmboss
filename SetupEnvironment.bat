@echo off
setlocal enabledelayedexpansion

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with Administrator privileges...
) else (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: ====================================
:: Segmentation Models PyTorch (SMP) Installer with venv (Py 3.10)
:: ====================================
echo.
echo ====================================
echo Segmentation Models PyTorch (SMP) Installer with venv (Py 3.10)
echo ====================================

:: Paths
set PYTHON310="C:\Users\bruto\AppData\Local\Programs\Python\Python310\python.exe"
set VENV_DIR="%~dp0venv"

:: Initialize error logging
set "ERROR_LOG=%~dp0errorOutput.txt"

:: Clear and initialize the log file
echo Starting setup at %date% %time% > "!ERROR_LOG!"
echo ========================================== >> "!ERROR_LOG!"

:: =====================================================
:: Step 1: Setup Virtual Environment
:: =====================================================
echo.
echo ====================================
echo Setting up virtual environment...
echo ====================================
echo Starting virtual environment setup... >> "!ERROR_LOG!"

if exist %VENV_DIR% (
  echo Found existing venv. Activating it...
  echo Using existing virtual environment >> "!ERROR_LOG!"
) else (
  echo Creating new venv...
  echo Creating new virtual environment >> "!ERROR_LOG!"
  %PYTHON310% -m venv %VENV_DIR%
)

call %VENV_DIR%\Scripts\activate.bat
echo Virtual environment activated >> "!ERROR_LOG!"

:: Upgrade tools inside venv
echo Upgrading pip/setuptools/wheel in venv... >> "!ERROR_LOG!"
python -m pip install --upgrade pip setuptools wheel

:: =====================================================
:: Step 2: Detect GPU and Set CUDA Version
:: =====================================================
echo.
echo ====================================
echo Detecting GPU...
echo ====================================
echo Starting GPU detection... >> "!ERROR_LOG!"
powershell -command "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM"

for /f "tokens=*" %%i in ('powershell -command "(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like '*NVIDIA*' }).Name"') do set GPU_NAME=%%i
echo Detected GPU: %GPU_NAME%
echo GPU Detection completed - Found: %GPU_NAME% >> "!ERROR_LOG!"

:: =====================================================
:: Step 3: Install PyTorch with local wheel if available
:: =====================================================
echo.
echo ====================================
echo Installing PyTorch stack
echo ====================================
echo Starting PyTorch installation... >> "!ERROR_LOG!"

if exist "torch-2.1.2+cu118-cp310-cp310-win_amd64.whl" (
    echo Using local torch wheel file... >> "!ERROR_LOG!"
    echo Installing from local wheel file...
    python -m pip install torch-2.1.2+cu118-cp310-cp310-win_amd64.whl
    python -m pip install torchvision==0.16.2+cu118 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Downloading PyTorch from PyTorch repository... >> "!ERROR_LOG!"
    echo Installing from PyTorch repository...
    python -m pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
)

if errorlevel 1 (
    echo ERROR: PyTorch CUDA installation failed, trying CPU version... >> "!ERROR_LOG!"
    echo Trying CPU version...
    python -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
    if errorlevel 1 (
        echo ERROR: PyTorch CPU installation also failed >> "!ERROR_LOG!"
    ) else (
        echo PyTorch CPU installation completed >> "!ERROR_LOG!"
    )
) else (
    echo PyTorch CUDA installation completed >> "!ERROR_LOG!"
)

:: =====================================================
:: Step 4: Smart Package Installation
:: =====================================================
echo.
echo ====================================
echo Smart Package Installation
echo ====================================
echo Starting smart package installation... >> "!ERROR_LOG!"

:: Function to check and install package with version check
echo Creating package check function... >> "!ERROR_LOG!"

:: Check and fix NumPy first (critical for compatibility)
echo Checking NumPy version...
python -c "import numpy; print('NumPy version:', numpy.__version__)" 2>nul | findstr "2\." >nul
if not errorlevel 1 (
    echo NumPy 2.x detected, downgrading to 1.x...
    echo Downgrading NumPy to 1.x >> "!ERROR_LOG!"
    python -m pip uninstall numpy -y
    python -m pip install "numpy<2"
) else (
    echo NumPy 1.x already installed, checking version...
    python -c "import numpy; print('NumPy version:', numpy.__version__)"
)

:: Check and install packages only if needed
echo Checking opencv-python...
python -c "import cv2; print('OpenCV version:', cv2.__version__)" 2>nul | findstr "4.9.0.80" >nul
if errorlevel 1 (
    echo Installing opencv-python==4.9.0.80...
    python -m pip install opencv-python==4.9.0.80
) else (
    echo opencv-python==4.9.0.80 already installed
)

echo Checking shapely...
python -c "import shapely; print('Shapely version:', shapely.__version__)" 2>nul | findstr "2.0.4" >nul
if errorlevel 1 (
    echo Installing shapely==2.0.4...
    python -m pip install shapely==2.0.4
) else (
    echo shapely==2.0.4 already installed
)

echo Checking ezdxf...
python -c "import ezdxf; print('ezdxf version:', ezdxf.__version__)" 2>nul | findstr "1.1.1" >nul
if errorlevel 1 (
    echo Installing ezdxf==1.1.1...
    python -m pip install ezdxf==1.1.1
) else (
    echo ezdxf==1.1.1 already installed
)

echo Checking efficientnet_pytorch...
python -c "import efficientnet_pytorch; print('efficientnet_pytorch version:', efficientnet_pytorch.__version__)" 2>nul | findstr "0.7.1" >nul
if errorlevel 1 (
    echo Installing efficientnet_pytorch==0.7.1...
    python -m pip install efficientnet_pytorch==0.7.1
) else (
    echo efficientnet_pytorch==0.7.1 already installed
)

echo Checking timm...
python -c "import timm; print('timm version:', timm.__version__)" 2>nul | findstr "0.9.5" >nul
if errorlevel 1 (
    echo Installing timm==0.9.5...
    python -m pip install timm==0.9.5
) else (
    echo timm==0.9.5 already installed
)

echo Checking albumentations...
python -c "import albumentations; print('albumentations version:', albumentations.__version__)" 2>nul | findstr "1.3.1" >nul
if errorlevel 1 (
    echo Installing albumentations==1.3.1...
    python -m pip install albumentations==1.3.1
    echo Ensuring NumPy 1.x after albumentations...
    python -m pip install "numpy<2" --force-reinstall
) else (
    echo albumentations==1.3.1 already installed
)

echo Checking segmentation-models-pytorch (main package)...
python -c "import segmentation_models_pytorch as smp; print('SMP version:', smp.__version__)" 2>nul | findstr "0.3.3" >nul
if errorlevel 1 (
    echo Installing segmentation-models-pytorch==0.3.3...
    python -m pip install segmentation-models-pytorch==0.3.3
    echo Ensuring NumPy 1.x after SMP...
    python -m pip install "numpy<2" --force-reinstall
) else (
    echo segmentation-models-pytorch==0.3.3 already installed
)

echo Smart package installation completed >> "!ERROR_LOG!"

:: =====================================================
:: Step 5: Verify CUDA Installation
:: =====================================================
echo.
echo ====================================
echo Verifying CUDA Installation
echo ====================================
echo Verifying CUDA installation... >> "!ERROR_LOG!"

python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'N/A'); print('GPU count:', torch.cuda.device_count() if torch.cuda.is_available() else 0)"
if errorlevel 1 (
    echo ERROR: CUDA verification failed >> "!ERROR_LOG!"
) else (
    echo CUDA verification completed >> "!ERROR_LOG!"
)

:: =====================================================
:: Done
:: =====================================================
echo.
echo ====================================
echo Setup complete!
echo Active Python: %VENV_DIR%
echo Test with: python -c "import segmentation_models_pytorch as smp; print('SMP version:', smp.__version__)"
echo ====================================

echo ========================================== >> "!ERROR_LOG!"
echo Setup completed at %date% %time% >> "!ERROR_LOG!"
echo ========================================== >> "!ERROR_LOG!"

echo.
echo Error log saved to: "!ERROR_LOG!"
echo Check this file for installation status and any errors.

pause