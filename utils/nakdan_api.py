from typing import Any
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from hebrew import Hebrew

from .models import NakdanResponse, NakdanAPIPayload, MorphologicalFeatures
from .hebrew_constants import (
    NAKDAN_BASE_URL, MAX_TEXT_LENGTH, DEFAULT_TIMEOUT,
    HebrewFeatures, ERROR_MESSAGES
)
from .constants import NAKDAN_API_KEY

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def analyze_text(text: str, timeout: float = DEFAULT_TIMEOUT, max_length: int = MAX_TEXT_LENGTH) -> NakdanResponse:
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
            return NakdanResponse(text="", error=ERROR_MESSAGES["empty_text"])
        
        if len(text) > MAX_TEXT_LENGTH:
            return NakdanResponse(text="", error=ERROR_MESSAGES["text_too_long"])
            
        if not is_hebrew(text):
            return NakdanResponse(text="", error=ERROR_MESSAGES["non_hebrew"])

        data = _call_nakdan_api(text, timeout, task="analyze")
        
        # Process API response for analysis
        word_analysis = []
        vowelized_words = []
        
        for word_data in data:
            if isinstance(word_data, dict):
                word = word_data.get('word', '')
                options = word_data.get('options', [])
                
                # Get the first vowelized form for display
                if options and isinstance(options[0], list) and len(options[0]) > 0:
                    vowelized_form = options[0][0] if isinstance(options[0][0], str) else word
                    vowelized_words.append(vowelized_form)
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
                
                # Parse the BGU field for morphological analysis
                if 'BGU' in word_data:
                    try:
                        # Split BGU data into header and content
                        bgu_lines = word_data['BGU'].strip().split('\n')
                        if len(bgu_lines) >= 2:
                            headers = bgu_lines[0].split('\t')
                            values = bgu_lines[1].split('\t')
                            
                            # Create a dictionary from headers and values
                            bgu_data = dict(zip(headers, values))
                            
                            analysis['lemma'] = bgu_data.get('lex', '')
                            analysis['pos'] = bgu_data.get('POS', '')
                            analysis['gender'] = bgu_data.get('Gender', '')
                            analysis['number'] = bgu_data.get('Number', '')
                            analysis['person'] = bgu_data.get('Person', '')
                            analysis['tense'] = bgu_data.get('Tense', '')
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
def _call_nakdan_api(text: str, timeout: float = DEFAULT_TIMEOUT, task: str = "nakdan") -> list[dict[str, Any]]:
    """
    Makes the actual API call to Nakdan service.
    
    Args:
        text: The Hebrew text to process
        timeout: Maximum time in seconds to wait for API response
        task: API task to perform
        
    Returns:
        Raw API response data
        
    Raises:
        httpx.HTTPError: If the API request fails
    """
    # Different endpoints and payloads for different tasks
    if task == "analyze":
        url = "https://nakdan-for-morph-analysis.loadbalancer.dicta.org.il/addnikud"
        payload = {
            "task": task,
            "apiKey": "3ab12a2f-80b3-450d-be66-8eb07748f9d2",
            "data": text,
            "genre": "modern",
            "freturnfullmorphstr": True,
            "addmorph": True,
            "keepmetagim": True,
            "keepnikud": True,
            "keepqq": True,
            "newjson": True
        }
    else:
        # Default endpoint for vowelize/nikud
        url = f"{NAKDAN_BASE_URL}/api"
        payload = {
            "task": task,
            "data": text,
            "genre": "modern"
        }
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Format Hebrew text for logging
    # Safely encode Hebrew text for logging
    safe_text = ' '.join(f"U+{ord(c):04X}" for c in text)
    logger.info("Nakdan API Request - URL: %s | Text: %s | Payload: %r", 
               url, safe_text, payload)
    
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
            # Safely log response content
            logger.debug("Raw Response Content: %r", response_json)
        except Exception as e:
            logger.error("Failed to format response for logging: %s", e)
            logger.debug("Raw Response Content: %r", response.text)
        return response.json()

def get_lemmas(text: str, timeout: float = DEFAULT_TIMEOUT, max_length: int = MAX_TEXT_LENGTH) -> NakdanResponse:
    """
    Gets the base/root form (lemma) of Hebrew words.
    
    Args:
        text: The Hebrew text to process
        timeout: Maximum time in seconds to wait for API response
        max_length: Maximum allowed text length
        
    Returns:
        NakdanResponse containing lemmatized text and word analysis
    """
    try:
        if not text.strip():
            return NakdanResponse(text="", error=ERROR_MESSAGES["empty_text"])
        
        if len(text) > max_length:
            return NakdanResponse(text="", error=ERROR_MESSAGES["text_too_long"])
            
        if not is_hebrew(text):
            return NakdanResponse(text="", error=ERROR_MESSAGES["non_hebrew"])

        data = _call_nakdan_api(text, timeout, task="analyze")
        
        # Process API response for lemmatization
        lemmatized_words = []
        word_analysis = []
        
        for word_data in data:
            if isinstance(word_data, dict):
                word = word_data.get('word', '')
                options = word_data.get('options', [])
                
                # Extract lemma from morphological analysis
                lemma = word  # Default to original word
                if options and isinstance(options[0], list):
                    try:
                        first_option = options[0]
                        if len(first_option) >= 2 and isinstance(first_option[1], list):
                            morph_data = first_option[1]
                            if len(morph_data) >= 1:
                                # Extract lemma from first element
                                lemma = morph_data[0][1] if len(morph_data[0]) > 1 else word
                    except Exception as e:
                        logger.warning("Failed to parse lemma: %s", e)
                
                lemmatized_words.append(lemma)
                
                # Add analysis info
                analysis = {
                    'word': word,
                    'lemma': lemma
                }
                word_analysis.append(analysis)
            else:
                lemmatized_words.append(str(word_data))
                word_analysis.append({})

        # Join the lemmatized words
        lemmatized_text = ' '.join(lemmatized_words)
        
        return NakdanResponse(
            text=lemmatized_text,
            word_analysis=word_analysis
        )

    except httpx.HTTPError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error("HTTP error occurred while calling Nakdan API: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)
    except Exception as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error("Error getting lemmas with Nakdan API: %s", str(e), exc_info=True)
        return NakdanResponse(text="", error=error_msg)

def get_nikud(text: str, timeout: float = DEFAULT_TIMEOUT, max_length: int = MAX_TEXT_LENGTH) -> NakdanResponse:
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
            return NakdanResponse(text="", error=ERROR_MESSAGES["empty_text"])
        
        if len(text) > max_length:
            return NakdanResponse(text="", error=ERROR_MESSAGES["text_too_long"])
            
        if not is_hebrew(text):
            return NakdanResponse(text="", error=ERROR_MESSAGES["non_hebrew"])
        
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
