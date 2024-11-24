from typing import Any
import re
import httpx
import logging
from attrs import define
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

@define
class NakdanResponse:
    text: str
    error: str | None = None

def is_hebrew(text: str) -> bool:
    """Check if string contains Hebrew characters."""
    hebrew_pattern = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]')
    return bool(hebrew_pattern.search(text))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def get_nikud(text: str, timeout: float = 10.0, max_length: int = 500) -> NakdanResponse:
    """
    Sends Hebrew text to the Nakdan API and returns it with niqqud.
    
    Args:
        text: The Hebrew text to process
        timeout: Maximum time in seconds to wait for API response
        
    Returns:
        NakdanResponse containing either the processed text or error message
    """
    try:
        if not text.strip():
            return NakdanResponse(text="", error="Text cannot be empty")
        
        if len(text) > max_length:
            return NakdanResponse(text="", error=f"Text exceeds maximum length of {max_length} characters")
            
        if not is_hebrew(text):
            return NakdanResponse(text="", error="Text must contain Hebrew characters")
        url = "https://nakdan-5-1.loadbalancer.dicta.org.il/api"
        payload: dict[str, str] = {
            "data": text,
            "genre": "modern"  # Options: 'modern', 'poetry', etc.
        }
        headers: dict[str, str] = {
            'Content-Type': 'application/json'
        }
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data: list[dict[str, Any]] = response.json()

        # Extract the vowelized text from the response
        words = [w['options'][0] if w['options'] else w['word'] for w in data]
        return NakdanResponse(text="".join(words))

    except httpx.HTTPError as e:
        error_msg = "An error occurred while connecting to the service."
        logger.error("HTTP error occurred while calling Nakdan API: %s", e)
        return NakdanResponse(text="", error=error_msg)
    except Exception as e:
        error_msg = "An error occurred while processing the text."
        logger.error("Error processing text with Nakdan API: %s", e)
        return NakdanResponse(text="", error=error_msg)
