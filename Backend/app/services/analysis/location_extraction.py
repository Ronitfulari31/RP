"""
Location Extraction Service
Level-1: Extract location mentions using spaCy
Level-2: Enrich and normalize into city/state/country using geocoder
(English-normalized, language-agnostic)
"""

import logging
import time
import os
from typing import Dict, List
from functools import lru_cache
from pymongo import MongoClient
from app.services.analysis.ner_service import ner_service

logger = logging.getLogger(__name__)


# Geographical Mappings for Inference (The "Connected Vector" Intelligence)
CITY_TO_STATE = {
    "pune": "Maharashtra", "mumbai": "Maharashtra", "bengaluru": "Karnataka",
    "chennai": "Tamil Nadu", "hyderabad": "Telangana", "delhi": "Delhi",
    "kolkata": "West Bengal", "san francisco": "California", "new york": "New York",
    "london": "England", "toronto": "Ontario", "berlin": "Berlin", "paris": "Île-de-France"
}

STATE_TO_COUNTRY = {
    "maharashtra": "India", "karnataka": "India", "tamil nadu": "India",
    "telangana": "India", "california": "USA", "ontario": "Canada",
    "england": "United Kingdom", "berlin": "Germany", "texas": "USA"
}

COUNTRY_TO_CONTINENT = {
    "india": "Asia", "china": "Asia", "japan": "Asia", "south korea": "Asia", 
    "russia": "Europe", "united kingdom": "Europe", "uk": "Europe", 
    "france": "Europe", "germany": "Europe", "italy": "Europe", 
    "spain": "Europe", "usa": "North America", "united states": "North America", 
    "canada": "North America", "brazil": "South America", "argentina": "South America", 
    "nigeria": "Africa", "south africa": "Africa", "egypt": "Africa", "kenya": "Africa",
    "australia": "Oceania"
}

