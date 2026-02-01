# app/services/fetch/extraction.py
import logging
import requests
import trafilatura
from bs4 import BeautifulSoup
from newspaper import Article, Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# ARTICLE EXTRACTION
# ---------------------------------------------------------

def extract_article_package(url: str):
    if not url:
        return {"success": False}, None

    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            content = trafilatura.extract(downloaded)
            if content:
                return {"success": True, "content": content}, url
    except Exception:
        logger.warning("Trafilatura extraction failed")

    try:
        config = Config()
        config.browser_user_agent = "Mozilla/5.0"
        article = Article(url, config=config)
        article.download()
        article.parse()
        if article.text:
            return {"success": True, "content": article.text}, article.canonical_link or url
    except Exception:
        logger.warning("Newspaper extraction failed")

    return {"success": False}, url

# ---------------------------------------------------------
# ARTICLE IMAGE EXTRACTION
# ---------------------------------------------------------

def is_generic_image(url: str) -> bool:
    """Check if an image URL looks like a generic logo or branded placeholder."""
    if not url:
        return True
    
    generic_keywords = ["logo", "branded", "placeholder", "default", "icon", "avatar", "Inside Science"]
    url_lower = url.lower()
    
    return any(keyword in url_lower for keyword in generic_keywords)

def extract_article_image(url: str):
    if not url:
        return None

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Try meta tags first
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            image_url = og["content"]
            if not is_generic_image(image_url):
                return image_url

        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            image_url = tw["content"]
            if not is_generic_image(image_url):
                return image_url

        # 2. Try to find the first large image in the body as fallback
        # This is very basic; newspaper3k usually does this better if used properly
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and src.startswith("http") and not is_generic_image(src):
                # Try to avoid very small images (icons)
                width = img.get("width")
                if width and width.isdigit() and int(width) < 100:
                    continue
                return src

    except Exception:
        logger.warning("Article image extraction failed", exc_info=True)

    return None
