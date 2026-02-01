# app/services/fetch/param_builder.py

def build_newsapi_params(context: dict, language: str, api_key: str) -> dict:
    params = {
        "apiKey": api_key,
        "pageSize": 20,
        "language": language
    }

    if context["category"] != "unknown":
        params["category"] = context["category"]

    if context["country"] != "unknown":
        params["country"] = context["country"][:2].lower()

    return params
