@echo off
rem Abre o Rastreador como aplicativo (janela do Chrome/Edge, sem barra de endereco).
rem Fechar a janela desliga tudo. Logs: %LOCALAPPDATA%\RastreadorPassagens\logs
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" rastreador_app.pyw
