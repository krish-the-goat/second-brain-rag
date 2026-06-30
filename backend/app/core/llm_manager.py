import os
import threading
import time
from app.core.logging import get_logger

logger = get_logger(__name__)

class LLMManager:
    """
    Manages the active LLM provider (gemini vs groq).
    Provides a fallback mechanism on 429 Too Many Requests errors.
    """
    def __init__(self):
        self._lock = threading.Lock()
        
        self.primary_provider = "gemini"
        self.fallback_provider = "groq"
        self.active_provider = self.primary_provider
        
        self.last_fallback_time = 0
        self.cooldown_seconds = 300 # Try returning to primary after 5 minutes
        
        self.gemini_key = os.getenv("GOOGLE_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        
        if not self.gemini_key:
            logger.warning("GOOGLE_API_KEY is not set.")
        if not self.groq_key:
            logger.warning("GROQ_API_KEY is not set.")

    def get_active_provider(self) -> str:
        with self._lock:
            # If we are on fallback, check if cooldown has expired
            if self.active_provider != self.primary_provider:
                if time.time() - self.last_fallback_time > self.cooldown_seconds:
                    logger.info(f"Cooldown expired. Reverting to primary LLM: {self.primary_provider}")
                    self.active_provider = self.primary_provider
            
            return self.active_provider

    def get_api_key(self, provider: str) -> str:
        if provider == "gemini":
            return self.gemini_key
        elif provider == "groq":
            return self.groq_key
        return ""

    def switch_to_fallback(self, current_failing_provider: str):
        with self._lock:
            # Only switch if the active provider is the one that failed (prevents concurrent race conditions)
            if self.active_provider == current_failing_provider:
                if self.active_provider == self.primary_provider and self.groq_key:
                    logger.warning(f"Rate limit hit! Switching LLM Provider from {self.primary_provider} to {self.fallback_provider}")
                    self.active_provider = self.fallback_provider
                    self.last_fallback_time = time.time()
                else:
                    logger.error(f"Cannot fallback. Active provider is already {self.active_provider} or backup key missing.")

llm_manager = LLMManager()
