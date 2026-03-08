@echo off
:: タスクスケジューラ経由で管理者権限起動（UAC確認なし）
schtasks /run /tn "WhisperMoji" >nul 2>&1
if %errorLevel% neq 0 (
    echo タスクが未登録です。管理者権限で直接起動します...
    reg query "HKU\S-1-5-19" >nul 2>&1
    if %errorLevel% neq 0 (
        powershell -Command "Start-Process '%~f0' -Verb RunAs"
        exit /b
    )
    cd /d "%~dp0"
    pythonw main.py
)
