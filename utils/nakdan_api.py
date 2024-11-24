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
    lemmas: list[str] = []
    pos_tags: list[str] = []
    word_analysis: list[dict[str, Any]] = []

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
        BASE_URL = "https://nakdan-5-1.loadbalancer.dicta.org.il"
        url = f"{BASE_URL}/api"
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

        # Extract the vowelized text and analysis from the response
        words = []
        lemmas = []
        pos_tags = []
        word_analysis = []
        for word_data in data:
            options = word_data.get('options', [])
            if options:
                try:
                    option = options[0]
                    word = option.get('word')
                    if not word:
                        logger.error("Missing required 'word' field in API response option: %s", option)
                        raise KeyError("Missing required 'word' field in API response")
                        
                    words.append(word)
                    lemmas.append(option.get('lemma', ''))
                    pos_tags.append(option.get('partOfSpeech', ''))
                    word_analysis.append({
                        'word': word,
                        'lemma': option.get('lemma', ''),
                        'pos': option.get('partOfSpeech', ''),
                        'gender': option.get('gender', ''),
                        'number': option.get('number', ''),
                        'person': option.get('person', ''),
                        'tense': option.get('tense', '')
                    })
                except (KeyError, IndexError) as e:
                    logger.error("Failed to parse API response option: %s. Error: %s", option, str(e))
                    raise
            else:
                word = word_data.get('word')
                if not word:
                    logger.error("Missing required 'word' field in API response data: %s", word_data)
                    raise KeyError("Missing required 'word' field in API response")
                words.append(word)
                lemmas.append('')
                pos_tags.append('')
                word_analysis.append({})

        return NakdanResponse(
            text="".join(words),
            lemmas=lemmas,
            pos_tags=pos_tags,
            word_analysis=word_analysis
        )

    except httpx.HTTPError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error("HTTP error occurred while calling Nakdan API: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)
    except KeyError as e:
        error_msg = f"Invalid API response format: {str(e)}"
        logger.error("Failed to parse Nakdan API response: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error("Error processing text with Nakdan API: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)
