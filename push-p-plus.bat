@echo off
REM Simple push script (Git required)
setlocal enabledelayedexpansion

if not exist .git (
  echo Initializing git repo...
  git init
  git add .
  git commit -m "Initial commit"
)

set /p REMOTE_URL="Enter remote URL (or leave empty to skip): "
if not "%REMOTE_URL%"=="" (
  git remote remove origin 2>nul
  git remote add origin %REMOTE_URL%
)

set ts=%date:~0,4%%date:~5,2%%date:~8,2%-%time:~0,2%%time:~3,2%%time:~6,2%
set ts=%ts: =0%

git add -A
git commit -m "push: %ts%"

if not "%REMOTE_URL%"=="" (
  echo Pushing to %REMOTE_URL%...
  git branch -M main
  git push -u origin main
)

echo Done.

