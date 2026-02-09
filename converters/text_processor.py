"""
Text Processor — Abbreviation expansion and proper capitalization.
"""

import re
from patterns import ABBREVIATIONS, PRESERVED_ACRONYMS
from config import EXPAND_ABBREVIATIONS, APPLY_CAPITALIZATION, PRESERVE_ACRONYMS


def expand_abbreviations(text):
    """Expand common abbreviations in text."""
    if not text or not isinstance(text, str) or not EXPAND_ABBREVIATIONS:
        return text
    result = text
    for pattern, replacement in ABBREVIATIONS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def capitalize_proper(text):
    """
    Apply Excel PROPER()-style capitalization, preserving acronyms.

    Example:
        "V-700 LP SEPARATOR LEVEL" → "V-700 Low Pressure Separator Level"
    """
    if not text or not isinstance(text, str) or not APPLY_CAPITALIZATION:
        return text

    text = expand_abbreviations(text)
    result = text.title()

    if PRESERVE_ACRONYMS:
        for acronym in PRESERVED_ACRONYMS:
            pattern = r'\b' + re.escape(acronym.title()) + r'\b'
            result = re.sub(pattern, acronym, result, flags=re.IGNORECASE)

    return result
