"""
CPA Screen Reader — parse CPA file into screen → objects structure.

This is the generic CPA parser that reads GraphicBlock sections and
returns all objects organized by screen name. Used by both:
  - parsers/cpa_parser.py (Step 1 extraction)
  - enrichers/cpa_screen_enricher.py (Step 2 enrichment)
"""

import re
from collections import defaultdict
from .cpa_text_library import parse_text_library


def parse_all_screens(cpa_path):
    """
    Parse CPA file and return all screen objects with their attributes.

    Returns:
        dict: {screen_name: [list of obj dicts]}
              Each obj dict has keys like 'x', 'y', 'IO', 'Text', etc.
    """
    in_graphic_block = False
    current_screen = None
    current_obj_type = None
    obj_data = {}
    screen_objects = defaultdict(list)

    with open(cpa_path, 'r', errors='ignore') as f:
        for line in f:
            s = line.strip()

            # Level-3 block header: [[[GraphicBlock]]], [[[IONaming]]], etc.
            if s.startswith('[[[') and s.endswith(']]]') and not s.startswith('[[[['):
                if obj_data and current_screen:
                    screen_objects[current_screen].append(obj_data.copy())

                name = s[3:-3].strip()
                if name == 'GraphicBlock':
                    in_graphic_block = True
                    current_screen = None
                else:
                    in_graphic_block = False
                    current_screen = None

                obj_data = {}
                current_obj_type = None
                continue

            if not in_graphic_block:
                continue

            # Screen name (first Name= after GraphicBlock)
            if current_screen is None and s.startswith('Name='):
                current_screen = s.split('=', 1)[1].strip()
                continue

            # Level-4 object header: [[[[GrAnaNumeric]]]]
            if s.startswith('[[[[') and s.endswith(']]]]'):
                if obj_data and current_screen:
                    screen_objects[current_screen].append(obj_data.copy())
                current_obj_type = s[4:-4].strip()
                obj_data = {}
                continue

            if not current_obj_type:
                continue

            # Key=Value attribute
            if '=' in s:
                key, val = s.split('=', 1)
                obj_data[key.strip()] = val.strip()

    # Save last object
    if obj_data and current_screen:
        screen_objects[current_screen].append(obj_data.copy())

    return screen_objects


def resolve_text(text_val, text_map):
    """
    Resolve a CPA text value: either direct string or @N reference.

    Args:
        text_val: Raw text from CPA (e.g. "@1636" or "PIT-801")
        text_map: dict from parse_text_library()

    Returns:
        str: Resolved text, or None if unresolvable
    """
    if not text_val:
        return None

    m = re.match(r'@(\d+)$', text_val)
    if m:
        tid = int(m.group(1))
        resolved = text_map.get(tid)
        return resolved.strip() if resolved else None

    text_val = text_val.strip()
    return text_val if text_val else None
