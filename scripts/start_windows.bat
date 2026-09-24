@echo off
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv not found. Run scripts\setup_windows.bat first.
  exit /b 1
)

echo Starting Scan2Stage...
echo Open http://127.0.0.1:8765 in your browser.
".venv\Scripts\python.exe" -m scan2stage.web
endlocal
