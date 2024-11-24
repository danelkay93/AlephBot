import json
from typing import Dict, List, Any
import httpx
import logging

logger = logging.getLogger(__name__)

def get_nikud(text: str) -> str:
    """
    Sends Hebrew text to the Nakdan API and returns it with niqqud.
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
        
        with httpx.Client() as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data: List[Dict[str, Any]] = response.json()

        # Extract the vowelized text from the response
        words = [w['options'][0] if w['options'] else w['word'] for w in data]
        return "".join(words)

    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred while calling Nakdan API: {e}")
        return "An error occurred while connecting to the service."
    except Exception as e:
        logger.error(f"Error processing text with Nakdan API: {e}")
        return "An error occurred while processing the text."
