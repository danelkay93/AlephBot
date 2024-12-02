import logging
from typing import cast

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from hebrew import Hebrew
from config import settings
from hebrew_constants import (
    NAKDAN_BASE_URL, MAX_TEXT_LENGTH, DEFAULT_TIMEOUT,
    ERROR_MESSAGES
)
from models import NakdanResponse
from nakdan_exceptions import (
    NakdanAPIError, NakdanResponseError
)
from nakdan_types import (
    NakdanTask, NakdanAPIResponse
)
import re

from nlp import _process_word_data

# Load API key from environment
NAKDAN_API_KEY = settings.nakdan_api_key
if not NAKDAN_API_KEY:
    raise ValueError("NAKDAN_API_KEY environment variable not set")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def check_text_requirements(text: str, max_length: int = MAX_TEXT_LENGTH) -> NakdanResponse | None:
    """Checks if text meets basic requirements (non-empty, length, Hebrew chars)."""
    if not text.strip():
        return NakdanResponse(text="", error=ERROR_MESSAGES["empty_text"])
    
    if len(text) > max_length:
        return NakdanResponse(text="", error=ERROR_MESSAGES["text_too_long"])
        
    if not is_hebrew(text):
        return NakdanResponse(text="", error=ERROR_MESSAGES["non_hebrew"])
    
    return None

def sanitize_input(text: str) -> str:
    """Sanitize input text to prevent injection attacks."""
    return re.sub(r'[^\x20-\x7E]', '', text)


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
        if error_response := check_text_requirements(text, max_length):
            return error_response

        data = call_nakdan_api(text, timeout, task="analyze")
        
        word_analysis = []
        vowelized_words = []
        
        for word_data in data:
            if isinstance(word_data, dict):
                vowelized_form, analysis = _process_word_data(word_data)
                vowelized_words.append(vowelized_form)
                word_analysis.append(analysis)
            else:
                word_analysis.append({})
                vowelized_words.append(str(word_data))

        vowelized_text = ''.join(vowelized_words)
        hebrew_text = Hebrew(vowelized_text)
        preserved_text = hebrew_text.normalize().string

        return NakdanResponse(
            text=preserved_text,
            word_analysis=word_analysis
        )

    except Exception as e:
        return handle_api_error(e, "analyzing text")

def is_hebrew(text: str) -> bool:
    """Check if string contains Hebrew characters using the hebrew package."""
    hebrew_text = Hebrew(text)
    # Check if any character is in the Hebrew alphabet range (0x0590-0x05FF)
    return any('\u0590' <= char <= '\u05FF' for char in str(hebrew_text))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_nakdan_api(
    text: str,
    timeout: float = DEFAULT_TIMEOUT,
    task: NakdanTask = NakdanTask.NAKDAN
) -> NakdanAPIResponse:
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
            "apiKey": NAKDAN_API_KEY,
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
            "data": sanitize_input(text),
            "genre": "modern"
        }
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Log request details without raw Hebrew text to avoid encoding issues
    logger.info("Nakdan API Request - URL: %s | Text length: %d chars | Task: %s", 
               url, len(text), payload.get('task', 'unknown'))
    
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
        else:
            logger.info("Response Content: %r", response_json)

        response_data = response.json()
        
        # Validate response structure
        if not isinstance(response_data, list):
            raise NakdanResponseError("Invalid response format: expected list")
            
        # Validate each word in response
        for item in response_data:
            if isinstance(item, dict):
                if 'word' not in item:
                    raise NakdanResponseError("Invalid word data: missing 'word' field")
                if 'options' not in item:
                    raise NakdanResponseError("Invalid word data: missing 'options' field")
            elif not isinstance(item, str):
                raise NakdanResponseError(f"Invalid response item type: {type(item)}")
        
        return cast(NakdanAPIResponse, response_data)

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
        if error_response := check_text_requirements(text, max_length):
            return error_response

        data = call_nakdan_api(text, timeout, task="analyze")
        
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

    except Exception as e:
        return handle_api_error(e, "getting lemmas")

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
        if error_response := check_text_requirements(text, max_length):
            return error_response
        
        data = call_nakdan_api(text, timeout)

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

    except Exception as e:
        return handle_api_error(e, "adding nikud")
def handle_api_error(e: Exception, operation: str) -> NakdanResponse:
    """
    Centralized error handling for API operations.
    
    Args:
        e: The exception that occurred
        operation: Description of the operation that failed
        
    Returns:
        NakdanResponse with appropriate error message
    """
    if isinstance(e, NakdanAPIError):
        error_msg = str(e)
        logger.error(
            "Nakdan API error while %s: %s", 
            operation, 
            error_msg,
            extra={"details": e.details} if e.details else None,
            exc_info=True
        )
    elif isinstance(e, httpx.HTTPError):
        error_msg = f"Connection error: {str(e)}"
        logger.error(
            "HTTP error occurred while %s: %s",
            operation,
            str(e),
            extra={"status_code": getattr(e.response, 'status_code', None)},
            exc_info=True
        )
    elif isinstance(e, KeyError):
        error_msg = f"Invalid API response format: {str(e)}"
        logger.error(
            "Failed to parse response while %s: %s",
            operation,
            str(e),
            exc_info=True
        )
    else:
        error_msg = f"Processing error: {str(e)}"
        logger.error(
            "Error while %s: %s",
            operation,
            str(e),
            exc_info=True
        )
    return NakdanResponse(text="", error=error_msg)
