import bpy
import os
import json

translations = {}  # 保存整个 JSON


def load_language():
    global translations
    path = os.path.join(os.path.dirname(__file__), "translations.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            translations = json.load(f)
    except Exception:
        translations = {}
    print(f"translations: {translations}")


def _(text):
    blender_lang = bpy.app.translations.locale
    # 简单映射到 JSON 里的 key
    if blender_lang.startswith("zh"):
        lang = "zh"
    else:
        lang = "en"
    # print(f"当前文本: {text}, 翻译语言: {lang},是否存在: {text in translations}")
    if text in translations:
        return translations[text].get(lang, text)
    return text


def _f(text, **kwargs):
    return _(text).format(**kwargs)
