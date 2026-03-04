import customtkinter as ctk
from core.i18n import L
from core.config import MODEL_OPTIONS, MODEL_SPECS, _recommend_model, _get_total_ram_gb
from ui.constants import (
    COLOR_INFO, COLOR_MUTED, FONT, FONT_BTN, HOTKEY_OPTIONS
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
        self.app.cb_hotkey = ctk.CTkComboBox(hk_frame, values=HOTKEY_OPTIONS, width=180, height=26, font=FONT)
        self.app.cb_hotkey.pack(side="left")
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

        # 設定を反映
        self.app._load_config()
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
