import requests
from functools import lru_cache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

REST_COUNTRIES_API = "https://restcountries.com/v3.1/name/{}"


class CountryLanguageService:
    def __init__(self, db):
        self.db = db
        self.common_countries = {
            "India": ["hi", "en"],
            "United States": ["en"],
            "China": ["zh-TW", "en"],
            "France": ["fr", "en"],
            "Spain": ["es", "en"],
            "Germany": ["de", "en"],
            "Russia": ["ru", "en"],
            "Japan": ["ja", "en"],
            "Indonesia": ["id", "en"],
            "Netherlands": ["nl", "en"],
            "Brazil": ["pt", "en"],
            "United Kingdom": ["en"]
        }

        # ISO-639-3 → ISO-639-1 (NewsAPI compatible)
        # Expanded to include more Indian languages
        self.iso_map = {
            "eng": "en",
            "hin": "hi",
            "por": "pt",
            "fra": "fr",
            "deu": "de",
            "spa": "es",
            "ara": "ar",
            "rus": "ru",
            "jpn": "ja",
            "zho": "zh-TW",
            # Indian languages
            "tam": "ta",  # Tamil
            "tel": "te",  # Telugu
            "mar": "mr",  # Marathi
            "ben": "bn",  # Bengali
            "guj": "gu",  # Gujarati
            "kan": "kn",  # Kannada
            "mal": "ml",  # Malayalam
            "ori": "or",  # Odia
            "pan": "pa",  # Punjabi
            "urd": "ur",  # Urdu
        }

    # -------------------------------
    # IN-MEMORY CACHE (FAST PATH)
    # -------------------------------
    @lru_cache(maxsize=256)
    def _memory_cache(self, country: str) -> list[str]:
        return self._fetch_country_languages(country)

    # -------------------------------
    # MAIN ENTRY
    # -------------------------------
    def get_country_languages(self, country: str) -> list[str]:
        if not country or country == "unknown" or country == "global" or country == "middle_east" or country == "europe" or country == "americas":
            return []

        # Normalize country name to title case for consistent caching
        normalized_country = country.title() if country else country

        # 0️⃣ Quick check in common countries map
        if normalized_country in self.common_countries:
            return self.common_countries[normalized_country]

        # 1️⃣ MongoDB cache (persistent) - case-insensitive lookup
        if self.db is not None:
            # Try normalized name first
            cached = self.db.country_languages.find_one(
                {"country": normalized_country},
                {"_id": 0, "languages": 1}
            )
            if not cached:
                # Try case-insensitive lookup as fallback
                cached = self.db.country_languages.find_one(
                    {"country": {"$regex": f"^{country}$", "$options": "i"}},
                    {"_id": 0, "languages": 1}
                )
            if cached:
                logger.info(f"[CountryLanguageService] Cache hit for {country}: {cached['languages']}")
                return cached["languages"]

        # 2️⃣ In-memory + API fallback
        # Use original country name for API call (works with both cases)
        languages = self._memory_cache(country)
        
        logger.info(f"[CountryLanguageService] API result for {country}: {languages}")

        if languages and self.db is not None:
            # Store with normalized name to avoid case mismatches
            try:
                self.db.country_languages.insert_one({
                    "country": normalized_country,
                    "languages": languages,
                    "source": "restcountries",
                    "cached_at": datetime.utcnow()
                })
            except Exception:
                # Ignore duplicate key errors (race condition or already exists)
                pass

        return languages

    # -------------------------------
    # EXTERNAL API CALL (ONE-TIME)
    # -------------------------------
    def _fetch_country_languages(self, country: str) -> list[str]:
        try:
            resp = requests.get(
                REST_COUNTRIES_API.format(country),
                timeout=2
            )
            if resp.status_code != 200:
                logger.warning(f"[CountryLanguageService] API call failed for {country}: status {resp.status_code}")
                return []

            data = resp.json()[0]
            langs = data.get("languages", {})
            
            # Debug: log the full response structure
            logger.info(f"[CountryLanguageService] Full languages object for {country}: {langs}")
            logger.info(f"[CountryLanguageService] API returned language codes for {country}: {list(langs.keys())}")

            resolved = []
            unmapped = []
            for lang_code in langs.keys():
                # REST Countries API v3.1 returns ISO 639-1 codes (2-letter) like "en", "hi"
                # If it's already ISO 639-1 (2-letter), use it directly
                if len(lang_code) == 2:
                    resolved.append(lang_code)
                # If it's ISO 639-3 (3-letter) like "eng", "hin", map it
                elif len(lang_code) == 3:
                    mapped = self.iso_map.get(lang_code)
                    if mapped:
                        resolved.append(mapped)
                    else:
                        unmapped.append(lang_code)
                else:
                    unmapped.append(lang_code)
            
            if unmapped:
                logger.warning(f"[CountryLanguageService] Unmapped language codes for {country}: {unmapped}")

            # Remove duplicates, preserve order
            result = list(dict.fromkeys(resolved))
            logger.info(f"[CountryLanguageService] Mapped languages for {country}: {result}")
            return result

        except Exception as e:
            logger.error(f"[CountryLanguageService] Exception fetching languages for {country}: {e}")
            return []
