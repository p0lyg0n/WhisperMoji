import customtkinter as ctk
import threading
import time
import keyboard
from core.i18n import L
from core.config import MODEL_OPTIONS, MODEL_SPECS, _recommend_model, _get_total_ram_gb
from ui.constants import (
    COLOR_INFO, COLOR_WARNING, COLOR_MUTED, FONT, FONT_BTN, HOTKEY_OPTIONS
)

class SettingsWindow(ctk.CTkToplevel):
    """設定を変更するための別ウィンドウ。"""

    def __init__(self, app, first_run: bool = False):
        super().__init__(app)
        self.app = app
        self._first_run = first_run
        self.title(L.get("first_run_title", "Initial Setup") if first_run else L.get("settings_title", "Settings"))
        self.geometry("400x500" if first_run else "400x380")
        self.resizable(False, False)
        self.transient(app)
        if first_run:
            self.protocol("WM_DELETE_WINDOW", self._on_first_run_close)  # メインウィンドウに紐付け

        if app.is_running:
            self._build_locked()
        else:
            self._build_settings()

    def _build_locked(self):
        """AI起動中は変更不可メッセージを表示。"""
        ctk.CTkLabel(
            self, text=L.get("settings_locked", "Settings locked"),
            font=("Meiryo", 13), text_color="#e67e22",
        ).pack(expand=True)

    def _build_settings(self):
        """設定タブを構築。"""
        if self._first_run:
            welcome = ctk.CTkFrame(self, fg_color="#162230", corner_radius=8)
            welcome.pack(pady=(8, 0), padx=10, fill="x")
            ctk.CTkLabel(
                welcome, text=L.get("welcome_title", "Welcome!"),
                font=("Meiryo", 14, "bold"), text_color=COLOR_INFO,
            ).pack(pady=(6, 0))
            ctk.CTkLabel(
                welcome,
                text=L.get("welcome_steps", ""),
                font=("Meiryo", 12), text_color="#b0bec5", justify="left",
            ).pack(pady=(2, 6), padx=10)

        # 現在のアプリ内の設定値をウィジェット生成前に退避
        cur_mic = self.app.cb_mic.get()
        cur_hotkey = self.app.cb_hotkey.get()
        cur_enter = self.app.chk_enter.get()
        cur_model = self.app.cb_model.get()
        cur_prompt = self.app.ent_prompt.get()
        cur_noise = self.app.sw_noise.get()
        cur_gain = self.app.sl_gain.get()

        tabview = ctk.CTkTabview(self, width=370, height=260)
        tabview.pack(pady=8, padx=10)

        # 基本タブ
        tab1 = tabview.add(L.get("tab_basic", "Basic"))
        ctk.CTkLabel(tab1, text=L.get("label_mic", "Microphone"), font=FONT).pack(anchor="w", padx=10, pady=(4, 0))
        self.app.cb_mic = ctk.CTkComboBox(tab1, values=self.app._mic_list, width=340, height=26, font=FONT)
        self.app.cb_mic.pack(padx=10, pady=2)

        ctk.CTkLabel(tab1, text=L.get("label_hotkey", "Hotkey"), font=FONT).pack(anchor="w", padx=10, pady=(6, 0))
        hk_frame = ctk.CTkFrame(tab1, fg_color="transparent")
        hk_frame.pack(fill="x", padx=10, pady=2)
        self.app.cb_hotkey = ctk.CTkComboBox(hk_frame, values=HOTKEY_OPTIONS, width=130, height=26, font=FONT)
        self.app.cb_hotkey.pack(side="left")
        
        self._btn_record = ctk.CTkButton(
            hk_frame, text=L.get("btn_record_key", "⌨️ 記録"), font=FONT, width=60, height=26,
            fg_color=COLOR_INFO, hover_color="#2980b9", command=self._start_record_hotkey
        )
        self._btn_record.pack(side="left", padx=(6, 0))
        
        self.app.chk_enter = ctk.CTkCheckBox(hk_frame, text=L.get("label_auto_enter", "Auto Enter"), font=FONT)
        self.app.chk_enter.pack(side="left", padx=(12, 0))

        # AI設定タブ
        tab2 = tabview.add(L.get("tab_ai", "AI Settings"))

        # PCのRAM容量を表示
        ram_gb = _get_total_ram_gb()
        ram_text = L.get("label_ram_info", "RAM: {ram}GB").replace("{ram}", f"{ram_gb:.0f}")
        ctk.CTkLabel(
            tab2, text=ram_text,
            font=("Meiryo", 9), text_color=COLOR_INFO,
        ).pack(anchor="w", padx=10, pady=(4, 0))

        ctk.CTkLabel(tab2, text=L.get("label_ai_model", "AI Model"), font=FONT).pack(anchor="w", padx=10, pady=(4, 0))
        self.app.cb_model = ctk.CTkComboBox(
            tab2, values=MODEL_OPTIONS, width=340, height=26, font=FONT,
            command=lambda _: self._update_model_spec(),
        )
        self.app.cb_model.pack(padx=10, pady=2)

        # 初回起動時はRAMに基づいて自動選択
        if self._first_run:
            recommended = _recommend_model()
            self.app.cb_model.set(recommended)

        self._lbl_spec = ctk.CTkLabel(
            tab2, text="", font=("Meiryo", 9), text_color=COLOR_MUTED, wraplength=340,
        )
        self._lbl_spec.pack(anchor="w", padx=10, pady=(2, 0))
        self._update_model_spec()

        # 詳細タブ
        tab3 = tabview.add(L.get("tab_advanced", "Advanced"))
        ctk.CTkLabel(tab3, text=L.get("label_prompt", "Context Prompt"), font=FONT).pack(anchor="w", padx=10, pady=(4, 0))
        self.app.ent_prompt = ctk.CTkEntry(tab3, placeholder_text=L.get("placeholder_prompt", "Ex: Um, ah..."), width=340, height=26, font=FONT)
        self.app.ent_prompt.pack(padx=10, pady=2)

        opt_frame = ctk.CTkFrame(tab3, fg_color="transparent")
        opt_frame.pack(fill="x", padx=10, pady=(6, 0))
        self.app.sw_noise = ctk.CTkSwitch(opt_frame, text=L.get("label_noise_cancel", "Noise Cancel"), font=FONT)
        self.app.sw_noise.select()
        self.app.sw_noise.pack(side="left")

        gain_frame = ctk.CTkFrame(tab3, fg_color="transparent")
        gain_frame.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(gain_frame, text=L.get("label_gain", "Mic Gain"), font=FONT).pack(side="left")
        self.app.sl_gain = ctk.CTkSlider(gain_frame, from_=0.5, to=3.0, number_of_steps=25, width=200)
        self.app.sl_gain.set(1.0)
        self.app.sl_gain.pack(side="left", padx=(8, 0))

        # 設定を反映（退避した値でウィジェットを初期化）
        if cur_mic and cur_mic in self.app._mic_list:
            self.app.cb_mic.set(cur_mic)
        else:
            self.app._select_default_mic()

        if cur_hotkey:
            self.app.cb_hotkey.set(cur_hotkey)
            
        if cur_enter:
            self.app.chk_enter.select()
        else:
            self.app.chk_enter.deselect()
            
        if cur_model:
            self.app.cb_model.set(cur_model)
            
        if cur_prompt:
            self.app.ent_prompt.delete(0, "end")
            self.app.ent_prompt.insert(0, cur_prompt)
            
        if cur_noise:
            self.app.sw_noise.select()
        else:
            self.app.sw_noise.deselect()
            
        if cur_gain:
            self.app.sl_gain.set(cur_gain)

        # 初回起動時のみ一部の値を推奨値で上書き
        if self._first_run:
            recommended = _recommend_model()
            self.app.cb_model.set(recommended)
            self.app._select_default_mic()

        # 保存ボタン
        btn_text = L.get("btn_first_start", "Start") if self._first_run else L.get("btn_save_close", "Save & Close")
        ctk.CTkButton(
            self, text=btn_text, font=FONT_BTN, height=36,
            command=self._save_and_close,
        ).pack(pady=(4, 10), padx=15, fill="x")

    def _update_model_spec(self):
        """選択中のモデルに合わせてスペック説明を更新。"""
        model_name = self.app.cb_model.get().split(" ")[0].strip()
        spec = MODEL_SPECS.get(model_name, "")
        self._lbl_spec.configure(text=spec)

    def _save_and_close(self):
        # ウィジェットの値をキャプチャ（destroy前）
        values = {
            "mic": self.app.cb_mic.get(),
            "hotkey": self.app.cb_hotkey.get(),
            "auto_enter": self.app.chk_enter.get(),
            "model": self.app.cb_model.get(),
            "prompt": self.app.ent_prompt.get(),
            "noise_cancel": self.app.sw_noise.get(),
            "gain": self.app.sl_gain.get(),
        }
        self.app._save_config()
        start_after = self._first_run
        self.destroy()

        # FakeWidgetに戻す（破棄されたウィジェットを参照しないようにする）
        self.app._init_setting_vars()
        self.app.cb_mic.set(values["mic"])
        self.app.cb_hotkey.set(values["hotkey"])
        if values["auto_enter"]:
            self.app.chk_enter.select()
        self.app.cb_model.set(values["model"])
        self.app.ent_prompt.insert(0, values["prompt"])
        if values["noise_cancel"]:
            self.app.sw_noise.select()
        self.app.sl_gain.set(values["gain"])
        self.app._update_guide()

        if start_after:
            self.app.after(300, self.app._start)

    def _on_first_run_close(self):
        """初回設定を×で閉じてもデフォルトで保存して起動。"""
        self._save_and_close()

    def _start_record_hotkey(self):
        """ホットキーの記録待機を開始する。"""
        self._btn_record.configure(text=L.get("btn_recording", "待機中..."), fg_color=COLOR_WARNING, state="disabled")
        threading.Thread(target=self._record_thread, daemon=True).start()

    def _record_thread(self):
        # クリック直後にマウスキーなどが拾われないよう少し待つ
        time.sleep(0.3)
        try:
            # 入力完了（キーが離される）まで待機
            hk = keyboard.read_hotkey(suppress=False)
            if hk:
                self.after(0, lambda: self._update_hotkey_ui(hk))
            else:
                self._reset_record_btn()
        except Exception:
            self._reset_record_btn()

    def _update_hotkey_ui(self, hk: str):
        # プラス記号等の前後のスペースを削除・正規化
        hk = " + ".join([k.strip() for k in hk.split('+')])
        self.app.cb_hotkey.set(hk)
        
        # もし選択肢になければ追加しておく
        current_values = self.app.cb_hotkey.cget("values")
        if hk not in current_values:
            self.app.cb_hotkey.configure(values=current_values + [hk])
            
        self._reset_record_btn()

    def _reset_record_btn(self):
        self.after(0, lambda: self._btn_record.configure(
            text=L.get("btn_record_key", "⌨️ 記録"), fg_color=COLOR_INFO, state="normal"
        ))
