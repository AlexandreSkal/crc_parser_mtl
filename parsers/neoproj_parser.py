"""
NeoProj Parser — Extract IOs from IX Developer project files.

Data source priority:
  1. External Export files (Tags Export.xlsx) in INPUT_DIR
  2. Export files inside the NeoProj .zip
  3. Direct .neo file parsing (Tags.neo + Controller*.neo + AlarmServer.neo)  ← NEW fallback
  4. XAML parsing (for screen usage information only)
"""

import os
import re
import glob
import zipfile
import tempfile
import shutil
from collections import defaultdict
from xml.etree import ElementTree as ET

import pandas as pd

from utils.neoproj_zip import extract_neoproj_zip


# XML namespace used in all .neo files
_NS = 'urn:Neo.ApplicationFramework.Serializer'


# =============================================================================
# EXPORT FILE LOADERS  (priority 1 & 2 — Tags Export .xlsx / .xls)
# =============================================================================

def read_excel_file(file_path):
    """
    Read Excel file (.xlsx via openpyxl, .xls via xlrd).
    Returns DataFrame or None.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    try:
        if file_path.lower().endswith('.xls') and not file_path.lower().endswith('.xlsx'):
            try:
                return pd.read_excel(file_path, engine='xlrd')
            except ImportError:
                print(f"    ERROR: .xls requires xlrd — run: pip install xlrd")
                print(f"    Or convert to .xlsx: Open in Excel → Save As → Excel Workbook (.xlsx)")
                return None
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

    df = df.rename(columns={'// Name': 'Name', 'Address_1': 'Address'})
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

    df = df.rename(columns={'// Name': 'AlarmName', 'Text': 'AlarmText'})
    useful = ['AlarmName', 'AlarmText', 'DataConnection']
    df = df[[c for c in useful if c in df.columns]]
    print(f"    -> {len(df)} alarms loaded")
    return df


def find_export_files_in_dir(directory):
    """Find Tags Export and Alarms Export files in a directory (recursive, flexible naming)."""
    tags, alarms = None, None

    tag_patterns = [
        '*_Tags Export.xls*', '*_Tags_Export.xls*', '*TagsExport.xls*',
        '*Tags Export.xls*', '*tags export.xls*', '*tags_export.xls*',
        '* Tags Export.xls*',
    ]
    alarm_patterns = [
        '*_Alarms Export.xls*', '*_Alarms_Export.xls*', '*AlarmsExport.xls*',
        '*Alarms Export.xls*', '*alarms export.xls*', '*alarms_export.xls*',
        '* Alarms Export.xls*',
    ]

    for pattern in tag_patterns:
        matches = glob.glob(os.path.join(directory, '**', pattern), recursive=True)
        if matches:
            tags = matches[0]
            break

    for pattern in alarm_patterns:
        matches = glob.glob(os.path.join(directory, '**', pattern), recursive=True)
        if matches:
            alarms = matches[0]
            break

    return tags, alarms


# =============================================================================
# DIRECT .NEO PARSER  (priority 3 — no export files needed)
# =============================================================================

def _neo_attr(element, attr):
    """Get namespaced attribute from a .neo XML element."""
    return element.get(f'{{{_NS}}}{attr}', '')


def _parse_controller_neo(content):
    """
    Parse Controller*.neo → {DataItemName: PLC_Address}.
    Handles multiple controllers; merges all into one map.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"    WARNING: Could not parse controller file: {e}")
        return {}

    dataitem_map = {}
    for obj in root.iter('Object'):
        type_attr = _neo_attr(obj, 'type')
        if 'DataItem,' in type_attr or 'DataItem"' in type_attr:
            name = _neo_attr(obj, 'Site.Name')
            item_id = obj.get('ItemID', '')
            if name:
                dataitem_map[name] = item_id
    return dataitem_map


