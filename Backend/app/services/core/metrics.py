"""
NLP Evaluation Metrics Utilities
Provides helper functions for computing various NLP evaluation metrics
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import logging

logger = logging.getLogger(__name__)


def compute_precision_recall_f1(predicted_items: List, gold_items: List) -> Tuple[float, float, float]:
    """
    Compute precision, recall, and F1 score for two lists of items
    
    Args:
        predicted_items: List of predicted items (e.g., entities, keywords)
        gold_items: List of gold standard items
        
    Returns:
        Tuple of (precision, recall, f1_score)
        
    Example:
        >>> pred = ['apple', 'banana', 'cherry']
        >>> gold = ['banana', 'cherry', 'date']
        >>> p, r, f1 = compute_precision_recall_f1(pred, gold)
        >>> # precision = 2/3 (2 correct out of 3 predicted)
        >>> # recall = 2/3 (2 correct out of 3 gold)
    """
    if not predicted_items and not gold_items:
        return 1.0, 1.0, 1.0  # Perfect if both empty
    
    if not predicted_items:
        return 0.0, 0.0, 0.0  # No predictions
    
    if not gold_items:
        # No gold standard - use heuristic quality score
        return 0.5, 0.5, 0.5
    
    # Convert to sets for comparison (case-insensitive)
    pred_set = set([str(item).lower() for item in predicted_items])
    gold_set = set([str(item).lower() for item in gold_items])
    
    # Calculate metrics
    true_positives = len(pred_set.intersection(gold_set))
    
    precision = true_positives / len(pred_set) if pred_set else 0.0
    recall = true_positives / len(gold_set) if gold_set else 0.0
    
    if precision + recall > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0.0
    
    return precision, recall, f1_score


def compute_bleu(reference: str, hypothesis: str, max_n: int = 4) -> Optional[float]:
    """
    Compute BLEU score for translation evaluation
    
    Args:
        reference: Reference (gold standard) translation
        hypothesis: Hypothesis (predicted) translation
        max_n: Maximum n-gram order (default: 4 for BLEU-4)
        
    Returns:
        BLEU score (0.0 to 1.0) or None if inputs are invalid
        
    Note:
        BLEU (Bilingual Evaluation Understudy) measures n-gram overlap
        between reference and hypothesis translations. Higher is better.
        Uses smoothing to handle zero counts in n-grams.
    """
    if not reference or not hypothesis:
        return None
    
    try:
        # Tokenize (simple whitespace split)
        reference_tokens = reference.lower().split()
        hypothesis_tokens = hypothesis.lower().split()
        
        if not reference_tokens or not hypothesis_tokens:
            return 0.0
        
        # Use smoothing function to handle zero counts
        smoothing = SmoothingFunction().method1
        
        # Compute BLEU score
        bleu_score = sentence_bleu(
            [reference_tokens],  # NLTK expects list of references
            hypothesis_tokens,
            smoothing_function=smoothing
        )
        
        return round(bleu_score, 4)
        
    except Exception as e:
        logger.error(f"BLEU computation error: {str(e)}")
        return None


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> Optional[float]:
    """
    Compute cosine similarity between two vectors
    
    Args:
        vec1: First vector (e.g., embedding)
        vec2: Second vector
        
    Returns:
        Cosine similarity (-1.0 to 1.0) or None if inputs are invalid
        
    Note:
        Cosine similarity measures the cosine of the angle between vectors.
        1.0 = identical direction, 0.0 = orthogonal, -1.0 = opposite direction
        Used to measure semantic similarity between embeddings.
    """
    if not vec1 or not vec2:
        return None
    
    if len(vec1) != len(vec2):
        logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
        return None
    
    try:
        # Convert to numpy arrays
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Compute cosine similarity
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        
        similarity = dot_product / (norm_v1 * norm_v2)
        
        return round(float(similarity), 4)
        
    except Exception as e:
        logger.error(f"Cosine similarity computation error: {str(e)}")
        return None


def compute_text_cleaning_quality(cleaned_text: str, original_text: str) -> float:
    """
    Compute text cleaning quality score
    
    Args:
        cleaned_text: Cleaned/preprocessed text
        original_text: Original raw text
        
    Returns:
        Quality score (0.0 to 1.0)
        
    Note:
        Good cleaning should retain 60-100% of original length.
        This is a heuristic metric - actual quality depends on use case.
    """
    if not original_text:
        return 0.0
    
    if not cleaned_text:
        return 0.0
    
    # Calculate length ratio
    cleaned_len = len(cleaned_text)
    original_len = len(original_text)
    
    ratio = cleaned_len / original_len
    
    # Ideal ratio is 0.6 to 1.0
    if 0.6 <= ratio <= 1.0:
        quality = 1.0
    elif ratio < 0.6:
        # Penalize over-aggressive cleaning
        quality = ratio / 0.6
    else:
        # Penalize insufficient cleaning (ratio > 1.0 shouldn't happen)
        quality = 0.7
    
    return round(quality, 3)


def compute_entity_diversity(entities: Dict[str, List]) -> float:
    """
    Compute entity diversity score
    
    Args:
        entities: Dictionary with entity types as keys (e.g., 'persons', 'locations')
        
    Returns:
        Diversity score (0.0 to 1.0)
        
    Note:
        Measures how many different entity types were found.
        Good NER should identify multiple entity types.
    """
    if not entities:
        return 0.0
    
    # Expected entity types
    expected_types = ['persons', 'locations', 'organizations']
    
    # Count how many types have at least one entity
    types_found = sum([
        1 for entity_type in expected_types
        if entities.get(entity_type) and len(entities.get(entity_type, [])) > 0
    ])
    
    diversity = types_found / len(expected_types)
    
    return round(diversity, 3)


def compute_keyword_relevance(keywords: List[str], text: str) -> float:
    """
    Compute keyword relevance score
    
    Args:
        keywords: List of extracted keywords
        text: Original text
        
    Returns:
        Relevance score (0.0 to 1.0)
        
    Note:
        Measures how many keywords actually appear in the text.
        Good keyword extraction should produce keywords present in text.
    """
    if not keywords or not text:
        return 0.0
    
    text_lower = text.lower()
    
    # Count how many keywords appear in text
    relevant_count = sum([
        1 for keyword in keywords
        if keyword.lower() in text_lower
    ])
    
    relevance = relevant_count / len(keywords)
    
    return round(relevance, 3)
