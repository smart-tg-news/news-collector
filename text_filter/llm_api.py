import asyncio
import aiohttp
import logging
import os
from aiolimiter import AsyncLimiter

from utils.http_session import get_shared_session
from utils.config import cfg


logger = logging.getLogger(__name__)

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1/chat/completions") 


# 20 requests per 60 seconds, shared across the entire process
_OPENROUTER_RATE_LIMITER_FREE = AsyncLimiter(max_rate=20, time_period=60)
_OPENROUTER_RATE_LIMITER_PAID = AsyncLimiter(max_rate=120, time_period=60)


class TextFilter:
    """
    An async class to filter articles using the OpenRouter API.
    """

    SYSTEM_PROMPT = (
        "You are ArticleFilterGPT, an expert classifier. "
        "You receive raw article text parsed from various websites—often incomplete, truncated, link‑heavy, or low‑quality. "
        "Decide if each article is engaging and informative enough to show to end users (“good”) or if it should be discarded (“garbage”). "
        "Always reply with exactly one word: good or garbage."
    )
    USER_PROMPT_TEMPLATE = (
        "Classify this article. Reply with only \"good\" or \"garbage\".\n\n"
        "Article:\n"
        "{text}"
    )

    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        model: str = cfg.filter_llm,
        max_retries: int = 3,
        backoff_factor: float = 3.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/smart-tg-news/news-collector",
            "X-Title": "SmartDigest News Summarizer"
        }
        self.session = get_shared_session()

    async def check(self, text: str) -> bool:
        """
        Filters the given article text.
        Returns True if article is 'good', False if 'garbage'.
        On errors, logs the exception and returns False (conservative discard).
        """
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.USER_PROMPT_TEMPLATE.format(text=text)}
        ]

        try:
            response = await self._request(messages)
            content = response["choices"][0]["message"]["content"].strip().lower()
        except Exception as e:
            logging.error(f"Article check failed: {e}")
            return True

        # Normalize and fallback parsing
        if content not in ("good", "garbage"):
            if "garbage" in content:
                return False
            if "good" in content:
                return True
            return False

        return content == "good"

    async def _request(self, messages: list) -> dict:
        """
        Internal async method to send requests to OpenRouter with retry/backoff.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "top_p": 1.0,
        }
        rate_limiter = _OPENROUTER_RATE_LIMITER_PAID
        if self.model.endswith(":free"):
            rate_limiter = _OPENROUTER_RATE_LIMITER_FREE

        for attempt in range(1, self.max_retries + 1):
            async with rate_limiter:
                try:
                    async with self.session.post(
                            self.base_url, 
                            json=payload, 
                            headers=self.headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()

                except aiohttp.ClientResponseError as http_err:
                    status = http_err.status
                    # Retry on rate limit or server errors
                    if status in (429, 503):
                        wait = self.backoff_factor * (2 ** (attempt - 1))
                        logging.warning(f"Transient HTTP error {status}, retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    # Non-retryable HTTP errors
                    raise

                except (aiohttp.ClientError, asyncio.TimeoutError) as req_err:
                    # Network or timeout errors
                    wait = self.backoff_factor * (2 ** (attempt - 1))
                    logging.warning(f"Network error: {req_err}, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue

            # Exceeded retries
            raise RuntimeError("Failed to get a valid response from OpenRouter after retries")