class LocationExtractionService:
    """Service for hierarchical location extraction"""

    def __init__(self):
        self.nlp = None
        self.geolocator = None
        self.geocode = None
        
        # MongoDB Cache Setup
        self.db = None
        self._db_initialized = False

    def _init_db(self):
        """Initialize MongoDB connection for persistent Geo-Knowledge Graph"""
        if self._db_initialized:
            return
        try:
            uri = os.getenv("MONGODB_URI")
            db_name = os.getenv("MONGODB_DB_NAME", "news_sentiment_intelligence_db")
            if uri:
                client = MongoClient(uri, serverSelectionTimeoutMS=2000)
                self.client = client
                self.db = client[db_name]
                self._db_initialized = True
                logger.info("✅ Geo-Knowledge Graph (MongoDB) connected.")
            else:
                logger.warning("⚠️ MONGODB_URI not found. Geo-Knowledge cache disabled.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Geo-Knowledge DB: {e}")
            self._db_initialized = True # Mark as tried

    # -------------------------------------------------
    # spaCy
    # -------------------------------------------------

    def _load_spacy_model(self):
        if self.nlp is not None:
            return
        try:
            import spacy
            logger.info("🔄 Loading SpaCy (Location) model (en_core_web_sm)...")
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ SpaCy (Location) model loaded")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Run: python -m spacy download en_core_web_sm")

    def extract_entities(self, text: str) -> List[Dict]:
        self._load_spacy_model()
        if self.nlp is None:
            logger.error("spaCy model not loaded")
            return []

        try:
            doc = self.nlp(text)
            return [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                }
                for ent in doc.ents
            ]
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    # -------------------------------------------------
    # LEVEL-1 → LEVEL-2 PIPELINE
    # -------------------------------------------------

    def extract_locations(self, text: str) -> Dict:
        start_time = time.time()

        try:
            if not text or not text.strip():
                return {"location": None, "extraction_time": 0.0}

            # -------- LEVEL-1: V2 NER DETECTION (GLiNER) --------
            # Call the upgraded NER service which already handles Triple-Tier GPU logic
            ner_result = ner_service.extract_entities(text)
            detected_entities = ner_result.get("entities", [])
            ner_status = ner_result.get("status")

            raw_locations = []
            seen = set()

            for ent in detected_entities:
                # GLiNER labels are uppercase: LOCATION, CITY, COUNTRY, CONTINENT
                # SpaCy labels are: GPE, LOC
                label = ent["label"].upper()
                if label not in {"GPE", "LOC", "LOCATION", "CITY", "COUNTRY", "CONTINENT"}:
                    continue

                value = ent["text"].strip()
                key = value.lower()

                if key in seen:
                    continue

                seen.add(key)
                raw_locations.append({
                    "entity_text": value,
                    "location_type": self._classify_location_type(value)
                })

            # -------- LEVEL-2: ENRICHMENT --------
            enriched = self._enrich_locations(raw_locations)

            extraction_time = round(time.time() - start_time, 3)

            logger.info(
                f"Location extraction completed | "
                f"Level-1={len(raw_locations)} | "
                f"Enriched={'yes' if enriched else 'no'} | "
                f"NER_Status={ner_status} | "
                f"time={extraction_time}s"
            )

            return {
                "location": enriched,
                "extraction_time": extraction_time,
                "status": ner_status, # Propagate V2 status
                "role": ner_result.get("role"),
                "continent": enriched.get("continent") if enriched else "Continent not mentioned"
            }

        except Exception as e:
            logger.error(f"Location extraction failed: {e}")
            return {
                "location": None,
                "extraction_time": round(time.time() - start_time, 3),
                "error": str(e)
            }

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------

    def _classify_location_type(self, location_text: str) -> str:
        value = location_text.lower()

        continents = {"asia", "africa", "europe", "north america", "south america", "oceania", "antarctica"}
        countries = {
            "india", "usa", "united states", "china", "japan", "uk",
            "united kingdom", "france", "germany", "spain", "italy",
            "russia", "brazil", "mexico", "australia", "canada"
        }

        indian_states = {
            "maharashtra", "karnataka", "tamil nadu", "kerala",
            "gujarat", "rajasthan", "punjab", "haryana",
            "uttar pradesh", "bihar", "west bengal", "odisha"
        }

        if value in continents:
            return "continent"
        if value in countries:
            return "country"
        if value in indian_states:
            return "state"
        return "city"

    @lru_cache(maxsize=512)
    def _cached_geocode(self, place: str, country_codes=None):
        if self.geolocator is None:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter
            
            self.geolocator = Nominatim(user_agent="news_location_enrichment")
            self.geocode = RateLimiter(
                self.geolocator.geocode,
                min_delay_seconds=1,
                swallow_exceptions=False # Visible errors for debugging
            )
            
        # ✅ FIX: Force English at REQUEST LEVEL (supported by geopy)
        logger.info(f"🌐 [GEO-LOC] Geocoding request for: '{place}' (Bias: {country_codes})")
        return self.geocode(
            place.strip(),
            addressdetails=True,
            language="en",
            country_codes=country_codes,
            timeout=10
        )

    # -------------------------------------------------
    # LEVEL-2 ENRICHMENT (WITH PERSISTENT CACHE)
    # -------------------------------------------------

    def _lookup_cache(self, entity_text: str) -> Dict | None:
        """Lookup persistent hierarchical chain from DB"""
        self._init_db()
        if self.db is None:
            return None
        try:
            # Search by lower-cased normalize name
            entity_key = entity_text.strip().lower()
            cached = self.db.geo_knowledge_graph.find_one({"entity_key": entity_key})
            if cached:
                logger.info(f"⚡ [GEO-CACHE] Hit for '{entity_text}'")
                # Return essential fields
                return {
                    "city": cached.get("city"),
                    "state": cached.get("state"),
                    "country": cached.get("country"),
                    "continent": cached.get("continent"),
                    "confidence": cached.get("confidence", 1.0),
                    "chain_source": "cached_vector"
                }
        except Exception as e:
            logger.debug(f"Cache lookup failed: {e}")
        return None

    def _save_cache(self, entity_text: str, entity_type: str, chain: Dict):
        """Save discovered hierarchical chain to persistent DB"""
        self._init_db()
        if self.db is None:
            return
        try:
            entity_key = entity_text.strip().lower()
            self.db.geo_knowledge_graph.update_one(
                {"entity_key": entity_key},
                {
                    "$set": {
                        "entity_text": entity_text,
                        "entity_type": entity_type,
                        "city": chain.get("city"),
                        "state": chain.get("state"),
                        "country": chain.get("country"),
                        "continent": chain.get("continent"),
                        "confidence": chain.get("confidence"),
                        "updated_at": time.time()
                    }
                },
                upsert=True
            )
            logger.info(f"💾 [GEO-CACHE] Saved hierarchical vector for '{entity_text}'")
        except Exception as e:
            logger.debug(f"Cache save failed: {e}")

    def _infer_hierarchy_fallbacks(self, chain: Dict) -> Dict:
        """
        Intelligence Fallbacks: If geocoder skips a level, use internal maps to fill the gap.
        Chain: City -> State -> Country -> Continent
        """
        # 1. City -> State
        city = str(chain.get("city") or "").strip().lower()
        if city in CITY_TO_STATE and ("not mentioned" in str(chain.get("state")).lower()):
            chain["state"] = CITY_TO_STATE[city]
            logger.info(f"🧠 [GEO-INTEL] Inferred State '{chain['state']}' from City '{chain['city']}'")

        # 2. State -> Country
        state = str(chain.get("state") or "").strip().lower()
        if state in STATE_TO_COUNTRY and ("not mentioned" in str(chain.get("country")).lower()):
            chain["country"] = STATE_TO_COUNTRY[state]
            logger.info(f"🧠 [GEO-INTEL] Inferred Country '{chain['country']}' from State '{chain['state']}'")

        # 3. Country -> Continent
        country = str(chain.get("country") or "").strip().lower()
        if country in COUNTRY_TO_CONTINENT and ("not mentioned" in str(chain.get("continent")).lower()):
            chain["continent"] = COUNTRY_TO_CONTINENT[country]
            logger.info(f"🧠 [GEO-INTEL] Inferred Continent '{chain['continent']}' from Country '{chain['country']}'")
        
        return chain

    def _enrich_locations(self, locations: List[Dict]) -> Dict | None:
        """
        Connected Vector Logic: Resolves detected locations into a primary city/state/country chain.
        Hierarchy: City ➔ State ➔ Country ➔ Continent
        """
        self._init_db()
        
        # Hierarchical Sort
        sorted_locations = sorted(
            locations,
            key=lambda x: 0 if x["location_type"] == "city" else (
                1 if x["location_type"] == "state" else (
                    2 if x["location_type"] == "country" else 3
                )
            )
        )

        for loc in sorted_locations:
            try:
                # --- PERSISTENT CACHE LOOKUP ---
                cached_chain = self._lookup_cache(loc["entity_text"])
                if cached_chain:
                    return cached_chain

                mention_type = loc["location_type"]

                # --- GEOCODING RESOLUTION (IF NOT CACHED) ---
                # 🔍 Contextual Scoring: Pass Country bias to Geocoder if known
                source_country = "global" # Default if context not passed
                bias_code = None

                geo = self._cached_geocode(loc["entity_text"], country_codes=bias_code)
                
                address = {}
                if geo and geo.raw:
                    address = geo.raw.get("address", {})
                    logger.info(f"📍 [GEO-DEBUG] Raw Address (Bias={bias_code}) for '{loc['entity_text']}': {address}")
                
                # Normalize values from Geocoder
                g_city = address.get("city") or address.get("town") or address.get("city_district") or address.get("suburb") or address.get("municipality")
                g_state = address.get("state") or address.get("state_district") or address.get("province")
                g_country = address.get("country")
                g_continent = address.get("continent")
                
                # --- GEOGRAPHICAL INFERENCE (Intelligence) ---
                res = {
                    "city": g_city or (loc["entity_text"] if mention_type == "city" else "City not mentioned specifically in article"),
                    "state": g_state or (loc["entity_text"] if mention_type == "state" else "State not mentioned specifically"),
                    "country": g_country or (loc["entity_text"] if mention_type == "country" else "Country not mentioned"),
                    "continent": g_continent or "Continent not mentioned",
                    "confidence": 0.95 if mention_type == "city" else 0.85,
                    "chain_source": f"{mention_type}_level"
                }

                # Apply Intelligence Fallbacks (THE HEART OF THE CONNECTED VECTOR)
                res = self._infer_hierarchy_fallbacks(res)

                # 🟢 FEEDBACK FIX: Accuracy Boost - Capital City Priority
                # If geocoder returns "City not mentioned" but we are certain about the country,
                # we don't just return. We try to find the capital if appropriate.
                if res.get("city") == "City not mentioned specifically in article" and res.get("country") != "Country not mentioned":
                    capitals = {"india": "New Delhi", "usa": "Washington D.C.", "uk": "London", "france": "Paris"}
                    country_key = res["country"].lower()
                    if country_key in capitals:
                        logger.info(f"[GEO_BOOST] Defaulting to Capital '{capitals[country_key]}' for high-conf Country '{res['country']}'")
                        res["city"] = capitals[country_key]

                # Check if we actually have anything besides "Not mentioned"
                has_intel = any(v for k, v in res.items() if k in ["city", "state", "country", "continent"] and "Not mentioned" not in str(v))
                
                if has_intel:
                    self._save_cache(loc["entity_text"], mention_type, res)
                    return res

            except Exception as e:
                import traceback
                logger.warning(f"Connected Vector resolution failed for {loc['entity_text']}: {e}\n{traceback.format_exc()}")

            except Exception as e:
                import traceback
                logger.warning(f"Connected Vector resolution failed for {loc['entity_text']}: {e}\n{traceback.format_exc()}")

        return None

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    def get_location_summary(self, locations: List[Dict]) -> Dict:
        summary = {
            "total_locations": len(locations),
            "cities": [],
            "states": [],
            "countries": []
        }

        for loc in locations:
            if loc.get("city"):
                summary["cities"].append(loc["city"])
            if loc.get("state"):
                summary["states"].append(loc["state"])
            if loc.get("country"):
                summary["countries"].append(loc["country"])

        summary["cities"] = list(set(summary["cities"]))
        summary["states"] = list(set(summary["states"]))
        summary["countries"] = list(set(summary["countries"]))

        return summary


# Singleton instance
location_extraction_service = LocationExtractionService()
