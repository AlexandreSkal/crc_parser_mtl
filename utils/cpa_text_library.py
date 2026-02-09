"""
CPA Text Library — decode TextW format and build text_id → string mapping.

CPA files store text in Unicode hex format:
    TextW=0054 0049 0054 002D 0033 0036 0039 0032  →  "TIT-3692"

This module provides the decoder and text library builder used by
both CPA screen parsers and enrichers.
"""

import re


def decode_textw(textw):
    """
    Decode CIMREX TextW format to readable string.

    Each 4-hex group is a Unicode code point.

    Example:
        "0054 0049 0054" → "TIT"
    """
    if not isinstance(textw, str):
        return ""
    parts = re.findall(r'\b[0-9A-Fa-f]{4}\b', textw)
    chars = []
    for p in parts:
        try:
            chars.append(chr(int(p, 16)))
        except ValueError:
            continue
    return ''.join(chars).strip()


def parse_text_library(cpa_path):
    """
    Build mapping: text_id (int) → decoded string from CPA file.

    Scans for blocks like:
        No=1636
        TextW=0054 0049 0054 002D 0033 0036 0039 0032

    Returns:
        dict: {int: str}
    """
    text_map = {}
    current_no = None

    with open(cpa_path, 'r', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line.startswith('No='):
                try:
                    current_no = int(line.split('=')[1])
                except ValueError:
                    current_no = None
            elif line.startswith('TextW=') and current_no is not None:
                textw = line.split('=', 1)[1]
                decoded = decode_textw(textw)
                if decoded:
                    text_map[current_no] = decoded

    return text_map
