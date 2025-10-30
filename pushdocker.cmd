@echo off
setlocal 

if "%~1"=="" (
    echo Usage: pushdocker TAG
    echo Example: pushdocker 1.0.3
    exit /b 1
)

set "TAG=%~1"
set "IMAGE_NAMESPACE=cellularimagingcf"
set "IMAGE_NAME=w_cellexpansionadvanced"
set "FULL_IMAGE=%IMAGE_NAMESPACE%/%IMAGE_NAME%"

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
