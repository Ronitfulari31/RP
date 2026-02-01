from datetime import datetime

class GeoLanguageService:
    def __init__(self, db):
        self.db = db

        # Seed data (optional)
        self.STATE_LANG = {
            "Maharashtra": ["mr", "hi"],
            "Tamil Nadu": ["ta"],
            "Karnataka": ["kn"]
        }

        self.CITY_LANG = {
            "Pune": ["mr"],
            "Mumbai": ["mr"]
        }
        
        self.CONTINENT_LANG = {
            "Asia": ["en", "hi", "zh-TW", "ja"],
            "Europe": ["en", "fr", "de", "es", "ru"],
            "Americas": ["en", "es", "pt"],
            "Africa": ["en", "fr", "ar"],
            "Oceania": ["en"],
            "Global": ["en"]
        }

    # ---------------- STATE ----------------
    def get_state_languages(self, state: str) -> list[str]:
        if not state or state == "unknown":
            return []

        if self.db is not None:
            cached = self.db.geo_state_languages.find_one(
                {"state": state},
                {"_id": 0, "languages": 1}
            )
            if cached:
                return cached["languages"]

        langs = self.STATE_LANG.get(state, [])
        if langs and self.db is not None:
            try:
                self.db.geo_state_languages.insert_one({
                    "state": state,
                    "languages": langs,
                    "source": "static",
                    "cached_at": datetime.utcnow()
                })
            except Exception:
                pass # safely ignore duplicate key or other errors

        return langs

    # ---------------- CITY ----------------
    def get_city_languages(self, city: str, state: str | None = None) -> list[str]:
        if not city or city == "unknown":
            return []

        if self.db is not None:
            cached = self.db.geo_city_languages.find_one(
                {"city": city},
                {"_id": 0, "languages": 1}
            )
            if cached:
                return cached["languages"]

        langs = self.CITY_LANG.get(city, [])
        if langs and self.db is not None:
            try:
                self.db.geo_city_languages.insert_one({
                    "city": city,
                    "state": state,
                    "languages": langs,
                    "cached_at": datetime.utcnow()
                })
            except Exception:
                pass

        return langs

    def get_continent_languages(self, continent: str) -> list[str]:
        return self.CONTINENT_LANG.get(continent, [])
