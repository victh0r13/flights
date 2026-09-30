@echo off
rem Gera o Configurar.exe a partir do configurar.py. Rode de novo sempre que mudar o codigo.
rem Precisa do ambiente de desenvolvimento: .venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pyinstaller --onefile --console --name Configurar --distpath . --workpath build --specpath build --collect-all fast_flights --collect-all primp --collect-all selectolax --noconfirm configurar.py
pause
