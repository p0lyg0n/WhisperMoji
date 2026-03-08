@echo off
chcp 65001 >nul

cd /d "%~dp0"

:: ---- Python確認 & 自動インストール ----
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [Info] Python not found. Starting automatic installation...
    echo [Info] Pythonが見つかりません。自動インストールを開始します...
    
    :: wingetでPython 3.11をインストール
    winget install --id Python.Python.3.11 --exact --no-upgrade --source winget --accept-package-agreements --accept-source-agreements
    
    if %errorLevel% neq 0 (
        echo [Error] Automatic installation failed. Please install Python 3.11 manually: https://www.python.org/downloads/
        echo [Error] 自動インストールに失敗しました。手動でインストールしてください。
        pause
        exit /b
    )
    
    echo [Success] Python installed. Please RE-RUN this 1_Setup.bat.
    echo [成功] Pythonをインストールしました。もう一度はこの 1_Setup.bat を実行してください。
    pause
    exit /b
)

:: ---- 言語データ読み込み ----
for /f "delims=" %%I in ('python -c "import sys,json,os,ctypes,locale; sys.stdout.reconfigure(encoding='utf-8'); l=os.environ.get('LANG_OVERRIDE') or locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), 'en').split('_')[0]; f=rf'lang\{l}.json' if os.path.exists(rf'lang\{l}.json') else r'lang\en.json'; d=json.load(open(f, encoding='utf-8')); [print('set \x22{k}={v}\x22'.format(k=k, v=v)) for k,v in {'L_TITLE':d.get('bat_setup_title','Setup'), 'L_PY':d.get('bat_check_python','Check Python...'), 'L_PY_OK':d.get('bat_python_ok','OK:'), 'L_PKG':d.get('bat_pkg_check','Check Pkgs...'), 'L_PKG_OK':d.get('bat_pkg_installed','Installed'), 'L_PKG_DO':d.get('bat_pkg_installing','Installing...'), 'L_PKG_DONE':d.get('bat_pkg_done','Done'), 'L_TASK':d.get('bat_task_register','Register Task...'), 'L_TASK_OK':d.get('bat_task_done','Done'), 'L_COMP':d.get('bat_complete','Setup Complete!')}.items()]" 2^>nul') do %%I

echo =========================================================
echo   %L_TITLE%
echo =========================================================
echo.

:: ---- 管理者権限チェック ----
reg query "HKU\S-1-5-19" >nul 2>&1
if %errorLevel% neq 0 (
    echo ※ Administrator privileges required. Elevating...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)


:: ---- Python確認 (再表示) ----
echo [1/3] %L_PY%
for /f "delims=" %%v in ('python --version') do echo   %L_PY_OK% %%v
echo.

:: ---- パッケージ確認＆インストール ----
echo [2/3] %L_PKG%
python -c "import faster_whisper, customtkinter, keyboard, sounddevice, numpy, pyperclip" >nul 2>&1
if %errorLevel% equ 0 (
    echo   %L_PY_OK% %L_PKG_OK%
) else (
    echo   %L_PKG_DO%
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if %errorLevel% neq 0 (
        echo [Error] pip install failed.
        pause
        exit /b
    )
    echo   %L_PY_OK% %L_PKG_DONE%
)
echo.

:: ---- タスクスケジューラ登録 ----
echo [3/3] %L_TASK%
for /f "delims=" %%i in ('where pythonw') do set "PYTHONW_PATH=%%i" & goto :found
echo [Error] pythonw not found.
pause
exit /b
:found

schtasks /delete /tn "WhisperMoji" /f >nul 2>&1
schtasks /create /tn "WhisperMoji" /tr "\"%PYTHONW_PATH%\" \"%~dp0main.py\"" /sc onlogon /rl highest /f >nul 2>&1

if %errorLevel% neq 0 (
    echo   [Error] Task registration failed.
    pause
    exit /b
)
echo   %L_PY_OK% %L_TASK_OK%
echo.

:: ---- 完了 → 自動起動 ----
echo =========================================================
echo   %L_COMP%
echo =========================================================
schtasks /run /tn "WhisperMoji" >nul 2>&1
timeout /t 3 /nobreak >nul
