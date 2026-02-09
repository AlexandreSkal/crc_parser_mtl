"""
IO Address Utilities — cleaning, suffix removal, normalization.

These functions were previously duplicated across step1, step2, and cpa_rack_parser.
"""

import re

# Suffixes to strip from PLC addresses
_SUFFIXES = [
    '!RD', '!WR', '!SC',
    '!BI', '!BO', '!AI', '!AO',
    '!DI', '!DO',
    '!ST', '!EN', '!DN',
    '!PV', '!SP', '!CV',
]


def clean_io_address(address):
    """
    Remove common PLC suffixes from an IO address.

    Example:
        "RACK00_SLOT06[10]!RD" → "RACK00_SLOT06[10]"
    """
    if not address:
        return address
    for suffix in _SUFFIXES:
        if address.endswith(suffix):
            return address[:-len(suffix)]
    return address


def normalize_for_lookup(address):
    """
    Normalize address for dictionary lookup.
    Strips suffixes and returns cleaned version.
    """
    return clean_io_address(str(address)) if address else ''


def clean_target_id(target_id):
    """
    Normalize an ISA target_id: uppercase, replace _ with -, ensure separator.

    Examples:
        "PT_200"  → "PT-200"
        "PIT-301" → "PIT-301"
        "LXY_801A" → "LXY-801A"
    """
    if not target_id:
        return ''
    if target_id.upper() in ('SPARE', 'M/A', 'N/A', ''):
        return ''
    if len(target_id) > 30:
        return ''

    cleaned = target_id.strip().upper().replace('_', '-')

    # Ensure separator between letters and numbers: PIT801 → PIT-801
    match = re.match(r'^([A-Z]+)(\d+.*)$', cleaned)
    if match and '-' not in cleaned:
        cleaned = f"{match.group(1)}-{match.group(2)}"

    return cleaned


def normalize_unit(unit):
    """
    Normalize engineering unit string.

    Returns empty string for non-units like 'M/A', 'SPARE'.
    """
    if not unit:
        return ''
    unit = unit.strip().upper()
    if unit in ('M/A', 'N/A', 'SPARE', ''):
        return ''

    normalizations = {
        'DEGF': 'DEGF', 'DEGC': 'DEGC',
        '"WC': '" WC', 'IN WC': '" WC',
        'BBLS': 'BPD', 'MA': 'mA', '"': 'IN',
        'DEG F': 'DEGF', 'DegF': 'DEGF',
        'INWC': '" WC',
    }
    return normalizations.get(unit, unit)
