@echo off
setlocal

:: ����� ���� ���� (����� ���� ���� �� ����� �� ����� ��� �� ���� ����)
cd /d "C:\Users\Aseman\OneDrive\Desktop\py-code\G"

:: ����� ���� git ��� ��� �� ��
git --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo Git ��� ���� �� �� ���� PATH ����.
    pause
    exit /b
)

:: ����� �����
echo --------------------------
echo ����� ���� ����:
git status
echo --------------------------

:: ������ ���� �����
set /p msg=����� ���� ������� �� ���� ��:

git add .
git commit -m "%msg%"
git push origin main

echo --------------------------
echo ? ������� �� ������ ����� ��.
pause
