@echo off
setlocal

cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

git --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Git is not installed or not in PATH.
    pause
    exit /b
)

echo --------------------------
echo Project status:
git status
echo --------------------------

set /p msg=Enter your commit message: 

git add .
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ? Successfully pushed to GitHub.
pause
