"""
Event Detection Service
Keyword-based hybrid classifier for disaster event classification
Events: flood, fire, earthquake, landslide, terror_attack, other
"""

import logging
import time
from typing import Dict, List
import re

logger = logging.getLogger(__name__)


class EventDetectionService:
    """Service for disaster event classification"""

    def __init__(self):
        # Disaster event keywords mapping
        self.event_keywords = {
            'flood': [
                'flood', 'flooding', 'flooded', 'water', 'rain', 'rainfall', 'heavy rain',
                'monsoon', 'overflow', 'river', 'dam', 'inundation', 'waterlogging',
                'submerged', 'drowned', 'drowning', 'rescue', 'evacuation', 'shelter',
                'बाढ़', 'पानी', 'बारिश'
            ],
            'fire': [
                'fire', 'burning', 'burnt', 'flame', 'smoke', 'blaze', 'wildfire',
                'forest fire', 'arson', 'explosion', 'burn', 'inferno', 'firefighter',
                'extinguish', 'ignite', 'combustion'
            ],
            'earthquake': [
                'earthquake', 'quake', 'tremor', 'seismic', 'magnitude', 'richter',
                'epicenter', 'aftershock', 'tsunami', 'shaking', 'ground', 'collapse',
                'building collapse', 'rubble', 'भूकंप'
            ],
            'landslide': [
                'landslide', 'mudslide', 'avalanche', 'debris', 'slope', 'hill',
                'mountain', 'rock fall', 'soil', 'erosion', 'collapse', 'buried',
                'भूस्खलन'
            ],
            'terror_attack': [
                'attack', 'terror', 'terrorist', 'bombing', 'blast', 'shooting',
                'shooter', 'gunfire', 'explosion', 'violence', 'victim', 'casualties',
                'injured', 'killed', 'death', 'assault', 'hostage', 'militant'
            ]
        }

        # Pre-trained simple classifier (will be replaced with real data if available)
        self.vectorizer = None
        self.classifier = None
        self._initialized = False

    def _initialize_baseline_classifier(self):
        """Initialize a baseline classifier using keyword examples"""
        if self._initialized:
            return
            
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            
            training_texts = []
            training_labels = []

            for event_type, keywords in self.event_keywords.items():
                for keyword in keywords[:5]:  # Use first 5 keywords as examples
                    training_texts.append(keyword)
                    training_labels.append(event_type)

            self.vectorizer = TfidfVectorizer(max_features=100)
            X = self.vectorizer.fit_transform(training_texts)

            self.classifier = MultinomialNB()
            self.classifier.fit(X, training_labels)
            self._initialized = True
            logger.info("==========================================================")
            logger.info("Baseline event classifier initialized (Lazy)")
            logger.info("==========================================================")

        except Exception as e:
            logger.info("==========================================================")
            logger.error(f"Failed to initialize baseline classifier: {e}")
            logger.info("==========================================================")

    def classify_by_keywords(self, text: str) -> Dict:
        text_lower = text.lower()
        event_scores = {}

        for event_type, keywords in self.event_keywords.items():
            score = 0
            matched_keywords = []

            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, text_lower))

                if matches > 0:
                    score += matches
                    matched_keywords.append(keyword)

            if score > 0:
                event_scores[event_type] = {
                    'score': score,
                    'matched_keywords': matched_keywords
                }

        if not event_scores:
            return {
                'event_type': 'other',
                'confidence': 0.0,
                'method': 'keyword',
                'matched_keywords': []
            }

        best_event = max(event_scores.items(), key=lambda x: x[1]['score'])
        event_type = best_event[0]
        score = best_event[1]['score']
        matched_keywords = best_event[1]['matched_keywords']

        word_count = len(text.split())
        if word_count < 20:
            confidence = min(score * 0.4, 1.0)
        else:
            confidence = min(score / max(word_count, 1), 1.0)

        return {
            'event_type': event_type,
            'confidence': round(confidence, 3),
            'method': 'keyword',
            'matched_keywords': matched_keywords[:5]
        }

    def classify_by_ml(self, text: str) -> Dict:
        try:
            self._initialize_baseline_classifier()
            if self.vectorizer is None or self.classifier is None:
                return None

            X = self.vectorizer.transform([text])
            predicted_event = self.classifier.predict(X)[0]
            probabilities = self.classifier.predict_proba(X)[0]

            return {
                'event_type': predicted_event,
                'confidence': round(max(probabilities), 3),
                'method': 'ml'
            }

        except Exception as e:
            logger.info("==========================================================")
            logger.error(f"ML classification failed: {e}")
            logger.info("==========================================================")
            return None

    def classify(self, text: str, method: str = 'hybrid') -> Dict:
        start_time = time.time()

        try:
            if not text or len(text.strip()) == 0:
                return {
                    'event_type': 'other',
                    'confidence': 0.0,
                    'method': method,
                    'classification_time': 0.0,
                    'error': 'Empty text'
                }

            result = None

            if method == 'hybrid':
                keyword_result = self.classify_by_keywords(text)

                if keyword_result['confidence'] > 0.3:
                    result = keyword_result
                else:
                    ml_result = self.classify_by_ml(text)

                    if ml_result and ml_result['event_type'] == keyword_result['event_type']:
                        result = keyword_result
                        result['confidence'] = min(keyword_result['confidence'] + 0.2, 1.0)
                        result['method'] = 'hybrid'
                    else:
                        result = keyword_result

            elif method == 'keyword':
                result = self.classify_by_keywords(text)

            elif method == 'ml':
                result = self.classify_by_ml(text) or self.classify_by_keywords(text)

            result['classification_time'] = round(time.time() - start_time, 3)
            logger.info("==========================================================")
            logger.info(f"Event classified: {result['event_type']} (confidence: {result['confidence']})")
            logger.info("==========================================================")
            return result

        except Exception as e:
            return {
                'event_type': 'other',
                'confidence': 0.0,
                'method': method,
                'classification_time': round(time.time() - start_time, 3),
                'error': str(e)
            }

    def get_event_types(self) -> List[str]:
        return ['flood', 'fire', 'earthquake', 'landslide', 'terror_attack', 'other']


# ------------------------------------------------------------------
# ✅ LAZY SINGLETON (ONLY ADDITION)
# ------------------------------------------------------------------

_event_detection_service_instance = None


def get_event_detection_service() -> EventDetectionService:
    global _event_detection_service_instance
    if _event_detection_service_instance is None:
        _event_detection_service_instance = EventDetectionService()
    return _event_detection_service_instance
