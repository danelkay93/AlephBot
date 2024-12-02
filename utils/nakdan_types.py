from typing import Literal, TypedDict, List, Optional, Union
from enum import Enum

class NakdanTask(str, Enum):
    NAKDAN = "nakdan"
    ANALYZE = "analyze"

class MorphData(TypedDict):
    word: str
    prefix: str
    suffix: str
    menukad: str
    lemma: str
    pos: str
    gender: str
    number: str
    person: str
    status: str
    tense: str
    binyan: str
    suf_gender: str
    suf_person: str
    suf_number: str

class WordOption(TypedDict):
    word: str
    options: List[Union[str, List[List[str]]]]
    BGU: Optional[str]
    UD: Optional[str]

NakdanAPIResponse = List[Union[WordOption, str]]
