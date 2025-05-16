from deep_translator import GoogleTranslator
from langdetect import detect

TRANSLATABLE_FIELDS = {"title", "description", "acceptance_criteria"}

def should_translate(text: str, target_lang: str) -> bool:
    try:
        detected = detect(text)
        return detected != target_lang
    except:
        return False

def translate_text(text: str, target_lang: str) -> str:
    if should_translate(text, target_lang):
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    return text

def translate_selected_fields(data, target_lang="en"):
    if isinstance(data, dict):
        translated_data = {}
        for key, value in data.items():
            if key in TRANSLATABLE_FIELDS:
                if isinstance(value, str):
                    translated_data[key] = translate_text(value, target_lang)
                elif isinstance(value, list):
                    translated_data[key] = [translate_text(v, target_lang) if isinstance(v, str) else translate_selected_fields(v, target_lang) for v in value]
                else:
                    translated_data[key] = value
            else:
                translated_data[key] = translate_selected_fields(value, target_lang)
        return translated_data

    elif isinstance(data, list):
        return [translate_selected_fields(item, target_lang) for item in data]

    return data