def _parse_tags_neo(content, dataitem_map):
    """
    Parse Tags.neo → list of {Name, DataType, Address}.
    Cross-references DataItem names with the controller map for PLC addresses.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"    WARNING: Could not parse Tags.neo: {e}")
        return []

    tags = []
    for obj in root.iter('Object'):
        type_attr = _neo_attr(obj, 'type')
        if 'GlobalDataItem,' not in type_attr:
            continue

        name = _neo_attr(obj, 'Site.Name')
        dtype = obj.get('DataType', '')
        if not name or name == 'Tag1':
            continue

        # Resolve PLC address via DataItemNames KeyValuePairs
        address = ''
        for kv in obj.iter('KeyValuePair'):
            children = list(kv)
            if len(children) >= 2:
                key_obj = children[0].find('Object')
                val_obj = children[1].find('Object')
                if key_obj is not None and val_obj is not None:
                    data_item_ref = val_obj.get('primitive.value', '')
                    if data_item_ref in dataitem_map:
                        address = dataitem_map[data_item_ref]
                        break  # first controller match is enough

        tags.append({'Name': name, 'DataType': dtype, 'Address': address})

    return tags


def _parse_alarmserver_neo(content):
    """
    Parse AlarmServer.neo → list of {AlarmText, DataConnection}.
    DataConnection format: 'Tags.ControllerN_TAG_NAME'
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"    WARNING: Could not parse AlarmServer.neo: {e}")
        return []

    alarms = []
    for obj in root.iter('Object'):
        type_attr = _neo_attr(obj, 'type')
        if 'AlarmItem,' not in type_attr:
            continue

        text = obj.get('StaticText', '') or obj.get('DefaultText', '')
        datasource = ''
        for param in obj.iter('Parameter'):
            if param.get('Name') == 'DataSource':
                datasource = param.get('Value', '')
                break

        if text or datasource:
            alarms.append({'AlarmText': text, 'DataConnection': datasource})

    return alarms


def extract_from_neo_files(zip_path=None, project_dir=None):
    """
    Extract tags and alarms directly from .neo project files.

    Works with either an open zip (pass zip_path) or an already-extracted
    directory (pass project_dir).

    Returns:
        (tags_df, alarms_df) — DataFrames matching the export file format.
    """
    print("\n  Falling back to direct .neo file parsing...")

    def _read_from_zip(zf, filename):
        """Try to read a file from zip, return decoded string or None."""
        try:
            return zf.read(filename).decode('utf-8', errors='ignore')
        except KeyError:
            return None

    def _read_from_dir(directory, filename):
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return None

    # Choose read strategy
    if zip_path and os.path.exists(zip_path):
        zf = zipfile.ZipFile(zip_path, 'r')
        read_fn = lambda fn: _read_from_zip(zf, fn)
        all_names = zf.namelist()
    elif project_dir and os.path.exists(project_dir):
        zf = None
        read_fn = lambda fn: _read_from_dir(project_dir, fn)
        all_names = os.listdir(project_dir)
    else:
        print("    ERROR: No zip or directory available for .neo parsing")
        return pd.DataFrame(), pd.DataFrame()

    try:
        # --- Build dataitem map from all Controller*.neo files ---
        dataitem_map = {}
        controller_files = [n for n in all_names
                            if os.path.basename(n).startswith('Controller') and n.endswith('.neo')]
        if not controller_files:
            print("    WARNING: No Controller*.neo files found")
        for cf in controller_files:
            content = read_fn(cf)
            if content:
                partial = _parse_controller_neo(content)
                dataitem_map.update(partial)
                print(f"    Controller: {os.path.basename(cf)} — {len(partial)} data items")

        # --- Parse Tags.neo ---
        tags_content = read_fn('Tags.neo')
        if not tags_content:
            print("    ERROR: Tags.neo not found in project")
            return pd.DataFrame(), pd.DataFrame()

        raw_tags = _parse_tags_neo(tags_content, dataitem_map)
        print(f"    Tags.neo — {len(raw_tags)} tags parsed")

        # Convert to DataFrame matching export format
        tags_df = pd.DataFrame(raw_tags)
        if not tags_df.empty:
            # Normalize DataType to match export convention (DT_REAL4 → FLOAT, DT_BOOLEAN → BOOL)
            dtype_map = {
                'DT_REAL4': 'FLOAT', 'DT_REAL8': 'DOUBLE',
                'DT_INT2': 'INTEGER', 'DT_INT4': 'LONG',
                'DT_BOOLEAN': 'BOOL', 'DT_STRING': 'STRING',
            }
            tags_df['DataType'] = tags_df['DataType'].replace(dtype_map)
            tags_df['Description'] = ''  # .neo doesn't store descriptions

        # --- Parse AlarmServer.neo ---
        alarm_content = read_fn('AlarmServer.neo')
        alarms_df = pd.DataFrame()
        if alarm_content:
            raw_alarms = _parse_alarmserver_neo(alarm_content)
            print(f"    AlarmServer.neo — {len(raw_alarms)} alarms parsed")
            if raw_alarms:
                alarms_df = pd.DataFrame(raw_alarms)
                alarms_df.rename(columns={'AlarmText': 'AlarmText', 'DataConnection': 'DataConnection'},
                                 inplace=True)
        else:
            print("    AlarmServer.neo not found — no alarms")

        return tags_df, alarms_df

    finally:
        if zf:
            zf.close()


