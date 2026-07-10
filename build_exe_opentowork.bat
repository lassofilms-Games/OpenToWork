@echo off
cd /d "%~dp0"
echo Installing requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 pause

echo Building EXE...
python -m PyInstaller OpenToWork.spec --noconfirm
if errorlevel 1 pause

echo.
echo DONE. Your EXE is here:
echo %CD%\dist\OpenToWork.exe
pause
