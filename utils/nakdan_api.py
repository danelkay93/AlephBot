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

def analyze_text(text: str, timeout: float = 10.0, max_length: int = 500) -> NakdanResponse:
    """
    Analyzes Hebrew text and returns morphological information.
    
    Args:
        text: The Hebrew text to analyze
        timeout: Maximum time in seconds to wait for API response
        max_length: Maximum allowed text length
        
    Returns:
        NakdanResponse containing analysis results or error message
    """
    try:
        if not text.strip():
            return NakdanResponse(text="", error="Text cannot be empty")
        
        if len(text) > max_length:
            return NakdanResponse(text="", error=f"Text exceeds maximum length of {max_length} characters")
            
        if not is_hebrew(text):
            return NakdanResponse(text="", error="Text must contain Hebrew characters")

        data = _call_nakdan_api(text, timeout)
        
        # Process API response for analysis
        word_analysis = []
        for word_data in data:
            if isinstance(word_data, dict):
                options = word_data.get('options', [])
                if options and isinstance(options[0], dict):
                    option = options[0]
                    word_analysis.append({
                        'word': option.get('word', ''),
                        'lemma': option.get('lemma', ''),
                        'pos': option.get('partOfSpeech', ''),
                        'gender': option.get('gender', ''),
                        'number': option.get('number', ''),
                        'person': option.get('person', ''),
                        'tense': option.get('tense', '')
                    })
                else:
                    word_analysis.append({})
            else:
                word_analysis.append({})

        return NakdanResponse(
            text=text,
            word_analysis=word_analysis
        )

    except httpx.HTTPError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error("HTTP error occurred while calling Nakdan API: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error("Error analyzing text with Nakdan API: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)

def is_hebrew(text: str) -> bool:
    """Check if string contains Hebrew characters."""
    hebrew_pattern = re.compile(r'[\u0590-\u05FF\uFB1D-\uFB4F]')
    return bool(hebrew_pattern.search(text))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def _call_nakdan_api(text: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """
    Makes the actual API call to Nakdan service.
    
    Args:
        text: The Hebrew text to process
        timeout: Maximum time in seconds to wait for API response
        
    Returns:
        Raw API response data
        
    Raises:
        httpx.HTTPError: If the API request fails
    """
    BASE_URL = "https://nakdan-5-1.loadbalancer.dicta.org.il"
    url = f"{BASE_URL}/api"
    payload: dict[str, str] = {
        "data": text,
        "genre": "modern"
    }
    headers: dict[str, str] = {
        'Content-Type': 'application/json'
    }
    
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

def get_nikud(text: str, timeout: float = 10.0, max_length: int = 500) -> NakdanResponse:
    """
    Sends Hebrew text to the Nakdan API and returns it with niqqud.
    
    Args:
        text: The Hebrew text to process
        timeout: Maximum time in seconds to wait for API response
        max_length: Maximum allowed text length
        
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
        
        data = _call_nakdan_api(text, timeout)

        # Split original text to preserve spaces
        original_words = text.split()
        original_spaces = []
        current_pos = 0
        
        # Collect original spacing
        for word in original_words:
            word_pos = text.find(word, current_pos)
            if word_pos > current_pos:
                original_spaces.append(text[current_pos:word_pos])
            else:
                original_spaces.append('')
            current_pos = word_pos + len(word)
        
        # Add any trailing space
        if current_pos < len(text):
            original_spaces.append(text[current_pos:])
        else:
            original_spaces.append('')

        # Process API response
        words = []
        lemmas = []
        pos_tags = []
        word_analysis = []
        
        for word_data in data:
            if isinstance(word_data, dict):
                options = word_data.get('options', [])
                if options and isinstance(options[0], dict):
                    option = options[0]
                    word = option.get('word', '')
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
                else:
                    word = word_data.get('word', '')
                    words.append(word)
                    lemmas.append('')
                    pos_tags.append('')
                    word_analysis.append({})
            else:
                words.append(str(word_data))
                lemmas.append('')
                pos_tags.append('')
                word_analysis.append({})

        # Reconstruct text with original spacing
        vowelized_text = ''
        for i, word in enumerate(words):
            if i < len(original_spaces):
                vowelized_text += original_spaces[i]
            vowelized_text += word
        # Add final spacing if available
        if original_spaces and len(original_spaces) > len(words):
            vowelized_text += original_spaces[-1]

        return NakdanResponse(
            text=vowelized_text,
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
