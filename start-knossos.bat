@echo off
REM ===================================================================
REM  Knossos MCP - start the server (run this on the SERVER machine).
REM  Just double-click this file.
REM  On the first run it creates the virtualenv and installs deps.
REM ===================================================================
cd /d "%~dp0"
title Knossos MCP

if not exist ".venv\Scripts\python.exe" (
    echo [knossos] First run: creating virtualenv and installing...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -e .
)

if not exist ".env" (
    echo.
    echo [knossos] ERROR: .env not found.
    echo Copy .env.example to .env and set KNOSSOS_TOKEN and KNOSSOS_ALLOWED_DIRS.
    echo.
    pause
    exit /b 1
)

echo [knossos] Starting server... (close this window or Ctrl+C to stop)
echo [knossos] While this window is open, the machine will not sleep from inactivity.

REM Keep the system awake via SetThreadExecutionState (ES_CONTINUOUS|ES_SYSTEM_REQUIRED)
REM while the server runs; closing the window releases the state automatically.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s='[DllImport(\"kernel32.dll\", SetLastError=true)] public static extern uint SetThreadExecutionState(uint e);'; $k=Add-Type -MemberDefinition $s -Name Pwr -Namespace Win32 -PassThru; [void]$k::SetThreadExecutionState([uint32]2147483649); Write-Host '[knossos] keep-awake ON'; try { & '.\.venv\Scripts\python.exe' -m knossos.server } finally { [void]$k::SetThreadExecutionState([uint32]2147483648); Write-Host '[knossos] keep-awake OFF' }"

echo.
echo [knossos] The server stopped.
pause
