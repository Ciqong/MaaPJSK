@echo off
setlocal
cd /d "%~dp0"

set "APP_DIR=%~dp0install-mfaavalonia"
set "APP_EXE=%APP_DIR%\MFAAvalonia.exe"
set "PYTHON_CMD="

call :is_running
if not errorlevel 1 (
    if /i "%~1"=="--rebuild" (
        echo MFAAvalonia is already running.
        echo Please close it before rebuilding.
        pause
        exit /b 1
    )
    echo MFAAvalonia is already running for this directory.
    exit /b 0
)

if /i "%~1"=="--rebuild" (
    if exist "%APP_DIR%" rmdir /s /q "%APP_DIR%"
)

if exist "%APP_EXE%" goto launch

where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo Python 3 was not found.
    echo Please install Python 3, then run this script again.
    pause
    exit /b 1
)

echo Building MFAAvalonia runtime...
%PYTHON_CMD% "tools\install_mfaavalonia_app.py" --mfa-version v2.12.1 --output "%APP_DIR%"
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

:launch
if not exist "%APP_EXE%" (
    echo MFAAvalonia.exe was not found: "%APP_EXE%"
    pause
    exit /b 1
)

echo Starting MFAAvalonia...
start "" /D "%APP_DIR%" "%APP_EXE%"
exit /b 0

:is_running
if not exist "%APP_EXE%" exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$target=[IO.Path]::GetFullPath('%APP_EXE%'); $p=Get-CimInstance Win32_Process -Filter 'Name=''MFAAvalonia.exe''' | Where-Object { $_.ExecutablePath -and ([IO.Path]::GetFullPath($_.ExecutablePath) -eq $target) }; if ($p) { exit 0 } exit 1" >nul 2>nul
exit /b %errorlevel%
