"""WhisperMoji — ホットキー音声入力ツール

ホットキーを押しながら話すことで、カーソル位置にテキストを自動入力する。
エンジン: faster-whisper (CTranslate2) / CPU / int8
"""

import time
import keyboard
import threading
import ctypes
import atexit
import numpy as np
import sounddevice as sd
import customtkinter as ctk
import pyperclip
import json
import os
import sys
import subprocess
import urllib.request
import re
from tkinter import messagebox
from typing import Optional

from core.i18n import L, LANG_CODE
from core.config import MODEL_OPTIONS, MODEL_SPECS, _recommend_model, _get_total_ram_gb, CONFIG_FILE
from ui.cursor_manager import CursorManager
from ui.settings_window import SettingsWindow
from ui.constants import (
    COLOR_SUCCESS, COLOR_INFO, COLOR_WARNING, COLOR_MUTED,
    COLOR_RESULT_BG, COLOR_RESULT_TEXT, COLOR_RESULT_MUTED,
    COLOR_BTN_START, COLOR_BTN_START_HOVER, COLOR_BTN_STOP, COLOR_BTN_STOP_HOVER,
    HOTKEY_OPTIONS, FONT, FONT_TITLE, FONT_BTN, FONT_RESULT, FONT_STATUS, FONT_SMALL
)
from engine.keyboard_input import KeyboardInputManager
from engine.audio import AudioManager, SAMPLE_RATE
from engine.whisper_engine import WhisperEngine

# ===========================================================================
#  定数






POLL_INTERVAL = 0.05



