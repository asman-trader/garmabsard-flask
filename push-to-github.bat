@echo off
setlocal enabledelayedexpansion

:: Project directory
cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

:: Check if Git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo Git is not installed or not added to PATH.
    pause
    exit /b
)

:: Read current version from file
set version=0
if exist version.txt (
    set /p version=<version.txt
)

:: Increase version number
set /a version+=1

:: Save new version
echo %version%>version.txt

:: Commit message
set msg=Auto commit version v%version%

:: Show status
echo --------------------------
echo Git status before commit:
git status
echo --------------------------

:: Commit and push
git add .
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ✅ %msg% has been pushed to garmabsard-flask repository.
pause
