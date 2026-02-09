"""
CPA Screen Enricher — Extract tag_id, unit, description from CPA screens.

Handles:
  - RACK screens (Analog I/O)
  - Discrete Input/Output and Analog Input/Output screens
"""

import re
import os
import pandas as pd
from collections import defaultdict

from utils.io_address import normalize_for_lookup
from utils.cpa_text_library import parse_text_library
from utils.cpa_screen_reader import parse_all_screens, resolve_text


# =============================================================================
# SHARED HELPERS
# =============================================================================

_UNIT_RE = re.compile(
    r'^(PSIG|PSI|PSIA|%|DEGF|DEGC|GPM|BPD|MCF|MCFD|MSCF|mA|MA|VDC|VAC|IN|Hz|AMPS|BBLS)$',
    re.IGNORECASE,
)
_TAG_RE = re.compile(r'^[A-Z]{2,5}[-_]?[A-Z]?\d+[A-Z]?$', re.IGNORECASE)

_SKIP_TEXTS = {
    'SPARE', 'TAG', 'DESCRIPTION', 'DESCRIPITION', 'PLC_TAG', 'PLC TAG', 'UNIT',
    'DISCRETE INPUTS', 'DISCRETE OUTPUTS', 'ANALOG INPUTS', 'ANALOG OUTPUTS',
    'SLOT', 'CH', 'CH.', 'CHANNEL', 'DISCRETE INPUT', 'DISCRETE OUTPUT',
    'ANALOG INPUT', 'ANALOG OUTPUT', 'MAIN', 'NEXT', 'PREVIOUS', 'M/A',
    'FAULT', 'SCALED', 'TEXT',
}


def _extract_plc_and_texts(objects, text_map):
    """Split screen objects into PLC tags (with IO=) and resolved texts."""
    plc_tags = []
    texts = []

    for obj in objects:
        if 'x' not in obj or 'y' not in obj:
            continue
        try:
            x, y = float(obj['x']), float(obj['y'])
        except (ValueError, TypeError):
            continue

        if 'IO' in obj and obj['IO']:
            plc_tags.append({'x': x, 'y': y, 'io': obj['IO']})

        if 'Text' in obj and obj['Text']:
            resolved = resolve_text(obj['Text'], text_map)
            if resolved:
                texts.append({'x': x, 'y': y, 'resolved': resolved})

    return plc_tags, texts


def _build_lookup(screen_data):
    """Build {io_address: metadata} lookup from screen extraction results."""
    lookup = {}
    for row in screen_data:
        io_addr = row['io_address']
        io_clean = normalize_for_lookup(io_addr)
        metadata = {
            'target_id': row.get('target_id', ''),
            'unit': row.get('unit', ''),
            'description': row.get('description', ''),
            'screen': row.get('screen', ''),
        }
        if metadata['target_id'] or metadata['unit'] or metadata['description']:
            lookup[io_clean] = metadata
            lookup[io_addr] = metadata
    return lookup


# =============================================================================
# RACK SCREEN PARSER
# =============================================================================

def _extract_rack_data(cpa_path):
    """Extract tag/unit/description from RACK screens in CPA file."""
    text_map = parse_text_library(cpa_path)
    all_screens = parse_all_screens(cpa_path)

    rack_screens = {n: o for n, o in all_screens.items() if n.upper().startswith('RACK')}
    if not rack_screens:
        return []

    print(f"    -> {len(rack_screens)} RACK screens found")

    unit_re = re.compile(r'^(PSIG|PSI|%|DEGF|GPM|BPD|MCF|MCFD|BBLS|mA|IN|Hz|VDC)$', re.IGNORECASE)
    tag_re = re.compile(r'^[A-Z]{2,5}[-_]?\d+', re.IGNORECASE)
    results = []

    for screen_name, objects in rack_screens.items():
        plc_tags, texts = _extract_plc_and_texts(objects, text_map)
        if not plc_tags:
            continue

        # Dynamic column detection
        x_buckets = defaultdict(list)
        for t in texts:
            bucket = int(t['x'] / 20) * 20
            x_buckets[bucket].append(t)

        unit_col, tag_col, desc_col = None, None, None
        for bucket, items in sorted(x_buckets.items()):
            if len(items) < 3:
                continue
            samples = [t['resolved'] for t in items[:15]]
            if sum(1 for s in samples if unit_re.match(s)) >= len(samples) * 0.3 and not unit_col:
                unit_col = (bucket - 20, bucket + 40)
                continue
            if sum(1 for s in samples if tag_re.match(s) and len(s) <= 20) >= len(samples) * 0.3 and not tag_col:
                tag_col = (bucket - 20, bucket + 60)
                continue
            if sum(1 for s in samples if len(s) > 15) >= len(samples) * 0.2 and not desc_col:
                desc_col = (bucket - 20, bucket + 200)

        unit_col = unit_col or (200, 350)
        tag_col = tag_col or (350, 500)
        desc_col = desc_col or (500, 1000)

        for plc in plc_tags:
            row = {'screen': screen_name, 'io_address': plc['io'],
                   'target_id': '', 'unit': '', 'description': ''}
            nearby = sorted(
                [t for t in texts if abs(t['y'] - plc['y']) <= 15],
                key=lambda t: t['x'],
            )

            for t in nearby:
                x, text = t['x'], t['resolved']
                if unit_col[0] <= x <= unit_col[1] and not row['unit'] and unit_re.match(text):
                    row['unit'] = text
                elif tag_col[0] <= x <= tag_col[1] and not row['target_id']:
                    row['target_id'] = text
                elif x >= desc_col[0] and not row['description']:
                    row['description'] = text
                elif x >= desc_col[0] and row['description'] and len(text) > len(row['description']):
                    row['description'] = text

            if row['target_id'].upper() == 'SPARE' or row['description'].upper().startswith('SPARE'):
                continue
            if row['target_id'] or row['unit'] or row['description']:
                results.append(row)

    print(f"    -> {len(results)} IOs from RACK screens")
    return results


