from typing import Optional
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from .hebrew_constants import DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

DEEPL_FREE_API_URL = "https://api-free.deepl.com/v2"
DEEPL_PRO_API_URL = "https://api.deepl.com/v2"

class DeepLAPI:
    """Client for the DeepL Translation API"""
    
    def __init__(self, auth_key: str, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the DeepL API client
        
        Args:
            auth_key: DeepL API authentication key
            timeout: Request timeout in seconds
        """
        self.auth_key = auth_key
        self.timeout = timeout
        # Determine if using free or pro API based on key suffix
        self.base_url = DEEPL_FREE_API_URL if ":fx" in auth_key else DEEPL_PRO_API_URL
        self.headers = {
            "Authorization": f"DeepL-Auth-Key {auth_key}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None,
        formality: Optional[str] = None
    ) -> str:
        """Translate text using the DeepL API
        
        Args:
            text: Text to translate
            target_lang: Target language code (e.g. 'EN-US', 'HE')
            source_lang: Source language code (optional)
            formality: Desired formality ('more', 'less', or None)
            
        Returns:
            Translated text
            
        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/translate"
        
        payload = {
            "text": [text],
            "target_lang": target_lang
        }
        
        if source_lang:
            payload["source_lang"] = source_lang
        if formality:
            payload["formality"] = formality

        logger.info("DeepL API Request - URL: %s | Target Lang: %s | Source Lang: %s",
                   url, target_lang, source_lang or "auto")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            logger.debug("DeepL API Response: %r", data)
            
            if "translations" in data and len(data["translations"]) > 0:
                return data["translations"][0]["text"]
            else:
                raise ValueError("No translation found in API response")

    async def get_usage(self) -> dict:
        """Get API usage statistics
        
        Returns:
            Dictionary containing usage information
        """
        url = f"{self.base_url}/usage"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
