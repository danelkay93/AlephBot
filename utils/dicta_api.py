import json
import asyncio
import logging
from typing import Optional, Literal
import websockets
from websockets.exceptions import WebSocketException
from tenacity import retry, stop_after_attempt, wait_exponential

from .hebrew_constants import DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

DICTA_WS_URL = "wss://translate.loadbalancer.dicta.org.il/api/ws"
TranslationDirection = Literal["he-en", "en-he"]

class DictaTranslateAPI:
    """Client for the Dicta Translation WebSocket API"""
    
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
                    "genre": genre,
                    "direction": direction,
                    "temperature": temperature
                }
                await ws.send(json.dumps(request))
                
                # Process response chunks
                translated_chunks = []
                current_json = ""
                
                while True:
                    try:
                        response = await ws.recv()
                        
                        # Skip empty responses
                        if not response.strip():
                            continue
                            
                        logger.debug("Received WebSocket message: %r", response)
                        
                        # Handle ping/pong immediately
                        try:
                            data = json.loads(response)
                            if isinstance(data, dict) and data.get("type") == "ping":
                                await ws.send(json.dumps({"type": "pong"}))
                                logger.debug("Sent pong response")
                                continue
                            elif isinstance(data, dict) and data.get("stage") == "done":
                                logger.debug("Received done message")
                                break
                        except json.JSONDecodeError:
                            pass  # Not a complete message, continue accumulating
                        
                        # Accumulate JSON chunks
                        current_json += response
                        
                        try:
                            # Try to parse accumulated JSON
                            data = json.loads(current_json)
                            
                            # Successfully parsed, process the data
                            if isinstance(data, list):
                                for chunk in data:
                                    if isinstance(chunk, dict) and "out" in chunk:
                                        translated_chunks.append(chunk["out"])
                                        logger.debug("Added translation chunk: %s", chunk["out"])
                            
                            # Clear accumulated JSON after successful parse
                            current_json = ""
                            
                        except json.JSONDecodeError:
                            # Continue accumulating if not complete JSON
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