# =============================================================================
# DISCRETE / ANALOG SCREEN PARSER
# =============================================================================

def _extract_discrete_analog_data(cpa_path):
    """Extract tag/unit/description from Discrete/Analog IO screens."""
    text_map = parse_text_library(cpa_path)
    all_screens = parse_all_screens(cpa_path)

    screen_patterns = [
        r'^Discrete\s*Input', r'^Discrete\s*Output',
        r'^Analog\s*Input', r'^Analog\s*Output',
        r'^DI\s*[\(\[\s]', r'^DO\s*[\(\[\s]',
        r'^AI\s*[\(\[\s]', r'^AO\s*[\(\[\s]',
    ]
    io_screens = {}
    for name, objs in all_screens.items():
        if any(re.match(p, name, re.IGNORECASE) for p in screen_patterns):
            io_screens[name] = objs

    if not io_screens:
        return []

    print(f"    -> {len(io_screens)} Discrete/Analog screens found")
    results = []

    for screen_name, objects in io_screens.items():
        plc_tags, texts = _extract_plc_and_texts(objects, text_map)
        if not plc_tags:
            continue

        # Dynamic column detection
        x_buckets = defaultdict(list)
        for t in texts:
            bucket = int(t['x'] / 50) * 50
            x_buckets[bucket].append(t)

        tag_col, desc_col = None, None
        for bucket, items in sorted(x_buckets.items()):
            if len(items) < 2:
                continue
            samples = [t['resolved'] for t in items[:20]]
            if sum(1 for s in samples if s.upper() in _SKIP_TEXTS) >= len(samples) * 0.5:
                continue
            if sum(1 for s in samples if _TAG_RE.match(s) and len(s) <= 15) >= len(samples) * 0.3 and not tag_col:
                tag_col = (bucket - 30, bucket + 80)
                continue
            if sum(1 for s in samples if len(s) > 15) >= len(samples) * 0.2 and not desc_col:
                desc_col = (bucket - 30, bucket + 300)

        tag_col = tag_col or (200, 400)
        desc_col = desc_col or (400, 800)

        for plc in plc_tags:
            row = {'screen': screen_name, 'io_address': plc['io'],
                   'target_id': '', 'unit': '', 'description': ''}
            nearby = sorted(
                [t for t in texts if abs(t['y'] - plc['y']) <= 20],
                key=lambda t: t['x'],
            )

            for t in nearby:
                x, text = t['x'], t['resolved']
                if text.upper() in _SKIP_TEXTS:
                    continue
                if text.isdigit() and int(text) <= 32:
                    continue
                if _UNIT_RE.match(text) and not row['unit']:
                    row['unit'] = text
                    continue
                if tag_col[0] <= x <= tag_col[1] and not row['target_id']:
                    if _TAG_RE.match(text) or text.upper() == 'SPARE':
                        row['target_id'] = text
                        continue
                if desc_col[0] <= x and not row['description']:
                    if _TAG_RE.match(text) and len(text) <= 12 and not row['target_id']:
                        row['target_id'] = text
                        continue
                    row['description'] = text
                    continue
                if len(text) > 15 and not row['description']:
                    row['description'] = text

            if row['target_id'].upper() == 'SPARE' or row['description'].upper().startswith('SPARE'):
                continue
            if row['target_id'] or row['description']:
                results.append({
                    **row,
                    'target_id': row['target_id'].upper().replace('_', '-') if row['target_id'] else '',
                })

    print(f"    -> {len(results)} IOs from Discrete/Analog screens")
    return results


# =============================================================================
# PUBLIC API
# =============================================================================

def enrich_from_cpa_screens(df, cpa_path):
    """
    Enrich DataFrame with data from CPA RACK + Discrete/Analog screens.

    Fills: target_id_rack, target_units, rack_description, Description.
    Returns df.
    """
    if not cpa_path or not os.path.exists(cpa_path):
        return df

    print(f"\n  Enriching from CPA screens: {os.path.basename(cpa_path)}")

    # RACK screens
    rack_data = _extract_rack_data(cpa_path)
    rack_lookup = _build_lookup(rack_data)

    # Discrete/Analog screens
    da_data = _extract_discrete_analog_data(cpa_path)
    da_lookup = _build_lookup(da_data)

    enriched = 0
    for idx, row in df.iterrows():
        io_address = str(row['IO Address'])
        io_clean = normalize_for_lookup(io_address)

        data = rack_lookup.get(io_address) or rack_lookup.get(io_clean) \
            or da_lookup.get(io_address) or da_lookup.get(io_clean)

        if not data:
            continue

        current_tag = row.get('target_id_rack', '')
        current_unit = row.get('target_units', '')
        current_rack_desc = row.get('rack_description', '')

        if (not current_tag or pd.isna(current_tag) or current_tag == '') and data['target_id']:
            df.at[idx, 'target_id_rack'] = data['target_id']
        if (not current_unit or pd.isna(current_unit) or current_unit == '') and data['unit']:
            df.at[idx, 'target_units'] = data['unit']
        if (not current_rack_desc or pd.isna(current_rack_desc) or current_rack_desc == '') and data['description']:
            df.at[idx, 'rack_description'] = data['description']

        current_desc = row.get('Description', '')
        if (not current_desc or pd.isna(current_desc) or current_desc == '') and data['description']:
            df.at[idx, 'Description'] = data['description']
            df.at[idx, 'Description Source'] = 'CPA_Screen'

        enriched += 1

    print(f"    -> Enriched {enriched} IOs from CPA screens")
    return df
