from argostranslate import translate
from langdetect import detect


SUPPORTED_LANGS = {"hi", "zh", "ar", "fr", "es", "ru", "de", "ja", "ko"}

def translate_query_if_needed(query: str) -> dict:
    """
    Deterministically translate query to English if needed.
    Returns both original and translated query.
    """

    result = {
        "original_query": query,
        "translated_query": query,
        "detected_language": "en"
    }

    try:
        lang = detect(query)
        result["detected_language"] = lang

        if lang != "en" and lang in SUPPORTED_LANGS:
            try:
                # Attempt translation
                translated = translate.translate(query, lang, "en")
                if translated and isinstance(translated, str):
                    result["translated_query"] = translated.strip()
            except Exception:
                # Argos might not have the package installed, fail gracefully
                pass

    except Exception:
        # Fail-safe: do nothing, keep original
        pass

    return result
