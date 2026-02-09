#!/usr/bin/env python3
"""
Run All Steps — Execute the complete extraction → enrichment → conversion pipeline.
"""

import os
import sys


def run_step(step_num, script):
    """Run a step script and return True if successful."""
    print(f"\n{'='*70}")
    print(f"RUNNING STEP {step_num}: {script}")
    print(f"{'='*70}\n")

    result = os.system(f"{sys.executable} {script}")
    if result != 0:
        print(f"\n[ERROR] Step {step_num} failed!")
        return False
    return True


def main():
    print("=" * 70)
    print("MTL CONVERTER — FULL PIPELINE")
    print("=" * 70)
    print("\n  1. Extract IOs from HMI file")
    print("  2. Enrich descriptions")
    print("  3. Convert to Master Tag List")
    print()

    input("Press ENTER to start (or Ctrl+C to cancel)...")

    steps = [
        (1, "step1_extract.py"),
        (2, "step2_enrich.py"),
        (3, "step3_convert.py"),
    ]

    for num, script in steps:
        if not run_step(num, script):
            print("\n[ERROR] Pipeline stopped.")
            return 1

    print("\n" + "=" * 70)
    print("ALL STEPS COMPLETE!")
    print("=" * 70)
    print("\nOutput files:")
    print("  1. data/output/01_extracted_ios.xlsx")
    print("  2. data/output/02_enriched_ios.xlsx")
    print("  3. data/output/03_MASTER_TAG_LIST.xlsx")
    return 0


if __name__ == '__main__':
    sys.exit(main())
