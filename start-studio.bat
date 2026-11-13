@echo off
REM Starts autoedit Studio (web interface) and opens it in your browser.
cd /d "%~dp0"
.venv\Scripts\python.exe -m webui %*
pause
