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

:: Pull latest changes from remote to avoid conflicts
git pull --no-rebase --quiet

:: Check if there is any change to commit
git add .
git diff --cached --quiet
if %errorlevel%==0 (
    echo Nothing to commit. Working directory is clean.
    pause
    exit /b
)

:: Read version
set version=0
if exist version.txt (
    set /p version=<version.txt
)

:: Increase version number
set /a version+=1
echo %version%>version.txt

:: Commit message
set msg=Auto commit version v%version%

:: Commit and push
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ✅ %msg% has been pushed to garmabsard-flask repository.
pause
