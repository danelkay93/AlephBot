import logging
from spacy_conll import init_parser
from spacy_conll.parser import ConllParser
from deplacy import deplacy
from nakdan_types import MorphData

logger = logging.getLogger(__name__)

def process_bgu_field(word_data: dict, analysis: MorphData) -> None:
    """Process BGU field for morphological analysis."""
    if 'BGU' not in word_data or word_data['BGU'] is None:
        return

    try:
        bgu_text = word_data['BGU']
        if not isinstance(bgu_text, str):
            logger.warning("BGU field is not a string: %r", bgu_text)
            return

        bgu_lines = bgu_text.strip().split('\n')
        if len(bgu_lines) >= 2:
            headers = bgu_lines[0].split('\t')
            values = bgu_lines[1].split('\t')
            bgu_data = dict(zip(headers, values))

            # Map BGU fields to our analysis
            analysis.update({
                'lemma': bgu_data.get('lex', ''),
                'pos': bgu_data.get('POS', ''),
                'gender': bgu_data.get('Gender', ''),
                'number': bgu_data.get('Number', ''),
                'person': bgu_data.get('Person', ''),
                'tense': bgu_data.get('Tense', ''),
                'binyan': bgu_data.get('Binyan', ''),
                'status': bgu_data.get('Status', '')
            })

            if analysis['suffix']:
                analysis.update({
                    'suf_gender': bgu_data.get('Suf_Gender', ''),
                    'suf_person': bgu_data.get('Suf_Person', ''),
                    'suf_number': bgu_data.get('Suf_Number', '')
                })
    except Exception as e:
        logger.warning("Failed to parse morphological analysis: %s", e)


def process_word_parts(word: str) -> MorphData:
    analysis: MorphData = {
        'word': word,
        'prefix': '',
        'suffix': '',
        'menukad': '',
        'lemma': '',
        'pos': '',
        'gender': '',
        'number': '',
        'person': '',
        'status': '',
        'tense': '',
        'binyan': '',
        'suf_gender': '',
        'suf_person': '',
        'suf_number': ''
    }

    word_parts = word.split('|')
    if len(word_parts) > 1:
        if word_parts[0]:  # Has prefix
            analysis['prefix'] = word_parts[0]
        main_word = word_parts[1]
        if len(word_parts) > 2:  # Has suffix
            analysis['suffix'] = word_parts[-1]
            main_word = '|'.join(word_parts[1:-1])
        analysis['menukad'] = main_word
    else:
        analysis['menukad'] = word

    return analysis

def process_ud_field(word_data: dict) -> None:
    if 'UD' in word_data:
        try:
            nlp = ConllParser(init_parser("lang/he", "spacy"))
            doc = nlp.parse_conll_text_as_spacy(word_data['UD'])
            deplacy.render(doc)
        except Exception as e:
            logger.warning("Failed to parse UD field: %s", e)

def process_word_data(word_data: dict) -> tuple[str, MorphData]:
    """Process individual word data and return vowelized form and analysis."""
    word = word_data.get('word', '')
    options = word_data.get('options', [])

    # Get vowelized form
    vowelized_form = word
    if options and isinstance(options[0], list) and len(options[0]) > 0:
        vowelized_form = options[0][0] if isinstance(options[0][0], str) else word

    # Get morphological analysis
    analysis = process_word_parts(word)
    process_ud_field(word_data)
    process_bgu_field(word_data, analysis)

    return vowelized_form, analysis
