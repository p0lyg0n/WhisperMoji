import os
import json
import locale

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_language() -> tuple[dict, str]:
    # 環境変数LANG_OVERRIDEがあれば優先
    override = os.environ.get("LANG_OVERRIDE")
    if override:
        os_lang = override
    else:
        try:
            os_lang = locale.getdefaultlocale()[0] or "en"
        except Exception:
            os_lang = "en"
    
    lang_code = os_lang.split("_")[0]
    lang_file = os.path.join(BASE_DIR, "lang", f"{lang_code}.json")
    if not os.path.exists(lang_file):
        lang_file = os.path.join(BASE_DIR, "lang", "en.json")
    
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f), lang_code
    except Exception:
        return {}, "en"

L, LANG_CODE = _load_language()
