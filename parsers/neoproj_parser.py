"""
NeoProj Parser — Extract IOs from IX Developer project files.

Data source priority:
  1. External Export files (Tags Export.xls, Alarms Export.xls) in INPUT_DIR
  2. Export files inside the NeoProj .zip
  3. XAML parsing (for screen usage information only)
"""

import os
import re
import glob
import tempfile
import shutil
from collections import defaultdict

import pandas as pd

from utils.neoproj_zip import extract_neoproj_zip


# =============================================================================
# EXPORT FILE LOADERS
# =============================================================================

def read_excel_file(file_path):
    """
    Read Excel file (.xlsx only — .xls not supported by openpyxl).

    Returns DataFrame or None.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    if file_path.lower().endswith('.xls') and not file_path.lower().endswith('.xlsx'):
        print(f"    ERROR: .xls format not supported!")
        print(f"    Please convert to .xlsx: Open in Excel → Save As → Excel Workbook (.xlsx)")
        return None

    try:
        return pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        print(f"    ERROR reading {file_path}: {e}")
        return None


def load_tags_export(file_path):
    """Load Tags Export file → DataFrame with Name, DataType, Address, Description."""
    print(f"\n  Loading Tags Export: {os.path.basename(file_path)}")
    df = read_excel_file(file_path)
    if df is None:
        return pd.DataFrame()

    df = df.rename(columns={
        '// Name': 'Name', 'Address_1': 'Address',
    })
    useful = ['Name', 'DataType', 'Address', 'Description']
    df = df[[c for c in useful if c in df.columns]]

    print(f"    -> {len(df)} tags loaded")
    return df


def load_alarms_export(file_path):
    """Load Alarms Export file → DataFrame with AlarmName, AlarmText, DataConnection."""
    print(f"\n  Loading Alarms Export: {os.path.basename(file_path)}")
    df = read_excel_file(file_path)
    if df is None:
        return pd.DataFrame()

    df = df.rename(columns={
        '// Name': 'AlarmName', 'Text': 'AlarmText',
    })
    useful = ['AlarmName', 'AlarmText', 'DataConnection']
    df = df[[c for c in useful if c in df.columns]]

    print(f"    -> {len(df)} alarms loaded")
    return df


def find_export_files_in_dir(directory):
    """Find Tags Export and Alarms Export files in a directory."""
    tags, alarms = None, None
    for pattern in ['*_Tags Export.xls*', '*_Tags_Export.xls*', '*TagsExport.xls*']:
        matches = glob.glob(os.path.join(directory, pattern))
        if matches:
            tags = matches[0]
            break
    for pattern in ['*_Alarms Export.xls*', '*_Alarms_Export.xls*', '*AlarmsExport.xls*']:
        matches = glob.glob(os.path.join(directory, pattern))
        if matches:
            alarms = matches[0]
            break
    return tags, alarms


# =============================================================================
# XAML SCREEN USAGE PARSER
# =============================================================================

def extract_screen_usage(project_dir):
    """
    Scan XAML files to find which screens reference each tag.

    Returns:
        dict: {tag_name: set(screen_names)}
    """
    if not project_dir or not os.path.exists(project_dir):
        return {}

    xaml_files = glob.glob(os.path.join(project_dir, '*.xaml'))
    if not xaml_files:
        return {}

    print(f"\n  Scanning {len(xaml_files)} XAML files for screen usage...")
    tag_pattern = re.compile(r'Path="\[Tags\.([^\]]+)\]', re.IGNORECASE)
    tag_screens = defaultdict(set)

    for xaml_path in xaml_files:
        screen_name = os.path.splitext(os.path.basename(xaml_path))[0]
        with open(xaml_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for m in tag_pattern.finditer(content):
            tag_screens[m.group(1)].add(screen_name)

    print(f"    -> {len(tag_screens)} tags found in screens")
    return tag_screens


# =============================================================================
# TAG CLASSIFICATION HELPERS
# =============================================================================

def classify_io_type(address, data_type):
    """Classify IO type from PLC address pattern."""
    if not address or pd.isna(address):
        return 'UNKNOWN'
    addr = str(address).upper()
    if 'ALARM' in addr:
        return 'ALARM'
    if 'WRITEFLOAT' in addr:
        return 'SETPOINT'
    if 'READFLOAT' in addr:
        return 'CALCULATED'
    if 'RACK' in addr:
        return 'DISCRETE_IO' if data_type == 'BOOL' else 'ANALOG_IO'
    if 'BIT' in addr:
        return 'INTERNAL_BIT'
    return 'OTHER'


def extract_tag_id_from_description(description):
    """
    Extract ISA tag ID from description text.

    Examples:
        "TEST HEADER PRESS (PIT-110)" → "PIT-110"
        "V-700 LP SEPARATOR LEVEL LSHH-701" → "LSHH-701"
    """
    if not description or pd.isna(description):
        return ''
    desc = str(description)

    # Tag in parentheses
    m = re.search(r'\(([A-Z]{2,6}[-_]\d+[A-Z]?)\)', desc)
    if m:
        return m.group(1).replace('_', '-')

    # Alarm/Switch tag
    m = re.search(
        r'\b((?:PAHH|PAH|PAL|PALL|TAHH|TAH|TAL|TALL|LAHH|LAH|LAL|LALL|LSHH|LSH|LSL|LSLL)[-_]\d+[A-Z]?)\b',
        desc,
    )
    if m:
        return m.group(1).replace('_', '-')

    # Transmitter tag
    m = re.search(r'\b((?:PIT|LIT|TIT|FIT|FQIT|AIT|PDT)[-_]\d+[A-Z]?)\b', desc)
    if m:
        return m.group(1).replace('_', '-')

    # Valve/Control tag
    m = re.search(r'\b((?:PY|LY|TY|FY|XY|ZSO|ZSC|PCV|LCV|TCV|FCV)[-_]\d+[A-Z]?)\b', desc)
    if m:
        return m.group(1).replace('_', '-')

    # Tag at start of description
    m = re.match(r'^([A-Z]{2,6}[-_]\d+[A-Z]?)\s', desc)
    if m:
        return m.group(1).replace('_', '-')

    return ''


def extract_unit_from_description(description):
    """
    Extract engineering unit from description.

    Examples:
        "(0-250 PSIG)" → "PSIG"
        "(0-100%)" → "%"
    """
    if not description or pd.isna(description):
        return ''
    desc = str(description)

    m = re.search(r'\([\d\-,\s]+\s*([A-Z%]+)\)$', desc)
    if m:
        return m.group(1)
    m = re.search(r',\s*[\d\-]+\s*([A-Z]+)\)', desc)
    if m:
        return m.group(1)
    if re.search(r'\d+-\d+%|\(\d+%\)', desc):
        return '%'
    return ''


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_tags_data(tags_df, alarms_df, tag_screens):
    """
    Convert Tags/Alarms export data into the standard IO DataFrame.

    Returns:
        DataFrame with columns matching CPA output format.
    """
    print("\n  Processing tags into standard format...")
    if tags_df.empty:
        return pd.DataFrame()

    # Build alarm text lookup
    alarm_lookup = {}
    if not alarms_df.empty and 'DataConnection' in alarms_df.columns:
        for _, row in alarms_df.iterrows():
            dc = str(row.get('DataConnection', ''))
            if dc.startswith('Tags.'):
                alarm_lookup[dc[5:]] = row.get('AlarmText', '')

    results = []
    for _, row in tags_df.iterrows():
        name = str(row['Name'])
        data_type = str(row.get('DataType', ''))
        address = str(row.get('Address', ''))
        description = str(row.get('Description', '')) if pd.notna(row.get('Description')) else ''

        if not description and name in alarm_lookup:
            description = alarm_lookup[name]

        screens = tag_screens.get(name, set())

        results.append({
            'IO Address': address,
            'HMI Tag Name': f"Tags.{name}",
            'DataType': data_type,
            'IO Type': classify_io_type(address, data_type),
            'target_id_rack': extract_tag_id_from_description(description),
            'target_units': extract_unit_from_description(description),
            'rack_description': '',
            'Description': description,
            'Description Source': 'Tags_Export' if description else '',
            'Number of Screens': len(screens),
            'Screens': ', '.join(sorted(screens)),
        })

    df = pd.DataFrame(results)

    # Stats
    total = len(df)
    print(f"\n  Stats: {total} tags, "
          f"{len(df[df['target_id_rack'] != ''])} with tag_id, "
          f"{len(df[df['Description'] != ''])} with desc, "
          f"{len(df[df['Number of Screens'] > 0])} used in screens")

    return df


def extract_from_neoproj(neoproj_path, input_dir, tags_export_path=None,
                          alarms_export_path=None, filter_unused=False):
    """
    Main extraction entry point for NeoProj projects.

    Args:
        neoproj_path: Path to .zip or folder
        input_dir: Directory to search for export files
        tags_export_path: Explicit path to Tags Export (or None for auto-detect)
        alarms_export_path: Explicit path to Alarms Export (or None for auto-detect)
        filter_unused: Remove tags not used in any screen

    Returns:
        DataFrame with extracted IOs
    """
    zip_temp_dir = None
    project_dir = None

    try:
        # Check external exports
        print("\n  Checking for Export files...")
        if tags_export_path:
            print(f"    Tags Export: {os.path.basename(tags_export_path)}")
        if alarms_export_path:
            print(f"    Alarms Export: {os.path.basename(alarms_export_path)}")

        # Extract ZIP if needed
        if neoproj_path and os.path.exists(neoproj_path):
            if neoproj_path.lower().endswith('.zip'):
                zip_temp_dir = tempfile.mkdtemp(prefix='neoproj_extract_')
                extract_neoproj_zip(neoproj_path, zip_temp_dir)
                subdirs = [d for d in os.listdir(zip_temp_dir)
                           if os.path.isdir(os.path.join(zip_temp_dir, d))]
                project_dir = os.path.join(zip_temp_dir, subdirs[0]) if subdirs else zip_temp_dir
            else:
                project_dir = neoproj_path

            # Look for export files inside ZIP if not found externally
            if not tags_export_path:
                zt, za = find_export_files_in_dir(project_dir)
                if zt:
                    tags_export_path = zt
                if za and not alarms_export_path:
                    alarms_export_path = za

        if not tags_export_path:
            print("\n  ERROR: No Tags Export file found!")
            return pd.DataFrame()

        # Load data
        tags_df = load_tags_export(tags_export_path)
        alarms_df = load_alarms_export(alarms_export_path) if alarms_export_path else pd.DataFrame()

        # Get screen usage
        tag_screens = extract_screen_usage(project_dir) if project_dir else {}

        # Process
        result_df = process_tags_data(tags_df, alarms_df, tag_screens)

        if filter_unused and not result_df.empty:
            before = len(result_df)
            result_df = result_df[result_df['Number of Screens'] > 0]
            print(f"\n  Filtered {before - len(result_df)} unused tags")

        return result_df

    finally:
        if zip_temp_dir and os.path.exists(zip_temp_dir):
            shutil.rmtree(zip_temp_dir, ignore_errors=True)
