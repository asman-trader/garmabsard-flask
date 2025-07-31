@echo off
setlocal

:: ÊäÙíã ãÓíÑ Ñæå (ÍÊãÇğ åãíä ãÓíÑ Ñæ äåÏÇÑ íÇ ÊÛííÑ ÈÏå Èå æÔå ÎæÏÊ)
cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

:: ÈÑÑÓí Çíä˜å git äÕÈ åÓÊ íÇ äå
git --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Git äÕÈ äíÓÊ íÇ ÏÑ ãÓíÑ PATH äíÓÊ.
    pause
    exit /b
)

:: äãÇíÔ æÖÚíÊ
echo --------------------------
echo æÖÚíÊ İÚáí Ñæå:
git status
echo --------------------------

:: ÏÑíÇİÊ íÇã ˜ÇãíÊ
set /p msg=áØİÇğ íÇã ÊÛííÑÇÊ ÑÇ æÇÑÏ ˜ä:

git add .
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ? ÊÛííÑÇÊ ÈÇ ãæİŞíÊ ÇÑÓÇá ÔÏ.
pause
