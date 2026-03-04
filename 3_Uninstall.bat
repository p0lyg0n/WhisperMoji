@echo off
chcp 65001 >nul

cd /d "%~dp0"

:: ---- Python確認 ----
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [Error] Python not found.
    pause
    exit /b
)

:: ---- 言語データ読み込み ----
for /f "delims=" %%I in ('python -c "import sys,json,os,ctypes,locale; sys.stdout.reconfigure(encoding='utf-8'); l=os.environ.get('LANG_OVERRIDE') or locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), 'en').split('_')[0]; f=rf'lang\{l}.json' if os.path.exists(rf'lang\{l}.json') else r'lang\en.json'; d=json.load(open(f, encoding='utf-8')); [print('set \x22{k}={v}\x22'.format(k=k, v=v)) for k,v in {'L_TITLE':d.get('bat_uninstall_title','Uninstall'), 'L_CONF':d.get('bat_uninstall_confirm','Uninstall? (Y/N): '), 'L_DONE':d.get('bat_uninstall_done','Uninstall Complete!'), 'L_ADMIN':d.get('bat_admin_req','Admin req'), 'L_PY_ERR':d.get('bat_py_err','Err'), 'L_DEL1':d.get('bat_del_msg1',''), 'L_DEL2':d.get('bat_del_msg2',''), 'L_DEL3':d.get('bat_del_msg3',''), 'L_DEL4':d.get('bat_del_msg4',''), 'L_CANCEL':d.get('bat_cancel','Cancel'), 'L_TASK':d.get('bat_del_task',''), 'L_CACHE':d.get('bat_del_cache','')}.items()]" 2^>nul') do %%I

echo =========================================================
echo   %L_TITLE%
echo =========================================================
echo.

:: ---- 管理者権限チェック ----
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo %L_ADMIN%
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo %L_DEL1%
echo %L_DEL2%
echo %L_DEL3% %USERPROFILE%\.cache\huggingface\hub\
echo.
echo %L_DEL4%
echo.

set /p CONFIRM="%L_CONF%"
if /i not "%CONFIRM%"=="Y" (
    echo %L_CANCEL%
    timeout /t 2 /nobreak >nul
    exit /b
)
echo.

:: ---- [1] タスクスケジューラ削除 ----
echo [1/2] %L_TASK%
schtasks /delete /tn "WhisperMoji" /f >nul 2>&1
echo.

:: ---- [2] AIモデルキャッシュ削除 ----
echo [2/2] %L_CACHE%
set "HF_CACHE=%USERPROFILE%\.cache\huggingface\hub"
for /d %%d in ("%HF_CACHE%\models--*whisper*") do (
    rmdir /s /q "%%d" 2>nul
)
echo.

:: ---- 完了 ----
echo =========================================================
echo   %L_DONE%
echo =========================================================
echo.
pause
