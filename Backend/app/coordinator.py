"""
Global Fetch-Process Coordinator
Manages coordination between RSS fetching and NLP processing.

Flow:
1. RSS fetches from ONE source
2. RSS pauses (state → PROCESSING)
3. Worker processes all pending articles
4. Worker pauses (state → IDLE)
5. RSS resumes (state → FETCHING)
6. Repeat for next source
"""

import threading
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GlobalCoordinator:
    """Thread-safe coordinator for fetch-process cycle management"""
    
    # States
    FETCHING = "FETCHING"      # RSS is actively fetching
    PROCESSING = "PROCESSING"  # Worker is processing articles
    IDLE = "IDLE"              # System is idle, waiting
    
    def __init__(self):
        self._lock = threading.RLock()
        self._state = self.IDLE
        self._current_source = None
        self._pending_count = 0
        self._processed_count = 0
        self._fetch_paused = False
        self._process_paused = False
        self._last_state_change = datetime.utcnow()
        
        logger.info("==============================================")
        logger.info("🎯 Global Coordinator initialized")
        logger.info("==============================================")
    
    # ==================== State Management ====================
    
    def get_state(self) -> str:
        """Get current coordinator state (thread-safe)"""
        with self._lock:
            return self._state
    
    def set_state(self, new_state: str) -> None:
        """Set coordinator state (thread-safe)"""
        with self._lock:
            if new_state not in [self.FETCHING, self.PROCESSING, self.IDLE]:
                raise ValueError(f"Invalid state: {new_state}")
            
            old_state = self._state
            self._state = new_state
            self._last_state_change = datetime.utcnow()
            
            if old_state != new_state:
                logger.info("==============================================")
                logger.info(f"🔄 State transition: {old_state} → {new_state}")
                logger.info("==============================================")
    
    # ==================== Fetch Control ====================
    
    def can_fetch(self) -> bool:
        """Check if RSS fetching is allowed"""
        with self._lock:
            return (self._state == self.IDLE or self._state == self.FETCHING) and not self._fetch_paused
    
    def pause_fetch(self) -> None:
        """Manually pause RSS fetching"""
        with self._lock:
            self._fetch_paused = True
            logger.info("==============================================")
            logger.info("⏸️  RSS fetching paused")
            logger.info("==============================================")
    
    def resume_fetch(self) -> None:
        """Manually resume RSS fetching"""
        with self._lock:
            self._fetch_paused = False
            logger.info("==============================================")
            logger.info("▶️  RSS fetching resumed")
            logger.info("==============================================")
    
    def start_fetching_source(self, source_name: str) -> None:
        """Mark start of fetching from a specific source"""
        with self._lock:
            self._state = self.FETCHING
            self._current_source = source_name
            logger.info(f"📡 Fetching from: {source_name}")
    
    def finish_fetching_source(self, source_name: str, article_count: int) -> None:
        """Mark completion of fetching from a source"""
        with self._lock:
            logger.info(f"✅ Fetched {article_count} articles from {source_name}")
            self._pending_count += article_count
            self._current_source = None
            
            # Transition to PROCESSING if articles were fetched
            if article_count > 0:
                self._state = self.PROCESSING
            else:
                self._state = self.IDLE
    
    # ==================== Process Control ====================
    
    def can_process(self) -> bool:
        """Check if NLP processing is allowed"""
        with self._lock:
            return self._state == self.PROCESSING and not self._process_paused
    
    def pause_process(self) -> None:
        """Manually pause NLP processing"""
        with self._lock:
            self._process_paused = True
            logger.info("==============================================")
            logger.info("⏸️  NLP processing paused")
            logger.info("==============================================")
    
    def resume_process(self) -> None:
        """Manually resume NLP processing"""
        with self._lock:
            self._process_paused = False
            logger.info("==============================================")
            logger.info("▶️  NLP processing resumed")
            logger.info("==============================================")
    
    def enter_priority_mode(self) -> None:
        """
        Enter priority mode for manual analysis.
        Pauses both fetching and background processing.
        """
        with self._lock:
            self._fetch_paused = True
            self._process_paused = True
            logger.info("==============================================")
            logger.info("🚀 PRIORITY MODE: ENABLED (Background tasks paused)")
            logger.info("==============================================")

    def exit_priority_mode(self) -> None:
        """
        Exit priority mode for manual analysis.
        Resumes both fetching and background processing.
        """
        with self._lock:
            self._fetch_paused = False
            self._process_paused = False
            logger.info("==============================================")
            logger.info("✅ PRIORITY MODE: DISABLED (Background tasks resumed)")
            logger.info("==============================================")
    
    def mark_article_processed(self) -> None:
        """Mark one article as processed"""
        with self._lock:
            if self._pending_count > 0:
                self._pending_count -= 1
                self._processed_count += 1
            
            # If no more pending, transition to IDLE
            if self._pending_count == 0:
                self._state = self.IDLE
                logger.info("==============================================")
                logger.info("🎉 Processing complete - transitioning to IDLE")
                logger.info("==============================================")
    
    def update_pending_count(self, count: int) -> None:
        """Update pending article count"""
        with self._lock:
            self._pending_count = count
    
    # ==================== Status & Metrics ====================
    
    def get_status(self) -> dict:
        """Get current coordinator status"""
        with self._lock:
            return {
                "state": self._state,
                "current_source": self._current_source,
                "pending_articles": self._pending_count,
                "processed_articles": self._processed_count,
                "fetch_paused": self._fetch_paused,
                "process_paused": self._process_paused,
                "last_state_change": self._last_state_change.isoformat()
            }
    
    def reset_stats(self) -> None:
        """Reset processing statistics"""
        with self._lock:
            self._processed_count = 0
            logger.info("==============================================")
            logger.info("📊 Stats reset")
            logger.info("==============================================")


# Global singleton instance
_coordinator: Optional[GlobalCoordinator] = None


def get_coordinator() -> GlobalCoordinator:
    """Get global coordinator instance"""
    global _coordinator
    if _coordinator is None:
        _coordinator = GlobalCoordinator()
    return _coordinator
