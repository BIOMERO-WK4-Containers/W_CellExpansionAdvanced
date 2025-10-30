@echo off
setlocal

if "%~1"=="" (
    echo Usage: pushdocker TAG
    echo Example: pushdocker 1.0.3
    exit /b 1
)

set "TAG=%~1"

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

for /f %%I in ('powershell -NoProfile -Command "(Split-Path -Leaf '%SCRIPT_DIR%').ToLower()"') do set "DERIVED_IMAGE_NAME=%%I"

if not defined DERIVED_IMAGE_NAME (
    for %%I in ("%SCRIPT_DIR%") do set "DERIVED_IMAGE_NAME=%%~nI"
)

if not defined IMAGE_NAME set "IMAGE_NAME=%DERIVED_IMAGE_NAME%"
if not defined IMAGE_NAMESPACE set "IMAGE_NAMESPACE=cellularimagingcf"
if "%IMAGE_NAMESPACE%"=="" (
    set "FULL_IMAGE=%IMAGE_NAME%"
) else (
    set "FULL_IMAGE=%IMAGE_NAMESPACE%/%IMAGE_NAME%"
)

REM Tag specific version
if not "%~2"=="--skip-build" (
    echo Tagging %IMAGE_NAME%:latest as %FULL_IMAGE%:%TAG%
    docker tag %IMAGE_NAME%:latest %FULL_IMAGE%:%TAG%
)

echo Pushing %FULL_IMAGE%:%TAG%
docker push %FULL_IMAGE%:%TAG%

REM Tag latest explicitly (optional re-tag)
echo Tagging %IMAGE_NAME%:latest as %FULL_IMAGE%:latest
if not "%~2"=="--skip-build" (
    docker tag %IMAGE_NAME%:latest %FULL_IMAGE%:latest
)

echo Pushing %FULL_IMAGE%:latest
docker push %FULL_IMAGE%:latest

echo Done.
endlocal
