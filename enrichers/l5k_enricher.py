"""
L5K Enricher — Load descriptions from Rockwell L5K export files.
"""

import os
import re
import pandas as pd
from utils.io_address import normalize_for_lookup


def load_l5k_data(filepath):
    """
    Parse L5K file for RC: (Rung Comment) descriptions.

    Returns:
        dict: {tag_address: description}
    """
    descriptions = {}

    if not filepath or not os.path.exists(filepath):
        return descriptions

    print(f"\n  Loading L5K: {os.path.basename(filepath)}")

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]
            if re.search(r'^\s+RC:', line):
                comment_match = re.search(r'RC:\s*"([^"]+)"', line)
                if comment_match and i + 1 < len(lines):
                    comment = comment_match.group(1)
                    next_line = lines[i + 1]
                    if re.search(r'^\s+N:', next_line):
                        tags = re.findall(r'((?:READ|WRITE|EXTER_READ)FLOAT\[\d+\])', next_line)
                        tags += re.findall(r'(RACK\d+_SLOT\d+_TABLE\[\d+\])', next_line)
                        tags += re.findall(r'(ALARM\[\d+\](?:\.\d+)?)', next_line)
                        for tag in tags:
                            if tag not in descriptions:
                                descriptions[tag] = comment
            i += 1

        print(f"    -> {len(descriptions)} L5K descriptions")

    except Exception as e:
        print(f"    -> Error: {e}")

    return descriptions


def enrich_from_l5k(df, l5k_path):
    """
    Enrich DataFrame with L5K descriptions.

    Only fills empty Description fields. Returns df.
    """
    if not l5k_path or not os.path.exists(l5k_path):
        return df

    descriptions = load_l5k_data(l5k_path)
    if not descriptions:
        return df

    enriched = 0
    for idx, row in df.iterrows():
        current_desc = row.get('Description', '')
        if not current_desc or pd.isna(current_desc) or current_desc == '':
            io_address = str(row['IO Address'])
            io_clean = normalize_for_lookup(io_address)
            desc = descriptions.get(io_address) or descriptions.get(io_clean)
            if desc:
                df.at[idx, 'Description'] = desc
                df.at[idx, 'Description Source'] = 'L5K'
                enriched += 1

    print(f"    -> {enriched} descriptions from L5K")
    return df
