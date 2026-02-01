
import re
import string

def clean_text(text: str) -> str:
    """
    Performs basic text cleaning:
    1. Removes URLs
    2. Removes HTML tags
    3. Fixes whitespace
    4. Removes special characters (optional, keeping basic punctuation)
    """
    if not text:
        return ""

    # 1. Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # 2. Remove HTML tags
    text = re.sub(r'<.*?>', '', text)

    # 3. Fix whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # 4. Remove excessive punctuation (optional: e.g. "!!!" -> "!")
    text = re.sub(r'([!?.])\1+', r'\1', text)

    return text

def preprocess_for_sentiment(text: str) -> str:
    """
    Specific preprocessing for sentiment analysis:
    - Basic cleaning
    - Handling some common noise
    """
    text = clean_text(text)
    
    # We might want to keep emoji for sentiment, 
    # but BERTweet handles them. Basic cleaners might strip them.
    # For now, just basic cleaning is fine.
    
    return text
