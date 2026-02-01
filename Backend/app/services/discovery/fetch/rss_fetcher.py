# RSS Fetcher
import feedparser
import socket
import logging

logger = logging.getLogger(__name__)

# Set global timeout for feed fetching
socket.setdefaulttimeout(10)

def is_generic_image(url: str) -> bool:
    """Check if an image URL looks like a generic logo or branded placeholder."""
    if not url:
        return True
    
    generic_keywords = ["logo", "branded", "placeholder", "default", "icon", "avatar", "Inside Science"]
    url_lower = url.lower()
    
    return any(keyword in url_lower for keyword in generic_keywords)

def extract_image_url(entry):
    """
    Extracts article image URL from RSS entry.
    Checks media:content, media:thumbnail, enclosures, and feed-level image.
    Uses getattr for defensive property access.
    """
    # 1. media:content
    media_content = getattr(entry, "media_content", [])
    if media_content:
        for media in media_content:
            if "url" in media:
                url = media["url"]
                if not is_generic_image(url):
                    return url

    # 2. media:thumbnail
    media_thumbnail = getattr(entry, "media_thumbnail", [])
    if media_thumbnail:
        url = media_thumbnail[0].get("url")
        if not is_generic_image(url):
            return url

    # 3. enclosure
    enclosures = getattr(entry, "enclosures", [])
    if enclosures:
        for enc in enclosures:
            if enc.get("type", "").startswith("image"):
                url = enc.get("href")
                if not is_generic_image(url):
                    return url

    # 4. feed-level image (weak fallback)
    image = getattr(entry, "image", None)
    if image:
        url = image.get("href")
        if not is_generic_image(url):
            return url

    return None


def fetch_rss_articles(feed_url: str, source_name: str = None):
    """
    Fetch articles metadata from RSS feed.
    Returns list of dicts similar to NewsAPI output.
    """
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.error(f"RSS fetch failed for {feed_url}: {e}")
        return []

    # Check for parsing errors
    if getattr(feed, "bozo", 0):
        logger.warning(
            f"RSS parsing issue ({feed_url}): {getattr(feed, 'bozo_exception', 'Unknown')}"
        )

    articles = []

    # feedparser.parse always returns a feed object even on failure
    entries = getattr(feed, "entries", [])
    for entry in entries:
        articles.append({
            "title": entry.get("title"),
            "original_url": entry.get("link"),
            "published_date": entry.get("published"),
            "rss_summary": entry.get("summary", ""),
            "image_url": extract_image_url(entry)
        })

    return articles
