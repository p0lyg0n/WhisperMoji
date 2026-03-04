import ctypes
import time
import threading
import keyboard
import pyperclip
from core.i18n import L

CLIPBOARD_RESTORE_DELAY = 0.5
PASTE_DELAY = 0.15

class KeyboardInputManager:
    """キーボード監視とクリップボードペーストの処理"""
    
    @staticmethod
    def paste_text(text: str, auto_enter: bool, target_hwnd: int, result_callback, status_callback, silence_label: str):
        if not text:
            result_callback(silence_label, "#bdc3c7")
            return
            
        old_clip = pyperclip.paste()
        pyperclip.copy(text)
        
        if target_hwnd:
            ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        
        time.sleep(PASTE_DELAY)
        keyboard.press_and_release("ctrl+v")
        
        if auto_enter:
            keyboard.press_and_release("enter")
            
        def restore_clipboard():
            time.sleep(CLIPBOARD_RESTORE_DELAY)
            pyperclip.copy(old_clip)
            
        threading.Thread(target=restore_clipboard, daemon=True).start()
        result_callback(text, "#2ecc71")
        status_callback(L.get("status_done", "Done"), "#95a5a6")

    @staticmethod
    def force_release_keys():
        """めり込み防止のための全キーリセット"""
        for k in ["ctrl", "right ctrl", "left ctrl", "shift", "alt", "space"]:
            try:
                keyboard.release(k)
            except Exception:
                pass