# =============================================================================
# XAML SCREEN USAGE PARSER  (priority 4 — screen mapping only)
# =============================================================================

def extract_screen_usage(project_dir):
    """
    Scan XAML files to find which screens reference each tag.
    Returns dict: {tag_name: set(screen_names)}
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
    if not address or (isinstance(address, float)):
        return 'UNKNOWN'
    addr = str(address).upper()
    if 'ALARM' in addr:
        return 'ALARM'
    if 'WRITEFLOAT' in addr:
        return 'SETPOINT'
    if 'READFLOAT' in addr:
        return 'CALCULATED'
    if 'RACK' in addr:
        return 'DISCRETE_IO' if data_type in ('BOOL', 'DT_BOOLEAN') else 'ANALOG_IO'
    if 'BIT' in addr or addr.startswith('B'):
        return 'DISCRETE_IO'
    if addr.startswith('F') or addr.startswith('N') or addr.startswith('D'):
        return 'ANALOG_IO'
    return 'OTHER'


def extract_tag_id_from_description(description):
    """Extract ISA tag ID (e.g. PIT-701) from description text."""
    if not description:
        return ''
    match = re.search(r'\b([A-Z]{2,5}[-_]\d+[A-Z]?)\b', str(description))
    return match.group(1).replace('_', '-') if match else ''


def extract_unit_from_description(description):
    """Extract engineering unit from description text."""
    if not description:
        return ''
    units = r'\b(PSIG|PSIA|PSI|%|DEGF|DEGC|GPM|BPD|MCF|MCFD|MSCF|MA|VDC|VAC|HZ|IN|BBLS|BOPD|MSCFD)\b'
    match = re.search(units, str(description), re.IGNORECASE)
    return match.group(1).upper() if match else ''


# =============================================================================
# PROCESS TAGS → STANDARD OUTPUT FORMAT
# =============================================================================

def process_tags_data(tags_df, alarms_df, tag_screens):
    """
    Merge tags + alarms + screen usage into the standard pipeline DataFrame.
    """
    print("\n  Processing tags into standard format...")
    if tags_df.empty:
        return pd.DataFrame()

    # Build alarm text lookup: tag_name → alarm_text
    alarm_lookup = {}
    if not alarms_df.empty and 'DataConnection' in alarms_df.columns:
        for _, row in alarms_df.iterrows():
            dc = str(row.get('DataConnection', ''))
            if dc.startswith('Tags.'):
                tag_key = dc[5:]  # strip 'Tags.' prefix
                alarm_lookup[tag_key] = row.get('AlarmText', '')

    results = []
    for _, row in tags_df.iterrows():
        name = str(row['Name'])
        data_type = str(row.get('DataType', ''))
        address = str(row.get('Address', ''))
        description = str(row.get('Description', '')) if pd.notna(row.get('Description')) else ''

        # Fall back 1: alarm text
        if not description and name in alarm_lookup:
            description = alarm_lookup[name]

        # Fall back 2: derive description from HMI tag name itself
        # e.g. "Controller1_PIT_100_POOL_SEPARATOR_V100_DISCH_PRESS"
        #   →  "PIT 100 POOL SEPARATOR V100 DISCH PRESS"
        desc_source = 'Tags_Export' if description else ''
        if not description and name and name != 'nan':
            derived = re.sub(r'^Controller\d+_', '', name).replace('_', ' ')
            description = derived
            desc_source = 'HMI_Tag_Name'

        screens = tag_screens.get(name, set())

        results.append({
            'IO Address':          address,
            'HMI Tag Name':        f"Tags.{name}",
            'DataType':            data_type,
            'IO Type':             classify_io_type(address, data_type),
            'target_id_rack':      extract_tag_id_from_description(description),
            'target_units':        extract_unit_from_description(description),
            'rack_description':    '',
            'Description':         description,
            'Description Source':  desc_source,
            'Number of Screens':   len(screens),
            'Screens':             ', '.join(sorted(screens)),
        })

    df = pd.DataFrame(results)

    total = len(df)
    print(f"\n  Stats: {total} tags, "
          f"{len(df[df['target_id_rack'] != ''])} with tag_id, "
          f"{len(df[df['Description'] != ''])} with desc, "
          f"{len(df[df['Number of Screens'] > 0])} used in screens")

    return df


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def _find_project_dir(root):
    """
    Given the root of an extracted NeoProj ZIP, return the directory that
    actually contains the project files (.xaml / .neo).

    Some ZIPs have all files at root level; others wrap them in a single
    subfolder. The Symbols/ folder (images only) must not be mistaken for
    the project dir.
    """
    # Root itself has project files?
    if glob.glob(os.path.join(root, '*.xaml')) or glob.glob(os.path.join(root, '*.neo')):
        return root
    # Check one level of subdirectories
    for entry in sorted(os.listdir(root)):
        full = os.path.join(root, entry)
        if os.path.isdir(full):
            if glob.glob(os.path.join(full, '*.xaml')) or glob.glob(os.path.join(full, '*.neo')):
                return full
    return root  # fallback


def extract_from_neoproj(neoproj_path, input_dir, tags_export_path=None,
                          alarms_export_path=None, filter_unused=False):
    """
    Main extraction entry point for NeoProj projects.

    Priority order:
      1. Explicit tags_export_path argument
      2. Auto-detect Tags Export file in input_dir
      3. Auto-detect Tags Export file inside ZIP
      4. Direct .neo file parsing (Tags.neo + Controller*.neo + AlarmServer.neo)

    Args:
        neoproj_path:      Path to .zip or folder
        input_dir:         Directory to search for export files
        tags_export_path:  Explicit path to Tags Export (or None for auto-detect)
        alarms_export_path: Explicit path to Alarms Export (or None for auto-detect)
        filter_unused:     Remove tags not used in any screen

    Returns:
        DataFrame with extracted IOs
    """
    zip_temp_dir = None
    project_dir = None

    try:
        # ── Show what we received ──────────────────────────────────────────
        print("\n  Checking for Export files...")
        if tags_export_path:
            print(f"    Tags Export (explicit): {os.path.basename(tags_export_path)}")
        if alarms_export_path:
            print(f"    Alarms Export (explicit): {os.path.basename(alarms_export_path)}")

        # ── Extract ZIP to temp dir if needed ─────────────────────────────
        if neoproj_path and os.path.exists(neoproj_path):
            if neoproj_path.lower().endswith('.zip'):
                zip_temp_dir = tempfile.mkdtemp(prefix='neoproj_extract_')
                extract_neoproj_zip(neoproj_path, zip_temp_dir)
                project_dir = _find_project_dir(zip_temp_dir)
            else:
                project_dir = neoproj_path

        # ── Priority 2: auto-detect export in input_dir ───────────────────
        if not tags_export_path:
            t, a = find_export_files_in_dir(input_dir)
            if t:
                tags_export_path = t
                print(f"    Tags Export (auto): {os.path.basename(t)}")
            if a and not alarms_export_path:
                alarms_export_path = a
                print(f"    Alarms Export (auto): {os.path.basename(a)}")

        # ── Priority 3: auto-detect export inside ZIP ─────────────────────
        if not tags_export_path and project_dir:
            t, a = find_export_files_in_dir(project_dir)
            if t:
                tags_export_path = t
                print(f"    Tags Export (in ZIP): {os.path.basename(t)}")
            if a and not alarms_export_path:
                alarms_export_path = a
                print(f"    Alarms Export (in ZIP): {os.path.basename(a)}")

        # ── Load data ──────────────────────────────────────────────────────
        if tags_export_path:
            # Normal path: use export files
            tags_df   = load_tags_export(tags_export_path)
            alarms_df = load_alarms_export(alarms_export_path) if alarms_export_path else pd.DataFrame()
        else:
            # Priority 4: fallback to direct .neo parsing
            print("\n  No Tags Export file found — switching to direct .neo parsing")
            tags_df, alarms_df = extract_from_neo_files(
                zip_path=neoproj_path if (neoproj_path and neoproj_path.endswith('.zip')) else None,
                project_dir=project_dir,
            )
            if tags_df.empty:
                print("\n  ERROR: Could not extract tags from .neo files either!")
                return pd.DataFrame()

        # ── Screen usage from XAML ─────────────────────────────────────────
        tag_screens = extract_screen_usage(project_dir) if project_dir else {}

        # ── Build result DataFrame ─────────────────────────────────────────
        result_df = process_tags_data(tags_df, alarms_df, tag_screens)

        if filter_unused and not result_df.empty:
            before = len(result_df)
            result_df = result_df[result_df['Number of Screens'] > 0]
            print(f"\n  Filtered {before - len(result_df)} unused tags")

        return result_df

    finally:
        if zip_temp_dir and os.path.exists(zip_temp_dir):
            shutil.rmtree(zip_temp_dir, ignore_errors=True)