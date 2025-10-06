@echo off
REM --- Run config_gui.py from the batch file's folder ---

REM Save current dir and switch to the directory containing this script
pushd "%~dp0"

echo Running from: %cd%

REM Try "python", fall back to "py -3" if python isn't on PATH
where python >nul 2>&1
if %errorlevel%==0 (
    python config_gui.py %*
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        py -3 config_gui.py %*
    ) else (
        echo.
        echo ERROR: Python not found on PATH. Install Python or add it to PATH.
        echo You can download it from: https://www.python.org/
        echo.
        pause
    )
)

REM Return to original directory
popd
