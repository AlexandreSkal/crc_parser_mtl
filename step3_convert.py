#!/usr/bin/env python3
"""
Step 3: Convert enriched IOs to Master Tag List (MTL) format.
"""

import os
import sys

from config import ENRICHED_PATH, FINAL_MTL_PATH, OUTPUT_DIR


def main():
    print("=" * 70)
    print("STEP 3: CONVERT TO MASTER TAG LIST")
    print("=" * 70)

    if not os.path.exists(ENRICHED_PATH):
        print(f"\nERROR: {ENRICHED_PATH} not found. Run step2 first.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    from converters.mtl_builder import convert_to_mtl
    convert_to_mtl(ENRICHED_PATH, FINAL_MTL_PATH)

    print("\n" + "=" * 70)
    print("STEP 3 COMPLETE!")
    print("=" * 70)
    print(f"\n  Output: {FINAL_MTL_PATH}")


if __name__ == '__main__':
    main()
