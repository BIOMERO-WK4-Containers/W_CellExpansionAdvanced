@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

for /f %%I in ('powershell -NoProfile -Command "(Split-Path -Leaf '%SCRIPT_DIR%').ToLower()"') do set "IMAGE_NAME=%%I"

if not defined IMAGE_NAME (
    for %%I in ("%SCRIPT_DIR%") do set "IMAGE_NAME=%%~nI"
)

pushd "%SCRIPT_DIR%" >nul
if errorlevel 1 (
    echo Failed to change directory to %SCRIPT_DIR%
    exit /b 1
)

docker build -t %IMAGE_NAME% %* .
set "EXITCODE=%ERRORLEVEL%"

popd >nul
endlocal & exit /b %EXITCODE%
