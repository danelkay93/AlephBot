from typing import Any
import re
import httpx
import logging
from attrs import define
from tenacity import retry, stop_after_attempt, wait_exponential
from hebrew import Hebrew, GematriaTypes

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
        vowelized_words = []
        
        for word_data in data:
            if isinstance(word_data, dict):
                word = word_data.get('word', '')
                options = word_data.get('options', [])
                
                # Get the first vowelized form for display
                if options and isinstance(options[0], str):
                    vowelized_words.append(options[0])
                else:
                    vowelized_words.append(word)
                
                # Extract morphological analysis
                analysis = {
                    'word': word,
                    'lemma': '',
                    'pos': '',
                    'gender': '',
                    'number': '',
                    'person': '',
                    'tense': ''
                }
                
                # Parse the first option's analysis string
                if options and isinstance(options[0], str):
                    try:
                        # Split analysis parts (typically separated by |)
                        parts = options[0].split('|')
                        if len(parts) > 1:
                            # First part usually contains POS and basic features
                            features = parts[0].split(' ')
                            if features:
                                analysis['pos'] = features[0]
                                # Additional features may include gender, number, etc.
                                for feature in features[1:]:
                                    if 'זכר' in feature or 'נקבה' in feature:
                                        analysis['gender'] = feature
                                    elif 'יחיד' in feature or 'רבים' in feature:
                                        analysis['number'] = feature
                                    elif 'עבר' in feature or 'הווה' in feature or 'עתיד' in feature:
                                        analysis['tense'] = feature
                            # Second part might contain the lemma
                            if len(parts) > 1:
                                analysis['lemma'] = parts[1].strip()
                    except Exception as e:
                        logger.warning("Failed to parse morphological analysis: %s", e)
                
                word_analysis.append(analysis)
            else:
                word_analysis.append({})
                vowelized_words.append(str(word_data))

        # Join the vowelized words to create the final text
        vowelized_text = ''.join(vowelized_words)
        
        # Use Hebrew package for proper normalization
        hebrew_text = Hebrew(vowelized_text)
        preserved_text = hebrew_text.normalize().string

        return NakdanResponse(
            text=preserved_text,
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
    """Check if string contains Hebrew characters using the hebrew package."""
    hebrew_text = Hebrew(text)
    # Check if any character is in the Hebrew alphabet range (0x0590-0x05FF)
    return any('\u0590' <= char <= '\u05FF' for char in str(hebrew_text))

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
    payload = {
        "task": "nakdan",
        "data": text,
        "genre": "modern",
        "addmorph": True,
        "keepqq": False,
        "nodageshdefmem": False,
        "patachma": False,
        "keepmetagim": True
    }
    headers = {
        'Content-Type': 'text/plain;charset=UTF-8'
    }
    
    # Format Hebrew text for logging
    logger.info("Nakdan API Request - URL: %s | Payload: %r", 
               url, payload)
    
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        logger.info("Nakdan API Response - Status: %d | Length: %d bytes | Cache: %s", 
                   response.status_code,
                   len(response.content),
                   response.headers.get('x-gg-cache-status', 'N/A'))
        # Format response content for better logging
        try:
            response_json = response.json()
            logger.debug("Raw Response Content: %s", response.text)
        except Exception as e:
            logger.error("Failed to format response for logging: %s", e)
            logger.debug("Raw Response Content: %r", response.text)
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
        vowelized_words = []
        
        for word_data in data:
            if isinstance(word_data, dict):
                options = word_data.get('options', [])
                if options and isinstance(options[0], str):
                    # Get the vowelized form from the first option string
                    vowelized_words.append(options[0])
                else:
                    # Fallback to original word if no options available
                    vowelized_words.append(word_data.get('word', ''))
            else:
                vowelized_words.append(str(word_data))

        # Join words with original spacing and normalize Hebrew text
        vowelized_text = ''
        for i, word in enumerate(vowelized_words):
            if i < len(original_spaces):
                vowelized_text += original_spaces[i]
            hebrew_word = Hebrew(word)
            vowelized_text += hebrew_word.normalize().string
        
        # Add final spacing if available
        if original_spaces and len(original_spaces) > len(vowelized_words):
            vowelized_text += original_spaces[-1]

        # Use Hebrew package for proper normalization
        hebrew_text = Hebrew(vowelized_text)
        preserved_text = hebrew_text.normalize().string
        
        return NakdanResponse(
            text=preserved_text,
            word_analysis=[]  # Empty for vowelize command
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
