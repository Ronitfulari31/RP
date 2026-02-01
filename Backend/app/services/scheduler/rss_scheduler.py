import time
import logging
from app.services.discovery.fetch.rss_fetcher import fetch_rss_articles
from app.services.discovery.fetch.source_selector import select_sources
from app.services.persistence.article_store import ArticleStore


logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_SOURCE = 50


class RSSScheduler:
    def __init__(self, interval_minutes=5):
        self.interval = interval_minutes * 60
        self.article_store = ArticleStore()
        self._paused = False

    def pause(self):
        """Pauses the scheduler's fetching logic."""
        if not self._paused:
            logger.info("=====================================================================")
            logger.info("⏸ RSS Scheduler PAUSED.")
            logger.info("=====================================================================")
            self._paused = True

    def resume(self):
        """Resumes the scheduler's fetching logic."""
        if self._paused:
            logger.info("=====================================================================")
            logger.info("▶ RSS Scheduler RESUMED.")
            logger.info("=====================================================================")
            self._paused = False

    def run_once(self):
        """
        One polling cycle - processes sources SEQUENTIALLY.
        After each source, waits for worker to process pending articles.
        """
        if self._paused:
            return

        from app.services.discovery.fetch.rss_sources import RSS_SOURCES
        from app.coordinator import get_coordinator
        
        coordinator = get_coordinator()

        for source in RSS_SOURCES:
            if self._paused:
                break

            # Only fetch if coordinator allows
            if not coordinator.can_fetch():
                logger.info("=====================================================================")
                logger.debug(f"⏸️  Coordinator blocking fetch - waiting for processing")
                logger.info("=====================================================================")
                time.sleep(5)
                continue

            try:
                # Notify coordinator we're fetching from this source
                coordinator.start_fetching_source(source["name"])
                
                rss_items = fetch_rss_articles(source["feed_url"], source["name"])
                if not rss_items:
                    logger.info(f"   Empty feed for {source['name']}")
                    coordinator.finish_fetching_source(source["name"], 0)
                    continue

                logger.info(f"   Feed analysis: {len(rss_items)} items found")
                stored = 0
                duplicates = 0
                no_image = 0
                
                for item in rss_items:
                    if self._paused:
                        break
                    
                    if stored >= MAX_ARTICLES_PER_SOURCE:
                        break

                    # 🔹 Lazy imports to speed up scheduler startup
                    from app.services.discovery.fetch.image_enricher import fetch_image_url
                    from app.services.analysis.classification.category_classifier import classify_category
                    from app.models.article import Article

                    # 🔹 Image Enrichment (One fast HTTP call)
                    image_url = item.get("image_url") or fetch_image_url(item["original_url"])

                    if not image_url:
                        no_image += 1
                        continue  # ❌ Skip image-less news

                    # 🔹 Content-based category inference (ADD-ONLY)
                    text_for_classification = f"{item.get('title', '')} {item.get('summary', '')}"
                    category_result = classify_category(text_for_classification)

                    article = Article(
                        title=item.get("title"),
                        original_url=item.get("original_url"),
                        source=source["name"],
                        published_date=item.get("published_date"),
                        summary=item.get("summary"),
                        language=source["language"][0], # 🌐 Keep using RSS for language as requested
                        country="global", # 🛠️ Dynamic: Start global, let NLP localize later
                        continent="global", # 🛠️ Dynamic: Start global, let NLP localize later
                        category="unknown", # 🛠️ Dynamic: Start unknown, let NLP classify later
                        image_url=image_url,
                        inferred_category=category_result.get("primary", "unknown"),
                        category_confidence=category_result.get("confidence", 0.0),
                        inferred_categories=category_result.get("labels", []),
                    )

                    if self.article_store.save_if_new(article):
                        stored += 1
                    else:
                        duplicates += 1
                
                if duplicates > 0 or no_image > 0:
                    logger.info(f"   Skipped: {duplicates} duplicates, {no_image} without images")
                
                if stored > 0:
                    logger.info("=====================================================================")
                    logger.info(f"💾 Saved {stored} image-ready articles from {source['name']}")
                    logger.info("=====================================================================")
                
                # Notify coordinator fetch is complete
                coordinator.finish_fetching_source(source["name"], stored)
                
                # 🔹 Wait for worker to process pending articles
                if stored > 0:
                    total_pending = coordinator.get_status()["pending_articles"]
                    logger.info("=====================================================================")
                    logger.info(f"⏸️  Pausing fetch - {stored} from this source, {total_pending} total pending")
                    logger.info("=====================================================================")
                    
                    # Poll until all pending articles are processed
                    max_wait_cycles = 120  # ~10 minutes max wait
                    wait_cycle = 0
                    
                    while coordinator.get_status()["state"] == coordinator.PROCESSING:
                        if wait_cycle >= max_wait_cycles:
                            logger.info("=====================================================================")
                            logger.warning("⚠️  Max wait time reached - resuming fetch")
                            logger.info("=====================================================================")
                            break
                        time.sleep(5)
                        wait_cycle += 1
                    
                    logger.info("=====================================================================")
                    logger.info(f"▶️  Worker finished - resuming fetch")
                    logger.info("=====================================================================")
                
                # Small pause between sources
                time.sleep(1.5)
                    
            except Exception as e:
                logger.info("=====================================================================")
                logger.error(
                    f"❌ Scheduler error for source {source['name']}: {e}"
                )
                logger.info("=====================================================================")
                coordinator.finish_fetching_source(source["name"], 0)
                continue

        logger.info("=====================================================================")
        logger.info(f"🔄 GLOBAL FETCH CYCLE COMPLETE. Restarting in {self.interval/60} minutes...")
        logger.info("=====================================================================")

    def start(self):
        """
        Blocking loop (run in background thread/process).
        """
        while True:
            if not self._paused:
                self.run_once()
            time.sleep(self.interval if not self._paused else 5)
