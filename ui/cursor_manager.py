import ctypes
import atexit

class CursorManager:
    """録音中・解析中をマウスカーソルで表示する。"""

    _OCR_NORMAL = 32512
    _OCR_IBEAM = 32513
    _OCR_CROSS = 32515
    _OCR_APPSTARTING = 32650
    _IMAGE_CURSOR = 2
    _SPI_SETCURSORS = 0x0057

    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._modified = False
        atexit.register(self.restore)

    def set_recording(self):
        self._replace(self._OCR_CROSS, self._OCR_IBEAM)
        self._replace(self._OCR_CROSS, self._OCR_NORMAL)
        self._modified = True

    def set_processing(self):
        self._replace(self._OCR_APPSTARTING, self._OCR_IBEAM)
        self._replace(self._OCR_APPSTARTING, self._OCR_NORMAL)
        self._modified = True

    def restore(self):
        if self._modified:
            self._user32.SystemParametersInfoW(self._SPI_SETCURSORS, 0, None, 0)
            self._modified = False

    def _replace(self, source_id: int, target_id: int):
        source = self._user32.LoadCursorW(0, source_id)
        if source:
            copy = self._user32.CopyImage(source, self._IMAGE_CURSOR, 0, 0, 0)
            if copy:
                self._user32.SetSystemCursor(copy, target_id)
