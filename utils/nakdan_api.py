from typing import Dict, List, Any, Optional
import httpx
import logging
from attrs import define

logger = logging.getLogger(__name__)

@define
class NakdanResponse:
    text: str
    error: Optional[str] = None

def get_nikud(text: str, timeout: float = 10.0) -> NakdanResponse:
    """
    Sends Hebrew text to the Nakdan API and returns it with niqqud.
    
    Args:
        text: The Hebrew text to process
        timeout: Maximum time in seconds to wait for API response
        
    Returns:
        NakdanResponse containing either the processed text or error message
    """
    try:
        url = "https://nakdan-5-1.loadbalancer.dicta.org.il/api"
        payload: Dict[str, str] = {
            "data": text,
            "genre": "modern"  # Options: 'modern', 'poetry', etc.
        }
        headers: Dict[str, str] = {
            'Content-Type': 'application/json'
        }
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data: List[Dict[str, Any]] = response.json()

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
