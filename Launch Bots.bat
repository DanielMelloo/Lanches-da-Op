@echo off
cd /d "d:\Prog\Novo Lanches OP"
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Virtual Environment not found or failed to activate.
    pause
    exit /b
)
start "Bot Manager" python bot_manager_gui.py
exit
