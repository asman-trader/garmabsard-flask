@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ================================================
REM Vinor (vinor.ir) – Safe Git Pusher (Final)
REM فقط کدها را پوش می‌کند؛ دیتا/آپلود/DB/لاگ/.env پوش نمی‌شوند
REM استفاده:
REM   vinor_push.bat "پیام کامیت"
REM   vinor_push.bat --cleanup   (یک‌بار برای untrack کردن فایل‌های دیتایی)
REM ================================================

REM مسیر ریپازیتوری (بر اساسِ اسکریپت قبلیِ شما)
set "REPO_DIR=C:\Users\Aseman\OneDrive\Desktop\py-code\G"

REM رفتن به مسیر ریپو
cd /d "%REPO_DIR%" || (
  echo [X] مسیر ریپو پیدا نشد: %REPO_DIR%
  exit /b 1
)

REM بررسی نصب بودن Git
where git >nul 2>&1 || (
  echo [X] Git نصب نیست یا در PATH نیست.
  exit /b 1
)

REM آیا داخل مخزن گیت هستیم؟
git rev-parse --is-inside-work-tree >nul 2>&1 || (
  echo [X] اين پوشه مخزن Git نيست.
  exit /b 1
)

REM شاخه فعلی
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set CURRENT_BRANCH=%%b
if not defined CURRENT_BRANCH (
  echo [X] شاخه فعلی مشخص نشد.
  exit /b 1
)
echo [i] Branch: %CURRENT_BRANCH%

REM حالت Cleanup: يکبار براي خارج کردن فايل‌هاي دیتايي از حالت track
if /i "%~1"=="--cleanup" (
  echo [i] Cleanup mode: حذف مسيرهاي دیتايي/حساس از حالت track...
  git rm -r --cached --quiet app/data 2>nul
  git rm -r --cached --quiet instance 2>nul
  git rm -r --cached --quiet app/static/uploads 2>nul
  git rm -r --cached --quiet uploads 2>nul
  git rm -r --cached --quiet logs 2>nul

  for %%P in (*.db *.sqlite *.sqlite3 *.log .env *.env *.tmp *.bak) do (
    git rm --cached --quiet "%%P" 2>nul
  )

  echo [✓] Cleanup انجام شد. لطفاً يک commit و push بزن تا تغيير اعمال شود.
  exit /b 0
)

REM Pull با rebase (ايمن‌تر براي تاريخچه)
echo [i] Pull (rebase)...
git pull --rebase
if errorlevel 1 (
  echo [X] خطا در pull. ابتدا کانفليکت‌ها را حل کن.
  exit /b 1
)

REM Stage همه‌چيز، سپس Unstage مسيرهاي حساس (دوبل‌سکيو)
echo [i] Staging all...
git add -A

echo [i] Unstaging data/uploads/db/logs/env...
git restore --staged --worktree --quiet -- app/data 2>nul
git restore --staged --worktree --quiet -- instance 2>nul
git restore --staged --worktree --quiet -- app/static/uploads 2>nul
git restore --staged --worktree --quiet -- uploads 2>nul
git restore --staged --worktree --quiet -- logs 2>nul

for %%P in (*.db *.sqlite *.sqlite3 *.log .env *.env *.tmp *.bak) do (
  git restore --staged --worktree --quiet -- "**/%%P" 2>nul
)

REM اگر چيزی برای commit نمانده، خروج تمیز
git diff --cached --quiet
if !errorlevel! EQU 0 (
  echo [i] تغييري براي commit وجود ندارد. Working directory تميز است.
  exit /b 0
)

REM نسخه‌گذاری خودکار با version.txt (حفظ روال قبلی شما)
set "version=0"
if exist version.txt (
  set /p version=<version.txt
  if not defined version set version=0
)
set /a version+=1
>version.txt echo %version%

REM افزودن version.txt به استيج (فايل کُدي محسوب مي‌شود)
git add version.txt

REM پيام کاميت
set "MSG=%~1"
if not defined MSG (
  for /f "tokens=1-3 delims=/: " %%a in ("%date% %time%") do set TS=%date% %time%
  set "MSG=Vinor: code update v%version% (%TS%)"
)

REM نمايش خلاصه وضعيت
git status --short

REM Commit
echo [i] Commit: %MSG%
git commit -m "%MSG%"
if errorlevel 1 (
  echo [X] Commit ناموفق بود.
  exit /b 1
)

REM Push به شاخه فعلي (در صورت نداشتن upstream، ست مي‌شود)
echo [i] Push...
git rev-parse --abbrev-ref --symbolic-full-name @{u} >nul 2>&1
if errorlevel 1 (
  git push -u origin "%CURRENT_BRANCH%"
) else (
  git push
)
if errorlevel 1 (
  echo [X] Push ناموفق بود.
  exit /b 1
)

echo --------------------------------------------
echo [✓] %MSG% با موفقيت پوش شد (بدون دیتاي لوکال/آپلود/DB/لاگ/ENV).
exit /b 0

