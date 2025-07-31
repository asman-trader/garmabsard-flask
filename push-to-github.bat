@echo off
setlocal

:: Project directory
cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

:: Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo Git is not installed or not added to PATH.
    pause
    exit /b
)

:: Show git status
echo --------------------------
echo Current project status:
git status
echo --------------------------

:: Get commit message from user
set /p msg=Enter your commit message:

:: Apply changes
git add .
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ✅ Changes successfully pushed to garmabsard-flask repository.
pause
