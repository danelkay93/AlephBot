import pytest
from utils.nakdan_api import get_nikud, is_hebrew

def test_nakdan_api_vowelize():
    """Test the Nakdan API with a simple Hebrew word"""
    # Test with a simple Hebrew word
    text = "שלום"
    result = get_nikud(text)
    
    # Verify no errors occurred
    assert result.error is None
    
    # Verify we got vowelized text back
    assert len(result.text) > 0
    assert result.text != text  # Should have niqqud added
    
    # Verify we got analysis data
    assert len(result.lemmas) > 0
    assert len(result.pos_tags) > 0
    assert len(result.word_analysis) > 0
    
    # Verify word analysis contains expected fields
    analysis = result.word_analysis[0]
    assert 'word' in analysis
    assert 'lemma' in analysis
    assert 'pos' in analysis
