from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from .hebrew_constants import MAX_TEXT_LENGTH

class MorphologicalFeatures(BaseModel):
    """Morphological features of a Hebrew word"""
    word: str
    lemma: str = ""
    pos: str = ""
    gender: str = ""
    number: str = ""
    person: str = ""
    tense: str = ""

class NakdanResponse(BaseModel):
    """Response from Nakdan API processing"""
    text: str
    error: Optional[str] = None
    lemmas: List[str] = Field(default_factory=list)
    pos_tags: List[str] = Field(default_factory=list)
    word_analysis: List[Dict[str, Any]] = Field(default_factory=list)

    @validator('text')
    def validate_text_length(cls, v):
        if len(v) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text exceeds maximum length of {MAX_TEXT_LENGTH} characters")
        return v

class NakdanAPIPayload(BaseModel):
    """Payload for Nakdan API requests"""
    task: str
    data: str
    genre: str = "modern"
    addmorph: bool = True
    keepqq: bool = False
    nodageshdefmem: bool = False
    patachma: bool = False
    keepmetagim: bool = True
