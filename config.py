"""
Configuration — All paths and settings in one place.

Supports:
  - CPA files (PanelBuilder / CIMREX)
  - NeoProj files (IX Developer) — .zip or extracted folder
  - External Export files (Tags Export, Alarms Export)
"""

import os
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# HMI TYPE — Choose one: "CPA" or "NEOPROJ"
# =============================================================================
HMI_TYPE = "CPA"

# =============================================================================
# INPUT FILES
# =============================================================================

# CPA (PanelBuilder / CIMREX)
CPA_FILE = "NU_TF_1C_6D.cpa"

# NeoProj (IX Developer) — .zip file or folder name
NEOPROJ_FILE = ".zip"

# IX Developer Export Files (optional, auto-detected if empty)
TAGS_EXPORT_FILE = ""       # e.g. "NU_36B_4B_TS_Tags Export.xls"
ALARMS_EXPORT_FILE = ""     # e.g. "NU_36B_4B_TS_Alarms Export.xls"

# Rockwell exports (optional — set to "" to disable)
CSV_FILE = ""               # e.g. "NU_TF_20B.CSV"
L5K_FILE = ""               # e.g. "NU_TF_20B.L5K"

# =============================================================================
# OUTPUT FILES
# =============================================================================
EXTRACTED_IOS_FILE = "01_extracted_ios.xlsx"
ENRICHED_IOS_FILE = "02_enriched_ios.xlsx"
FINAL_MTL_FILE = "03_MASTER_TAG_LIST.xlsx"

# =============================================================================
# PATHS (built automatically)
# =============================================================================
INPUT_DIR = os.path.join(BASE_DIR, "data", "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")

CPA_PATH = os.path.join(INPUT_DIR, CPA_FILE) if CPA_FILE else None
NEOPROJ_PATH = os.path.join(INPUT_DIR, NEOPROJ_FILE) if NEOPROJ_FILE else None
CSV_PATH = os.path.join(INPUT_DIR, CSV_FILE) if CSV_FILE else None
L5K_PATH = os.path.join(INPUT_DIR, L5K_FILE) if L5K_FILE else None

EXTRACTED_PATH = os.path.join(OUTPUT_DIR, EXTRACTED_IOS_FILE)
ENRICHED_PATH = os.path.join(OUTPUT_DIR, ENRICHED_IOS_FILE)
FINAL_MTL_PATH = os.path.join(OUTPUT_DIR, FINAL_MTL_FILE)

# =============================================================================
# PROCESSING OPTIONS
# =============================================================================
ENABLE_CSV = True
ENABLE_L5K = True
FILTER_UNUSED_IOS = False   # Remove tags not used in any screen

# Text processing
EXPAND_ABBREVIATIONS = True
APPLY_CAPITALIZATION = True
PRESERVE_ACRONYMS = True

# =============================================================================
# CPA-SPECIFIC OPTIONS
# =============================================================================
GRAPHIC_OBJECTS = [
    'GrAnaNumeric',
    'GrDigSymbol',
    'GrAnaBar',
    'GrMultipleChoice',
    'DigitalProperty',
    'GrDigText',
    'Alarm',
]

EXCLUDED_SCREENS = ['scrap', 'scrap 2']

# =============================================================================
# NEOPROJ-SPECIFIC OPTIONS
# =============================================================================
NEOPROJ_RACK_PREFIXES = ['RACK']
NEOPROJ_UNIT_X_RANGE = (320, 420)
NEOPROJ_TAG_X_RANGE = (400, 540)
NEOPROJ_DESC_X_RANGE = (540, 1200)
NEOPROJ_Y_TOLERANCE = 20

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_hmi_path():
    """Return the HMI file path based on HMI_TYPE."""
    if HMI_TYPE.upper() == "NEOPROJ":
        return NEOPROJ_PATH
    return CPA_PATH


def find_export_files():
    """
    Auto-detect Tags Export and Alarms Export files in INPUT_DIR.

    Returns:
        tuple: (tags_export_path, alarms_export_path) — None if not found
    """
    tags_export = _find_file(
        TAGS_EXPORT_FILE,
        ['*_Tags Export.xlsx', '*_Tags_Export.xlsx', '*TagsExport.xlsx',
         '*_Tags Export.xls', '*_Tags_Export.xls', '*TagsExport.xls'],
    )
    alarms_export = _find_file(
        ALARMS_EXPORT_FILE,
        ['*_Alarms Export.xlsx', '*_Alarms_Export.xlsx', '*AlarmsExport.xlsx',
         '*_Alarms Export.xls', '*_Alarms_Export.xls', '*AlarmsExport.xls'],
    )
    return tags_export, alarms_export


def _find_file(explicit_name, glob_patterns):
    """Try explicit name first, then glob patterns."""
    if explicit_name:
        path = os.path.join(INPUT_DIR, explicit_name)
        if os.path.exists(path):
            return path

    for pattern in glob_patterns:
        matches = glob.glob(os.path.join(INPUT_DIR, pattern))
        if matches:
            return matches[0]
    return None


# Convenience variables
HMI_PATH = get_hmi_path()
TAGS_EXPORT_PATH, ALARMS_EXPORT_PATH = find_export_files()


# =============================================================================
# DEBUG
# =============================================================================

def print_config():
    """Print current configuration."""
    print("=" * 70)
    print("CONFIGURATION")
    print("=" * 70)
    print(f"  HMI Type       : {HMI_TYPE}")
    print(f"  HMI Path       : {HMI_PATH}")
    print(f"  Tags Export    : {TAGS_EXPORT_PATH or '(not found)'}")
    print(f"  Alarms Export  : {ALARMS_EXPORT_PATH or '(not found)'}")
    print(f"  CSV            : {CSV_PATH or '(disabled)'}")
    print(f"  L5K            : {L5K_PATH or '(disabled)'}")
    print(f"  Output Dir     : {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == '__main__':
    print_config()
