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
                
                # Process response chunks
                translated_chunks = []
                translation_complete = False
                
                while not translation_complete:
                    try:
                        response = await ws.recv()
                        
                        # Skip empty responses
                        if not response.strip():
                            continue
                            
                        logger.debug("Received WebSocket message: %r", response)
                        
                        try:
                            data = json.loads(response)
                            
                            # Handle error messages
                            if isinstance(data, dict):
                                if "error" in data:
                                    error_msg = data["error"]
                                    logger.error("Translation API error: %s", error_msg)
                                    raise ValueError(f"API Error: {error_msg}")
                                    
                                # Handle ping/pong
                                if data.get("type") == "ping":
                                    await ws.send(json.dumps({"type": "pong"}))
                                    logger.debug("Sent pong response")
                                    continue
                                elif data.get("stage") == "done":
                                    logger.debug("Received done message")
                                    translation_complete = True
                                    continue
                                elif "out" in data:
                                    translated_text = data["out"].strip()
                                    if translated_text:
                                        translated_chunks.append(translated_text)
                                        logger.debug("Added translation chunk: %s", translated_text)
                            
                            # Handle array responses
                            elif isinstance(data, list):
                                for chunk in data:
                                    if isinstance(chunk, dict):
                                        if "error" in chunk:
                                            error_msg = chunk["error"]
                                            logger.error("Translation chunk error: %s", error_msg)
                                            raise ValueError(f"API Error: {error_msg}")
                                        elif "out" in chunk:
                                            translated_text = chunk["out"].strip()
                                            if translated_text:
                                                translated_chunks.append(translated_text)
                                                logger.debug("Added translation chunk: %s", translated_text)
                                            
                        except json.JSONDecodeError as e:
                            # Check if the raw response contains an error message
                            if "Error during translation task" in response:
                                logger.error("Translation API error: %s", response)
                                raise ValueError(f"API Error: {response}")
                            logger.warning("Failed to parse WebSocket message: %r", response)
                            continue
                            
                    except asyncio.TimeoutError:
                        raise ValueError("Translation timed out")
                
                # Check if we got any translation chunks
                if not translated_chunks:
                    logger.error("No translation chunks received in response")
                    raise ValueError("No translation received")
                
                # Join all translation chunks
                result = " ".join(translated_chunks)
                logger.debug("Final translation: %s", result)
                return result
                
        except WebSocketException as e:
            logger.error("WebSocket error during translation: %s", str(e))
            raise
        except Exception as e:
            logger.error("Translation error: %s", str(e))
            raise ValueError(f"Translation failed: {str(e)}")
