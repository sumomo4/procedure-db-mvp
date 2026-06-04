@echo off
setlocal

rem Change these paths for the secure company PC.
set "ACCESS_DB_PATH=C:\path\to\source.accdb"
set "OUTPUT_DIR=C:\path\to\mvp-root\storage\standard\access_exports"

set "SCRIPT_DIR=%~dp0"
python "%SCRIPT_DIR%export_accessdb_to_excel.py" --db "%ACCESS_DB_PATH%" --out "%OUTPUT_DIR%"

endlocal
