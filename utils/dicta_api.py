"""API clients for Dicta services including Translation and Nakdan"""
import json
import logging
from typing import Optional, Dict, Any
import httpx
import websockets
from websockets.exceptions import WebSocketException
from tenacity import retry, stop_after_attempt, wait_exponential
from hebrew import Hebrew

from .models import NakdanResponse
from .hebrew_constants import (
    DEFAULT_TIMEOUT, MAX_TEXT_LENGTH, ERROR_MESSAGES,
    NAKDAN_BASE_URL, NAKDAN_API_KEY
)
from .translation import TranslationDirection, TRANSLATION_GENRES, TranslationGenre

logger = logging.getLogger(__name__)

# Translation API Constants
DICTA_WS_URL = "wss://translate.loadbalancer.dicta.org.il/api/ws"

class DictaAPI:
    """Client for Dicta Translation and Nakdan APIs"""
    
    TRANSLATION_GENRES = TRANSLATION_GENRES
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the Dicta Translation API client
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.ws = None

    @retry(
        stop=stop_after_attempt(7),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def translate(
        self,
        text: str,
        direction: TranslationDirection,
        genre: str = "modern-fancy",
        temperature: float = 0
    ) -> str:
        """Translate text using the Dicta Translation API
        
        Args:
            text: Text to translate
            direction: Translation direction ('he-en' or 'en-he')
            genre: Translation style/genre
            temperature: Translation randomness (0-1)
            
        Returns:
            Translated text
            
        Raises:
            WebSocketException: If the WebSocket connection fails
            ValueError: If the translation fails
        """
        try:
            logger.info("Dicta Translation Request - Direction: %s | Genre: %s",
                       direction, genre)
            logger.debug("Opening WebSocket connection to: %s", DICTA_WS_URL)
            
            async with websockets.connect(DICTA_WS_URL) as ws:
                # Send translation request
                logger.debug("Connected to WebSocket")
                request = {
                    "text": text,
                    "direction": direction,
                    "genre": genre,
                    "temperature": temperature
                }
                request_json = json.dumps(request)
                logger.debug("Sending WebSocket message: %r", request_json)
                await ws.send(request_json)
                
                # Process translation response
                response = await ws.recv()
                logger.debug("Received WebSocket message: %r", response)
                if not response.strip():
                    raise ValueError("Empty response received")
                
                try:
                    data = json.loads(response)
                    
                    # Handle error messages
                    if isinstance(data, dict):
                        if "error" in data:
                            error_msg = data["error"]
                            logger.error("Translation API error: %s", error_msg)
                            raise ValueError(f"API Error: {error_msg}")
                        elif "out" in data:
                            translated_text = data["out"].strip()
                            if not translated_text:
                                raise ValueError("Empty translation received")
                            logger.debug("Final translation: %s", translated_text)
                            return translated_text
                            
                except json.JSONDecodeError:
                    if "Error during translation task" in response:
                        logger.error("Translation API error: %s", response)
                        raise ValueError(f"API Error: {response}")
                    logger.error("Failed to parse WebSocket message: %r", response)
                    raise ValueError("Invalid response format")
                
        except WebSocketException as e:
            logger.error("WebSocket error during translation: %s", str(e))
            raise
        except Exception as e:
            logger.error("Translation error: %s", str(e))
            raise ValueError(f"Translation failed: {str(e)}")
