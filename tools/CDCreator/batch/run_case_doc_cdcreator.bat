@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "POWERSHELL_SCRIPT=%SCRIPT_DIR%run_case_doc_cdcreator.ps1"

if not exist "%POWERSHELL_SCRIPT%" (
  echo [ERROR] PowerShell script was not found.
  echo %POWERSHELL_SCRIPT%
  pause
  exit /b 1
)

if "%~1"=="" (
  powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%POWERSHELL_SCRIPT%"
) else (
  powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%POWERSHELL_SCRIPT%" -CaseDocPath "%~f1"
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
  echo Completed successfully.
) else if "%EXIT_CODE%"=="2" (
  echo Canceled.
) else (
  echo Failed. Review the message above and the logs folder.
)
echo.
pause
exit /b %EXIT_CODE%
