#!/usr/bin/env python3
"""
Step 1: Extract IOs from HMI project file.

Routes to the appropriate parser based on HMI_TYPE in config.py:
  - CPA  → parsers.cpa_parser
  - NEOPROJ → parsers.neoproj_parser
"""

import os
import sys
import pandas as pd

from config import (
    HMI_TYPE, CPA_PATH, NEOPROJ_PATH, INPUT_DIR, OUTPUT_DIR,
    EXTRACTED_PATH, GRAPHIC_OBJECTS, EXCLUDED_SCREENS,
    FILTER_UNUSED_IOS, TAGS_EXPORT_PATH, ALARMS_EXPORT_PATH,
)


def run_cpa():
    """Extract IOs from CPA file."""
    from parsers.cpa_parser import extract_from_cpa

    if not CPA_PATH or not os.path.exists(CPA_PATH):
        print(f"ERROR: CPA file not found: {CPA_PATH}")
        print(f"  Place your .cpa file in: {INPUT_DIR}")
        sys.exit(1)

    ios_screens, descriptions, alarm_ios = extract_from_cpa(
        CPA_PATH, GRAPHIC_OBJECTS, EXCLUDED_SCREENS,
    )

    # Combine screen IOs and alarm IOs
    all_ios = set(ios_screens.keys()) | set(alarm_ios.keys())

    data = []
    for address in sorted(all_ios):
        screens = ios_screens.get(address, [])
        desc = descriptions.get(address, "")

        if desc:
            desc_source = "Alarm" if (address in alarm_ios and alarm_ios[address] == desc) else "IONaming"
        else:
            desc_source = ""

        data.append({
            'IO Address': address,
            'Description': desc,
            'Description Source': desc_source,
            'Number of Screens': len(screens),
            'Screens': ', '.join(sorted(screens)),
            'Is Alarm': 'Yes' if address in alarm_ios else 'No',
        })

    df = pd.DataFrame(data)
    df = df.sort_values(['Number of Screens', 'IO Address'], ascending=[False, True])
    return df


def run_neoproj():
    """Extract IOs from NeoProj project."""
    from parsers.neoproj_parser import extract_from_neoproj

    return extract_from_neoproj(
        NEOPROJ_PATH, INPUT_DIR,
        tags_export_path=TAGS_EXPORT_PATH,
        alarms_export_path=ALARMS_EXPORT_PATH,
        filter_unused=FILTER_UNUSED_IOS,
    )


def save_output(df, output_path):
    """Save DataFrame to Excel."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Extracted IOs', index=False)
        ws = writer.sheets['Extracted IOs']
        widths = {'A': 25, 'B': 60, 'C': 15, 'D': 12, 'E': 15,
                  'F': 12, 'G': 40, 'H': 60, 'I': 15, 'J': 10, 'K': 50}
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    print(f"\n  Saved: {output_path} ({len(df)} rows)")


def main():
    print("=" * 70)
    print(f"STEP 1: EXTRACT IOs ({HMI_TYPE})")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if HMI_TYPE.upper() == 'NEOPROJ':
        df = run_neoproj()
    else:
        df = run_cpa()

    if df is None or df.empty:
        print("ERROR: No IOs extracted!")
        sys.exit(1)

    save_output(df, EXTRACTED_PATH)

    # Stats
    total = len(df)
    with_desc = len(df[df['Description'].notna() & (df['Description'] != '')])
    print(f"\n  Total: {total} IOs, {with_desc} with descriptions ({with_desc/total*100:.1f}%)")

    print("\n" + "=" * 70)
    print("STEP 1 COMPLETE → Next: python step2_enrich.py")
    print("=" * 70)


if __name__ == '__main__':
    main()
