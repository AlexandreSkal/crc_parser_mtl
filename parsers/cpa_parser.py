"""
CPA Parser — Extract IOs from Iconics CPA files (PanelBuilder / CIMREX).

Extracts:
  - IO addresses from GraphicBlock screen objects
  - Descriptions from [[[IONaming]]] blocks
  - Alarm IOs from [[[Alarm]]] blocks (included even if not on any screen)
"""

import re
from collections import defaultdict
from utils.io_address import clean_io_address


def load_descriptions_and_alarms(lines):
    """
    Parse IONaming and Alarm blocks from CPA file lines.

    Returns:
        tuple: (descriptions, alarm_ios)
            descriptions: {address: description} — all sources
            alarm_ios: {address: description} — only alarm IOs
    """
    descriptions = {}
    alarm_ios = {}
    ionaming_count = 0
    alarm_count = 0

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line == '[[[IONaming]]]':
            address, comment = None, None
            j = i + 1
            while j < len(lines) and j < i + 30:
                attr = lines[j].strip()
                if attr.startswith('[[['):
                    break
                if attr.startswith('IONamingAddress='):
                    address = clean_io_address(attr.split('=', 1)[1].strip())
                if attr.startswith('IONamingComment='):
                    comment = attr.split('=', 1)[1].strip().strip('"')
                j += 1

            if address and comment:
                descriptions[address] = comment
                ionaming_count += 1

        elif line == '[[[Alarm]]]':
            address, text = None, None
            j = i + 1
            while j < len(lines) and j < i + 30:
                attr = lines[j].strip()
                if attr.startswith('[[[') and not attr.startswith('[[[['):
                    break
                if attr.startswith('IOActive=') and not attr.startswith('IOActive_'):
                    raw = attr.split('=', 1)[1].strip()
                    if raw:
                        address = clean_io_address(raw)
                if attr.startswith('Text='):
                    text = attr.split('=', 1)[1].strip()
                j += 1

            if address:
                alarm_ios[address] = text or ""
                if text and address not in descriptions:
                    descriptions[address] = text
                alarm_count += 1

        i += 1

    return descriptions, alarm_ios


def extract_ios_from_block(lines, start_idx, end_idx, graphic_objects):
    """
    Extract IO addresses from a GraphicBlock section.

    Args:
        lines: All file lines
        start_idx: Block start line
        end_idx: Block end line
        graphic_objects: List of object type names to extract

    Returns:
        list: IO addresses found
    """
    ios_found = []
    i = start_idx

    while i < end_idx:
        line = lines[i].strip()

        for obj_type in graphic_objects:
            if line == f'[[[[{obj_type}]]]]' or line == f'[[[[[[{obj_type}]]]]]]':
                j = i + 1
                while j < min(end_idx, i + 100):
                    io_line = lines[j].strip()
                    if io_line.startswith('[[[[') and j > i + 5:
                        break
                    if io_line.startswith('IO=') and not io_line.startswith('IO_'):
                        address = io_line.split('=', 1)[1].strip()
                        if address:
                            ios_found.append(clean_io_address(address))
                            break
                    j += 1
                break
        i += 1

    return ios_found


def extract_from_cpa(filepath, graphic_objects, excluded_screens):
    """
    Main extraction: parse CPA and return IOs, descriptions, alarm IOs.

    Args:
        filepath: Path to .cpa file
        graphic_objects: List of object types to scan
        excluded_screens: List of screen names to skip (lowercase)

    Returns:
        tuple: (ios_screens, descriptions, alarm_ios)
            ios_screens: {address: [screen_names]}
            descriptions: {address: description}
            alarm_ios: {address: description}
    """
    print(f"\n  Reading: {filepath}")
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    print(f"  -> {len(lines)} lines")

    descriptions, alarm_ios = load_descriptions_and_alarms(lines)
    ios_screens = defaultdict(list)

    print("\n  Processing screens...")
    i = 0
    num_screens = 0

    while i < len(lines):
        line = lines[i]

        if line.strip() == '[[[GraphicBlock]]]':
            if line.startswith('        [[[') or line.startswith('\t\t[[['):
                num_screens += 1

                j = i + 1
                screen_name = None
                block_end = len(lines)

                while j < len(lines):
                    param_line = lines[j].strip()
                    if j > i and lines[j].strip() == '[[[GraphicBlock]]]':
                        if lines[j].startswith('        [[[') or lines[j].startswith('\t\t[[['):
                            block_end = j
                            break
                    if param_line.startswith('Name=') and screen_name is None:
                        screen_name = param_line.split('=', 1)[1].strip()
                    j += 1

                if screen_name:
                    if screen_name.lower() in excluded_screens:
                        i += 1
                        continue

                    ios = extract_ios_from_block(lines, i, block_end, graphic_objects)
                    for address in ios:
                        if screen_name not in ios_screens[address]:
                            ios_screens[address].append(screen_name)

                    print(f"    {num_screens:2d}. {screen_name}: {len(ios)} IOs")
        i += 1

    print(f"\n  -> {num_screens} screens, {len(ios_screens)} unique IOs, {len(alarm_ios)} alarm IOs")
    return dict(ios_screens), descriptions, alarm_ios
