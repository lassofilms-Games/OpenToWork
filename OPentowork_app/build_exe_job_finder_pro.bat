@echo off
cd /d "%~dp0"
echo Installing requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 pause

echo Building EXE...
python -m PyInstaller --onefile --windowed --name JobFinderPro job_finder_pro.py
if errorlevel 1 pause

echo.
echo DONE. Your EXE is here:
echo %CD%\dist\JobFinderPro.exe
pause
