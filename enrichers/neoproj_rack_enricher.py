"""
NeoProj RACK Enricher — Extract tag_id, unit, description from NeoProj RACK XAML screens.
"""

import os
import re
import glob
import tempfile
import shutil

import pandas as pd

from utils.io_address import normalize_for_lookup
from utils.neoproj_zip import extract_neoproj_zip


# =============================================================================
# XAML RACK PARSER
# =============================================================================

def _parse_rack_xaml(xaml_path):
    """
    Parse a single NeoProj RACK XAML file.

    Returns list of {tag_name, tag_id, unit, description, screen}.
    """
    screen_name = os.path.splitext(os.path.basename(xaml_path))[0]

    with open(xaml_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    elements = []

    # AnalogNumericFX with Tag binding
    pattern1 = re.compile(
        r'<nac:AnalogNumericFX[^>]*Canvas\.Left="([^"]+)"[^>]*Canvas\.Top="([^"]+)"[^>]*>'
        r'(.*?)</nac:AnalogNumericFX>',
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern1.finditer(content):
        try:
            x, y = float(m.group(1)), float(m.group(2))
        except ValueError:
            continue
        tag_match = re.search(r'Path="\[Tags\.([^\]]+)\]', m.group(3))
        if tag_match:
            elements.append({'x': x, 'y': y, 'type': 'TAG', 'value': tag_match.group(1)})

    # Labels (text)
    label_patterns = [
        re.compile(r'<nac:Label[^>]*Text="([^"]+)"[^>]*Canvas\.Left="([^"]+)"[^>]*Canvas\.Top="([^"]+)"', re.IGNORECASE),
        re.compile(r'<nac:Label[^>]*Canvas\.Left="([^"]+)"[^>]*Canvas\.Top="([^"]+)"[^>]*Text="([^"]+)"', re.IGNORECASE),
    ]
    for pat in label_patterns:
        for m in pat.finditer(content):
            try:
                if 'Text' in pat.pattern[:50]:
                    text, x, y = m.group(1), float(m.group(2)), float(m.group(3))
                else:
                    x, y, text = float(m.group(1)), float(m.group(2)), m.group(3)
            except (ValueError, IndexError):
                continue
            elements.append({
                'x': x, 'y': y, 'type': 'TEXT',
                'value': text.replace('&amp;', '&').replace('&quot;', '"'),
            })

    # Match tags with nearby text
    SKIP = {'Ch.', 'TAG', 'DESCRIPTION', 'DESCRIPITION', 'MAIN', 'NEXT',
            'PREVIOUS', 'M/A', 'ANALOG INPUTS', 'DISCRETE INPUTS'}
    UNITS = {'PSIG', 'PSI', 'PSIA', '%', 'DEGF', 'DEGC', 'GPM', 'BPD',
             'MCF', 'MCFD', 'MSCF', 'MA', 'VDC', 'VAC', 'HZ', 'IN', 'BBLS'}

    tags = [e for e in elements if e['type'] == 'TAG']
    texts = [e for e in elements if e['type'] == 'TEXT']
    results = []

    for tag in tags:
        row_texts = sorted(
            [t for t in texts if abs(t['y'] - tag['y']) <= 25],
            key=lambda t: t['x'],
        )

        tag_id, unit, description = '', '', ''
        for t in row_texts:
            text = t['value'].strip()
            if text.upper() in SKIP or (text.isdigit() and int(text) <= 20):
                continue
            text_upper = text.upper()
            if text_upper in UNITS and not unit:
                unit = text
            elif re.match(r'^[A-Z]{2,5}[-_]\d+[A-Z]?$', text, re.IGNORECASE) and not tag_id:
                if text_upper != 'SPARE':
                    tag_id = text.upper().replace('_', '-')
            elif len(text) > 10 and not description:
                description = text

        if tag_id or unit or description:
            results.append({
                'tag_name': tag['value'], 'tag_id': tag_id,
                'unit': unit, 'description': description, 'screen': screen_name,
            })

    return results


def _extract_rack_data(project_dir):
    """Extract RACK data from all RACK*.xaml files in project_dir."""
    if not project_dir:
        return {}

    rack_files = glob.glob(os.path.join(project_dir, 'RACK*.xaml'))
    if not rack_files:
        return {}

    print(f"\n  Parsing {len(rack_files)} RACK XAML screens...")
    rack_data = {}

    for xaml_path in sorted(rack_files):
        items = _parse_rack_xaml(xaml_path)
        for item in items:
            tag_name = item['tag_name']
            if tag_name not in rack_data:
                rack_data[tag_name] = {
                    'tag_id': item['tag_id'],
                    'unit': item['unit'],
                    'description': item['description'],
                }

    print(f"    -> {len(rack_data)} tags from RACK screens")
    return rack_data


# =============================================================================
# PUBLIC API
# =============================================================================

def enrich_from_neoproj_rack(df, neoproj_path):
    """
    Enrich DataFrame with RACK screen data from NeoProj project.

    Handles .zip files (extracts to temp dir) and plain directories.
    Returns df.
    """
    if not neoproj_path or not os.path.exists(neoproj_path):
        return df

    temp_dir = None
    project_dir = None

    try:
        if neoproj_path.lower().endswith('.zip'):
            temp_dir = tempfile.mkdtemp(prefix='neoproj_enrich_')
            extract_neoproj_zip(neoproj_path, temp_dir)
            subdirs = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
            project_dir = os.path.join(temp_dir, subdirs[0]) if subdirs else temp_dir
        elif os.path.isdir(neoproj_path):
            project_dir = neoproj_path

        rack_data = _extract_rack_data(project_dir)
        if not rack_data:
            return df

        enriched = 0
        for idx, row in df.iterrows():
            hmi_tag = str(row.get('HMI Tag Name', ''))
            tag_name = hmi_tag.replace('Tags.', '') if hmi_tag else ''

            if tag_name and tag_name in rack_data:
                data = rack_data[tag_name]
                current_tag = row.get('target_id_rack', '')
                if (not current_tag or pd.isna(current_tag) or current_tag == '') and data['tag_id']:
                    df.at[idx, 'target_id_rack'] = data['tag_id']
                current_unit = row.get('target_units', '')
                if (not current_unit or pd.isna(current_unit) or current_unit == '') and data['unit']:
                    df.at[idx, 'target_units'] = data['unit']
                if data['description']:
                    df.at[idx, 'rack_description'] = data['description']
                enriched += 1

        print(f"    -> Enriched {enriched} tags from RACK screens")

    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    return df
