@echo off
setlocal

set "DATA_PATH=%~dp0"
if "%DATA_PATH:~-1%"=="\" set "DATA_PATH=%DATA_PATH:~0,-1%"

if "%IMAGE%"=="" set "IMAGE=cellexpansionadvanced:latest"

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
