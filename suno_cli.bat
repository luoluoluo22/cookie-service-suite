@echo off
chcp 65001 >nul
setlocal
set "SCRIPT_DIR=%~dp0"

set "PY_EXE=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    where py >nul 2>nul && set "PY_EXE=py"
)

"%PY_EXE%" "%SCRIPT_DIR%suno_cli.py" %*
