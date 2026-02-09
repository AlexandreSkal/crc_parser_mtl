#!/usr/bin/env python3
"""
Step 2: Enrich IOs with additional data sources.

Sources (applied in order):
  1. CPA RACK / Discrete / Analog screens (CPA projects)
  2. NeoProj RACK XAML screens (NeoProj projects)
  3. Rockwell CSV export (COMMENT + ALIAS)
  4. Rockwell L5K export
"""

import os
import sys
import pandas as pd

from config import (
    HMI_TYPE, CPA_PATH, NEOPROJ_PATH, CSV_PATH, L5K_PATH,
    EXTRACTED_PATH, ENRICHED_PATH, OUTPUT_DIR,
    ENABLE_CSV, ENABLE_L5K, FILTER_UNUSED_IOS,
)


def main():
    print("=" * 70)
    print("STEP 2: ENRICH DESCRIPTIONS")
    print("=" * 70)

    if not os.path.exists(EXTRACTED_PATH):
        print(f"\nERROR: {EXTRACTED_PATH} not found. Run step1 first.")
        sys.exit(1)

    # Load Step 1 output
    print(f"\n  Loading: {EXTRACTED_PATH}")
    df = pd.read_excel(EXTRACTED_PATH)
    print(f"  -> {len(df)} IOs")

    # Ensure enrichment columns exist
    for col in ['target_id_rack', 'target_units', 'rack_description', 'Description', 'Description Source']:
        if col not in df.columns:
            df[col] = ''
    df = df.fillna({'target_id_rack': '', 'target_units': '', 'rack_description': '',
                     'Description': '', 'Description Source': ''})

    # Enrich from HMI screens
    if HMI_TYPE.upper() == 'CPA' and CPA_PATH and os.path.exists(CPA_PATH):
        print("\n--- CPA Screen Enrichment ---")
        from enrichers.cpa_screen_enricher import enrich_from_cpa_screens
        df = enrich_from_cpa_screens(df, CPA_PATH)

    elif HMI_TYPE.upper() == 'NEOPROJ' and NEOPROJ_PATH and os.path.exists(NEOPROJ_PATH):
        print("\n--- NeoProj RACK Screen Enrichment ---")
        from enrichers.neoproj_rack_enricher import enrich_from_neoproj_rack
        df = enrich_from_neoproj_rack(df, NEOPROJ_PATH)

    # Enrich from CSV
    if ENABLE_CSV and CSV_PATH and os.path.exists(CSV_PATH):
        print("\n--- CSV Enrichment ---")
        from enrichers.csv_enricher import enrich_from_csv
        df = enrich_from_csv(df, CSV_PATH)

    # Enrich from L5K
    if ENABLE_L5K and L5K_PATH and os.path.exists(L5K_PATH):
        print("\n--- L5K Enrichment ---")
        from enrichers.l5k_enricher import enrich_from_l5k
        df = enrich_from_l5k(df, L5K_PATH)

    # Filter unused
    if FILTER_UNUSED_IOS:
        before = len(df)
        df = df[df['Number of Screens'] > 0]
        print(f"\n  Filtered {before - len(df)} unused IOs")

    # Stats
    total = len(df)
    print(f"\n--- Final Stats ({total} IOs) ---")
    print(f"  With tag_id:      {len(df[df['target_id_rack'] != ''])}")
    print(f"  With units:       {len(df[df['target_units'] != ''])}")
    print(f"  With description: {len(df[df['Description'] != ''])}")

    # Reorder columns
    col_order = [
        'IO Address', 'HMI Tag Name', 'DataType', 'IO Type',
        'target_id_rack', 'target_units', 'rack_description',
        'Description', 'Description Source', 'Number of Screens', 'Screens',
    ]
    df = df[[c for c in col_order if c in df.columns]]

    # Save
    os.makedirs(os.path.dirname(ENRICHED_PATH), exist_ok=True)
    with pd.ExcelWriter(ENRICHED_PATH, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Enriched IOs', index=False)
        ws = writer.sheets['Enriched IOs']
        widths = {'A': 25, 'B': 60, 'C': 10, 'D': 12, 'E': 15,
                  'F': 12, 'G': 40, 'H': 60, 'I': 15, 'J': 10, 'K': 50}
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    print(f"\n  Saved: {ENRICHED_PATH} ({len(df)} rows)")
    print("\n" + "=" * 70)
    print("STEP 2 COMPLETE → Next: python step3_convert.py")
    print("=" * 70)


if __name__ == '__main__':
    main()
