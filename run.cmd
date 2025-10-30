@echo off
setlocal

set "DATA_PATH=%~dp0"
if "%DATA_PATH:~-1%"=="\" set "DATA_PATH=%DATA_PATH:~0,-1%"

set "SCRIPT_DIR=%DATA_PATH%"
for /f %%I in ('powershell -NoProfile -Command "(Split-Path -Leaf '%SCRIPT_DIR%').ToLower()"') do set "DEFAULT_IMAGE=%%I"

if not defined DEFAULT_IMAGE (
	for %%I in ("%SCRIPT_DIR%") do set "DEFAULT_IMAGE=%%~nI"
)

if "%IMAGE%"=="" set "IMAGE=%DEFAULT_IMAGE%"

docker run --rm ^
	-v "%DATA_PATH%\infolder:/data/in" ^
	-v "%DATA_PATH%\outfolder:/data/out" ^
	-v "%DATA_PATH%\gtfolder:/data/gt" ^
	%IMAGE% ^
	--infolder /data/in ^
	--outfolder /data/out ^
	--gtfolder /data/gt ^
	--local ^
	%*

endlocal