# ===========================================================================
#  App — メインウィンドウ（コンパクト）
# ===========================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """WhisperMoji のメインウィンドウ（コンパクト版）。"""

    def __init__(self):
        super().__init__()
        self.title(L.get("app_title", "WhisperMoji"))
        self.geometry("340x290")
        self.resizable(False, False)

        # 内部状態
        self.is_running = False
        self.is_listening = False
        self.audio_buffer: list = []
        self.engine = WhisperEngine()
        self.cursor = CursorManager()
        self._target_hwnd: Optional[int] = None
        self._settings_win: Optional[SettingsWindow] = None

        # マイク一覧
        self._mic_list, self._mic_id_map = AudioManager.get_microphones()

        # 設定ウィジェットのデフォルト値（設定ウィンドウで上書きされる）
        self._init_setting_vars()

        # UI構築
        self._build_ui()

        # 設定読み込み
        self._load_config()

        # 初回起動判定
        if not os.path.exists(CONFIG_FILE):
            # 初回: 設定ウィンドウを先に開く（保存後に自動スタート）
            self.after(500, lambda: self._open_settings(first_run=True))
        else:
            # 2回目以降: 即自動スタート
            self.after(500, self._start)

        # 自動アップデートチェック (バックグラウンド)
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _init_setting_vars(self):
        """設定ウィジェットが未作成でもアクセスできるよう内部変数で保持。"""

        class _FakeWidget:
            """設定ウィンドウが開かれるまでの仮ウィジェット。"""
            def __init__(self, val=""):
                self._val = val
            def get(self):
                return self._val
            def set(self, v):
                self._val = v
            def select(self): self._val = 1
            def deselect(self): self._val = 0
            def delete(self, *a): pass
            def insert(self, *a):
                if len(a) >= 2:
                    self._val = a[1]

        self.cb_mic = _FakeWidget()
        self.cb_hotkey = _FakeWidget("right ctrl")
        self.chk_enter = _FakeWidget(0)
        self.cb_model = _FakeWidget(MODEL_OPTIONS[1])
        self.ent_prompt = _FakeWidget(L.get("placeholder_prompt", ""))
        self.sw_noise = _FakeWidget(1)
        self.sl_gain = _FakeWidget(1.0)

    def _select_default_mic(self):
        label = AudioManager.get_default_microphone(self._mic_id_map)
        if label:
            self.cb_mic.set(label)

    # ---------------------------------------------------------------
    #  UI
    # ---------------------------------------------------------------
    def _build_ui(self):
        # ヘッダー
        ctk.CTkLabel(self, text="🎙 WhisperMoji", font=FONT_TITLE).pack(pady=(6, 0))
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        admin_text = L.get("admin_ok", "OK") if is_admin else L.get("admin_warn", "Warning")
        admin_color = COLOR_SUCCESS if is_admin else "#e74c3c"
        ctk.CTkLabel(self, text=admin_text, font=FONT_SMALL, text_color=admin_color).pack(pady=(0, 2))

        # 起動ボタン
        self.btn_start = ctk.CTkButton(
            self, text=L.get("btn_start", "Start"), font=FONT_BTN, height=36, command=self._toggle,
        )
        self.btn_start.pack(pady=(2, 3), padx=12, fill="x")

        # 認識結果
        result_frame = ctk.CTkFrame(self, fg_color=COLOR_RESULT_BG)
        result_frame.pack(pady=2, padx=12, fill="x")
        self.lbl_result = ctk.CTkLabel(
            result_frame, text=L.get("result_default", "---"), font=FONT_RESULT,
            text_color=COLOR_RESULT_TEXT, wraplength=300,
        )
        self.lbl_result.pack(pady=4, padx=6)

        # ステータス
        self.lbl_status = ctk.CTkLabel(
            self, text=L.get("status_waiting", "Waiting"), font=FONT_STATUS, text_color="gray",
        )
        self.lbl_status.pack(pady=1)

        # 操作ガイド（トリガーキー表示）
        guide_frame = ctk.CTkFrame(self, fg_color="#162230", corner_radius=6)
        guide_frame.pack(pady=(2, 2), padx=12, fill="x")
        self.lbl_guide = ctk.CTkLabel(
            guide_frame, text="", font=("Meiryo", 12, "bold"), text_color="#dfe6e9",
        )
        self.lbl_guide.pack(pady=4)
        self._update_guide()

        # フッター（設定 & キーリセット）
        self.footer = ctk.CTkFrame(self, fg_color="transparent")
        self.footer.pack(pady=(2, 6))
        ctk.CTkButton(
            self.footer, text=L.get("btn_settings", "Settings"), font=FONT, height=28, width=90,
            fg_color="transparent", border_width=1, command=self._open_settings,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            self.footer, text=L.get("btn_key_reset", "Key Reset"), font=FONT, height=28, width=110,
            fg_color="transparent", border_width=1, command=self._reset_keys,
        ).pack(side="left", padx=4)

    def _open_settings(self, first_run: bool = False):
        """設定ウィンドウを開く。"""
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.focus()
            return
        self._settings_win = SettingsWindow(self, first_run=first_run)

    def _update_guide(self):
        """ホットキーの操作ガイドを更新する。"""
        key = self.cb_hotkey.get()
        guide_text = L.get("guide_template", "Hold 『{key}』 while speaking → Release to input").replace("{key}", key)
        self.lbl_guide.configure(text=guide_text)

    # ---------------------------------------------------------------
    #  オートアップデート処理
    # ---------------------------------------------------------------
    def _check_for_updates(self):
        try:
            import faster_whisper
            res = urllib.request.urlopen("https://pypi.org/pypi/faster-whisper/json", timeout=5)
            data = json.loads(res.read())
            latest_version = data["info"]["version"]
            current_version = faster_whisper.__version__

            def parse_ver(v_str):
                return tuple(map(int, re.findall(r"\d+", v_str)))

            if parse_ver(latest_version) > parse_ver(current_version):
                self.after(0, self._show_update_button)
        except Exception:
            pass

    def _show_update_button(self):
        if not hasattr(self, "btn_update"):
            self.btn_update = ctk.CTkButton(
                self.footer, text=L.get("btn_update", "🔄 Update"), font=FONT_SMALL, height=24, width=100,
                fg_color="#d35400", hover_color="#e67e22", text_color="white", command=self._prompt_update,
            )
            self.btn_update.pack(side="left", padx=4)

    def _prompt_update(self):
        ans = messagebox.askyesno(
            L.get("update_title", "Update Available"),
            L.get("update_message", "New Engine\nUpdate?")
        )
        if ans:
            self.btn_update.configure(state="disabled", text="...")
            self._set_status(L.get("update_progress", "Updating..."), COLOR_INFO)
            threading.Thread(target=self._do_update, daemon=True).start()

    def _do_update(self):
        try:
            if self.is_running:
                self._stop()
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "faster-whisper"],
                check=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            subprocess.Popen(
                ["schtasks", "/run", "/tn", "WhisperMoji"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            os._exit(0)
        except Exception as e:
            self.after(0, lambda: self._set_status(L.get("error_failed", "Failed: {error}").format(error=str(e)), "#e74c3c"))
            self.after(0, lambda: self.btn_update.configure(state="normal", text=L.get("btn_update", "🔄 Update")))

    # ---------------------------------------------------------------
    #  設定の永続化
    # ---------------------------------------------------------------
    def _save_config(self):
        config = {
            "mic": self.cb_mic.get(),
            "hotkey": self.cb_hotkey.get(),
            "auto_enter": self.chk_enter.get(),
            "model": self.cb_model.get(),
            "prompt": self.ent_prompt.get(),
            "noise_cancel": self.sw_noise.get(),
            "gain": self.sl_gain.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"設定の保存に失敗: {e}")
        self._update_guide()

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            self._select_default_mic()
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if cfg.get("mic") in self._mic_list:
                self.cb_mic.set(cfg["mic"])
            else:
                self._select_default_mic()
            if "hotkey" in cfg:
                self.cb_hotkey.set(cfg["hotkey"])
            if "auto_enter" in cfg:
                self.chk_enter.select() if cfg["auto_enter"] else self.chk_enter.deselect()
            if "model" in cfg:
                self.cb_model.set(cfg["model"])
            if "prompt" in cfg:
                self.ent_prompt.delete(0, "end")
                self.ent_prompt.insert(0, cfg["prompt"])
            if "noise_cancel" in cfg:
                self.sw_noise.select() if cfg["noise_cancel"] else self.sw_noise.deselect()
            if "gain" in cfg:
                self.sl_gain.set(cfg["gain"])
        except Exception as e:
            print(f"設定の読み込みに失敗: {e}")

    # ---------------------------------------------------------------
    #  ステータス更新
    # ---------------------------------------------------------------
    def _set_status(self, text: str, color: str = "gray"):
        self.after(0, lambda: self.lbl_status.configure(text=text, text_color=color))

    def _start_loading_animation(self, base_text: str, color: str = COLOR_WARNING):
        """ドットアニメーション付きステータス表示を開始。"""
        self._anim_base = base_text
        self._anim_color = color
        self._anim_dots = 0
        self._anim_running = True
        self._animate_step()

    def _animate_step(self):
        if not self._anim_running:
            return
        dots = "." * (self._anim_dots % 4)
        self.lbl_status.configure(
            text=f"{self._anim_base}{dots}", text_color=self._anim_color
        )
        self._anim_dots += 1
        self.after(500, self._animate_step)

    def _stop_loading_animation(self):
        self._anim_running = False

    def _set_result(self, text: str, color: str = COLOR_RESULT_TEXT):
        self.after(0, lambda: self.lbl_result.configure(text=text, text_color=color))

    # ---------------------------------------------------------------
    #  エンジン制御
    # ---------------------------------------------------------------
    def _toggle(self):
        if not self.is_running:
            self._start()
        else:
            self._stop()

    def _start(self):
        self.is_running = True
        self.btn_start.configure(text=L.get("status_preparing", "Preparing..."), state="disabled")
        threading.Thread(target=self._init_model, daemon=True).start()

    def _stop(self):
        self.is_running = False
        self.cursor.restore()
        self._save_config()
        self.btn_start.configure(
            text=L.get("btn_start", "Start"), state="normal",
            fg_color=COLOR_BTN_START, hover_color=COLOR_BTN_START_HOVER,
        )
        self.lbl_status.configure(text=L.get("status_stopped", "Stopped"), text_color="gray")
        try:
            keyboard.release(self.cb_hotkey.get())
        except Exception:
            pass

    def _reset_keys(self):
        KeyboardInputManager.force_release_keys()
        self.lbl_status.configure(text=L.get("status_key_reset", "Keys reset"), text_color=COLOR_SUCCESS)

    def _is_model_cached(self, model_name: str) -> bool:
        """モデルが既にHuggingFaceキャッシュにあるか確認。"""
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")
        # faster-whisperが使うモデル名パターン
        return WhisperEngine.is_model_cached(model_name)

    MODEL_DOWNLOAD_SIZES = {
        "large-v3": "約3GB", "medium": "約1.5GB", "small": "約500MB",
        "base": "約150MB", "tiny": "約75MB",
    }

    def _init_model(self):
        try:
            model_name = self.cb_model.get().split(" ")[0].strip()
            cpu_threads = os.cpu_count() or 8

            # キャッシュ判定で表示を切り替え
            if self._is_model_cached(model_name):
                self.after(0, lambda: self._start_loading_animation(
                    L.get("loading_read", "Loading model")))
                self.after(0, lambda: self.btn_start.configure(
                    text=L.get("loading_btn_read", "Loading...")))
            else:
                size = self.MODEL_DOWNLOAD_SIZES.get(model_name, "")
                self.after(0, lambda: self._start_loading_animation(
                    L.get("loading_download", "Downloading ({size})").replace("{size}", size)))
                self.after(0, lambda: self.btn_start.configure(
                    text=L.get("loading_btn_download", "Downloading ({size})").replace("{size}", size)))
                self._set_result(L.get("loading_first_time", "Wait..."), COLOR_MUTED)

            self.engine.load_model(model_name, cpu_threads)

            self.after(0, self._stop_loading_animation)
            print(f"\n[faster-whisper] {model_name} / cpu / int8 / threads={cpu_threads} / beam=1 / VAD=ON / timestamps=OFF")
            self.after(0, self._on_model_ready)
            self._listen_loop()
        except Exception as e:
            self.after(0, self._stop_loading_animation)
            self._set_status(L.get("error_failed", "Failed: {error}").replace("{error}", str(e)), "red")
            self.is_running = False
            self.after(0, lambda: self.btn_start.configure(
                text=L.get("btn_start", "Start"), state="normal", fg_color=COLOR_BTN_START))

    def _on_model_ready(self):
        self.btn_start.configure(
            text=L.get("btn_stop", "Stop"), state="normal",
            fg_color=COLOR_BTN_STOP, hover_color=COLOR_BTN_STOP_HOVER,
        )
        self.lbl_status.configure(text=L.get("status_ready", "Ready"), text_color=COLOR_SUCCESS)
        self.lbl_result.configure(text=L.get("result_default", "---"), text_color=COLOR_RESULT_TEXT)

    # ---------------------------------------------------------------
    #  音声キャプチャ & ホットキー監視
    # ---------------------------------------------------------------
    def _listen_loop(self):
        device_id = self._mic_id_map.get(self.cb_mic.get())

        def on_audio(indata, frames, time_info, status):
            if self.is_listening:
                self.audio_buffer.append(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, device=device_id, callback=on_audio):
            while self.is_running:
                hotkey = self.cb_hotkey.get()
                if keyboard.is_pressed(hotkey):
                    if not self.is_listening:
                        self.is_listening = True
                        self.audio_buffer = []
                        self._target_hwnd = ctypes.windll.user32.GetForegroundWindow()
                        self.cursor.set_recording()
                        self._set_status(L.get("status_listening", "Listening..."), COLOR_SUCCESS)
                else:
                    if self.is_listening:
                        self.is_listening = False
                        self.cursor.set_processing()
                        self._set_status(L.get("status_converting", "Converting..."), COLOR_INFO)
                        try:
                            keyboard.release(hotkey)
                        except Exception:
                            pass
                        threading.Thread(target=self._process_audio, daemon=True).start()
                time.sleep(POLL_INTERVAL)

    # ---------------------------------------------------------------
    #  音声処理パイプライン
    # ---------------------------------------------------------------
    def _process_audio(self):
        if not self.audio_buffer:
            self.cursor.restore()
            return
            
        gain = self.sl_gain.get()
        audio = AudioManager.prepare_audio_buffer(self.audio_buffer, gain)
        
        prompt = self.ent_prompt.get()
        text = self.engine.transcribe(audio, prompt)
        
        noise_cancel_enabled = self.sw_noise.get() == 1
        text = WhisperEngine.filter_noise(text, noise_cancel_enabled)
        
        self._output_text(text)
        
        self.cursor.restore()
        time.sleep(1)
        if self.is_running and not self.is_listening:
            self._set_status(L.get("status_ready", "Ready"), COLOR_SUCCESS)

    def _output_text(self, text: str):
        label = L.get("result_noise", "Noise") if self.sw_noise.get() else L.get("result_silent", "Silent")
        KeyboardInputManager.paste_text(
            text=text,
            auto_enter=self.chk_enter.get(),
            target_hwnd=self._target_hwnd,
            result_callback=self._set_result,
            status_callback=self._set_status,
            silence_label=label,
        )


# ===========================================================================
#  エントリーポイント
# ===========================================================================
MUTEX_NAME = "WhisperMoji_SingleInstance"

if __name__ == "__main__":
    # 多重起動防止（Windows Mutex）
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        msg = L.get("mutex_message", "Already running.")
        title = L.get("mutex_title", "Running")
        ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40)
        ctypes.windll.kernel32.CloseHandle(mutex)
    else:
        app = App()
        app.mainloop()
        ctypes.windll.kernel32.CloseHandle(mutex)
