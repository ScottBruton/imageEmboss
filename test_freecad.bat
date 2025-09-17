@echo off
echo Testing FreeCAD integration...
call venv_freecad\Scripts\activate.bat
if exist venv_freecad\Scripts\python.exe (
    venv_freecad\Scripts\python.exe test_freecad_integration.py
) else (
    echo Error: Python executable not found in venv_freecad\Scripts.
    echo Please ensure the virtual environment is set up correctly.
)
pause
