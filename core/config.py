import os
import ctypes
from core.i18n import L

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# 言語辞書（L）を使用してモデルオプションとスペックを初期化
MODEL_OPTIONS = [
    f"large-v3 ({L.get('spec_large', '').split('│')[-1].split(':')[1].strip() if '│' in L.get('spec_large', '') else 'highest'})",
    f"medium ({L.get('spec_medium', '').split('│')[-1].split(':')[1].strip() if '│' in L.get('spec_medium', '') else 'high'})",
    f"small ({L.get('spec_small', '').split('│')[-1].split(':')[1].strip() if '│' in L.get('spec_small', '') else 'fast'})",
    f"base ({L.get('spec_base', '').split('│')[-1].split(':')[1].strip() if '│' in L.get('spec_base', '') else 'very fast'})",
    f"tiny ({L.get('spec_tiny', '').split('│')[-1].split(':')[1].strip() if '│' in L.get('spec_tiny', '') else 'fastest'})"
]

MODEL_SPECS = {
    "large-v3": L.get("spec_large", ""),
    "medium":   L.get("spec_medium", ""),
    "small":    L.get("spec_small", ""),
    "base":     L.get("spec_base", ""),
    "tiny":     L.get("spec_tiny", ""),
}

def _get_total_ram_gb() -> float:
    """WindowsのメインメモリRAM容量をGB単位で返す。"""
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(stat)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return stat.ullTotalPhys / (1024 ** 3)

def _recommend_model() -> str:
    """PCのRAM容量とCPUスレッド数に基づいて推奨モデルを返す。"""
    ram_gb = _get_total_ram_gb()
    logical_cores = os.cpu_count() or 4
    if ram_gb >= 64 and logical_cores > 12:
        return MODEL_OPTIONS[0]  # large-v3
    elif ram_gb >= 8:
        return MODEL_OPTIONS[1]  # medium
    elif ram_gb >= 4:
        return MODEL_OPTIONS[2]  # small
    else:
        return MODEL_OPTIONS[3]  # base
