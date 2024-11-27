import json
import asyncio
import logging
from typing import Optional, Literal, Dict
import websockets
from websockets.exceptions import WebSocketException
from tenacity import retry, stop_after_attempt, wait_exponential

from .hebrew_constants import DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

DICTA_WS_URL = "wss://translate.loadbalancer.dicta.org.il/api/ws"
TranslationDirection = Literal["he-en", "en-he"]

TRANSLATION_GENRES: Dict[str, str] = {
    "modern": "Standard modern translation style",
    "modern-formal": "Formal/professional translation style",
    "modern-colloquial": "Casual/conversational style",
    "biblical": "Biblical/archaic style translation",
    "technical": "Technical/scientific translation style",
    "legal": "Legal/official document style"
}

class DictaTranslateAPI:
    """Client for the Dicta Translation WebSocket API"""
    
    TRANSLATION_GENRES = {
        "modern": "Standard modern translation style",
        "modern-formal": "Formal/professional translation style", 
        "modern-colloquial": "Casual/conversational style",
        "biblical": "Biblical/archaic style translation",
        "technical": "Technical/scientific translation style",
        "legal": "Legal/official document style"
    }
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the Dicta Translation API client
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.ws = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def translate(
        self,
        text: str,
        direction: TranslationDirection,
        genre: str = "modern",
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
            
            async with websockets.connect(DICTA_WS_URL) as ws:
                # Send translation request
                request = {
                    "text": text,
                    "direction": direction,
                    "genre": genre,
                    "style": genre,  # API requires both genre and style
                    "temperature": temperature
                }
                await ws.send(json.dumps(request))
                
                # Process translation response
                response = await ws.recv()
                if not response.strip():
                    raise ValueError("Empty response received")
                    
                logger.debug("Received WebSocket message: %r", response)
                
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
