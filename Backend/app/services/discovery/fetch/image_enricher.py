import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (NewsSentimentBot/1.0)"
}

def is_generic_image(url: str) -> bool:
    """Check if an image URL looks like a generic logo or branded placeholder."""
    if not url:
        return True
    
    generic_keywords = ["logo", "branded", "placeholder", "default", "icon", "avatar", "Inside Science"]
    url_lower = url.lower()
    
    return any(keyword in url_lower for keyword in generic_keywords)

def fetch_image_url(article_url, timeout=6):
    """
    Lightweight resolution of og:image tag from article URL.
    Does NOT perform full parsing or NLP.
    """
    try:
        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=timeout
        )

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Check meta tags
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            image_url = og["content"].strip()
            if not is_generic_image(image_url):
                return image_url

        twitter = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter and twitter.get("content"):
            image_url = twitter["content"].strip()
            if not is_generic_image(image_url):
                return image_url

        # 2. Basic body image fallback
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("http") and not is_generic_image(src):
                return src

    except Exception as e:
        logger.debug(f"Image enrichment failed for {article_url}: {e}")
        return None

    return None
