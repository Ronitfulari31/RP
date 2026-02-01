from app.services.metadata.country_language_service import CountryLanguageService
from app.services.metadata.geo_language_service import GeoLanguageService
from app.services.discovery.fetch.resolver_metrics import log_resolver_metrics
import logging

logger = logging.getLogger(__name__)


def resolve_context(params: dict, db=None) -> dict:
    if db is not None:
        log_resolver_metrics(db, "resolver_calls_total")
        geo_lang_service = GeoLanguageService(db)
        country_lang_service = CountryLanguageService(db)
    else:
        geo_lang_service = GeoLanguageService(None)
        country_lang_service = CountryLanguageService(None)

    def get_single(key, default="unknown"):
        val = params.get(key, default)
        if isinstance(val, list) and len(val) > 0:
            return val[0]
        return val

    city = get_single("city")
    state = get_single("state")
    country = get_single("country")
    continent = get_single("continent")

    # ---------------- SCOPE ----------------
    if city != "unknown":
        scope = "city"
    elif state != "unknown":
        scope = "state"
    elif country != "unknown":
        scope = "country"
    elif continent != "unknown":
        scope = "continent"
    else:
        scope = "global"

    # ---------------- LANGUAGE RESOLUTION ----------------
    user_provided_language = params.get("language")
    if user_provided_language:
        languages = [user_provided_language]
        language_source = "user_provided"
    else:
        languages = []

        if city != "unknown":
            languages += geo_lang_service.get_city_languages(city, state)
            languages += geo_lang_service.get_state_languages(state)
            languages += country_lang_service.get_country_languages(country)

        elif state != "unknown":
            languages += geo_lang_service.get_state_languages(state)
            languages += country_lang_service.get_country_languages(country)

        elif country != "unknown":
            languages += country_lang_service.get_country_languages(country)

        elif continent != "unknown":
            languages += geo_lang_service.get_continent_languages(continent)

        # Remove fallback - don't default to English
        # if not languages:
        #     languages = ["en"]

        languages = list(dict.fromkeys(languages))
        language_source = "inferred" if languages else "none"

    category = params.get("category") or "unknown"
    source = params.get("source") or "unknown"
    analyzed = params.get("analyzed") or "false"

    # ---------------- LOGGING ----------------
    if db is not None and language_source == "inferred" and not languages:
        log_resolver_metrics(db, "resolver_no_languages_found")

    logger.info(
        "[resolver] scope=%s | city=%s | state=%s | country=%s | languages=%s | language_source=%s | category=%s | source=%s | analyzed=%s",
        scope, city, state, country, languages, language_source, category, source, analyzed
    )

    return {
        "scope": scope,
        "continent": continent,
        "country": country,
        "state": state,
        "city": city,
        "language": languages,  # For context/analytics/UI
        "language_source": language_source,  # Track source
        "category": category,
        "source": source,
        "analyzed": analyzed
    }
