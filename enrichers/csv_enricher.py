"""
CSV Enricher — Load descriptions and ALIAS mappings from Rockwell CSV export.
"""

import os
import pandas as pd
from utils.io_address import normalize_for_lookup


def load_csv_data(filepath):
    """
    Parse Rockwell CSV for COMMENT descriptions and ALIAS mappings.

    Returns:
        tuple: (descriptions, alias_map)
            descriptions: {address: description}
            alias_map: {address: {tag_id, description}}
    """
    descriptions = {}
    alias_map = {}

    if not filepath or not os.path.exists(filepath):
        return descriptions, alias_map

    print(f"\n  Loading CSV: {os.path.basename(filepath)}")

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()

            if line.startswith('COMMENT,,'):
                parts = line.split(',')
                if len(parts) >= 6:
                    desc = parts[3].strip('"')
                    tag = parts[-1].strip('"')
                    if tag and desc:
                        descriptions[tag] = desc

            elif line.startswith('ALIAS,,'):
                parts = line.split(',')
                if len(parts) >= 6:
                    alias_name = parts[2].strip('"')
                    desc = parts[3].strip('"')
                    plc_address = parts[5].strip('"')
                    if alias_name and plc_address:
                        alias_map[plc_address] = {
                            'tag_id': alias_name.upper().replace('_', '-'),
                            'description': desc or '',
                        }

        print(f"    -> {len(descriptions)} COMMENT descriptions, {len(alias_map)} ALIAS mappings")

    except Exception as e:
        print(f"    -> Error: {e}")

    return descriptions, alias_map


def enrich_from_csv(df, csv_path):
    """
    Enrich DataFrame with CSV descriptions and ALIAS tag IDs.

    Modifies df in place (target_id_rack, Description, Description Source).
    Returns df.
    """
    if not csv_path or not os.path.exists(csv_path):
        return df

    descriptions, alias_map = load_csv_data(csv_path)
    if not descriptions and not alias_map:
        return df

    enriched = 0
    alias_count = 0

    for idx, row in df.iterrows():
        io_address = str(row['IO Address'])
        io_clean = normalize_for_lookup(io_address)

        # ALIAS → tag_id
        current_tag = row.get('target_id_rack', '')
        if not current_tag or pd.isna(current_tag) or current_tag == '':
            alias = alias_map.get(io_address) or alias_map.get(io_clean)
            if alias:
                df.at[idx, 'target_id_rack'] = alias['tag_id']
                alias_count += 1
                current_desc = row.get('Description', '')
                if (not current_desc or pd.isna(current_desc) or current_desc == '') and alias['description']:
                    df.at[idx, 'Description'] = alias['description']
                    df.at[idx, 'Description Source'] = 'CSV_ALIAS'

        # COMMENT → Description
        current_desc = row.get('Description', '')
        if not current_desc or pd.isna(current_desc) or current_desc == '':
            desc = descriptions.get(io_address) or descriptions.get(io_clean)
            if desc:
                df.at[idx, 'Description'] = desc
                df.at[idx, 'Description Source'] = 'CSV'
                enriched += 1

    print(f"    -> {enriched} descriptions from CSV, {alias_count} tag IDs from ALIAS")
    return df
