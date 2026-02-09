"""
Tag Classifier — ISA tag classification, alarm/switch detection, unit extraction.

All classification logic for converting raw IO data into MTL categories.
Each function is independent (no inter-dependencies) for easy maintenance.
"""

import re

from patterns import (
    ALARM_PATTERNS, SWITCH_PATTERNS, TRANSMITTER_PATTERNS,
    CONTROLLER_PATTERNS, VALVE_PATTERNS, CLASSIFICATION_KEYWORDS,
    TRANSMITTER_PREFIXES, VALID_TARGET_NAMES, IO_SUFFIXES,
)

# =============================================================================
# EXPANDED VALID TARGET NAMES (merged with patterns.py list)
# =============================================================================
VALID_TARGET_NAMES_MERGED = list(set(VALID_TARGET_NAMES))

# PLC SUFFIX → TND mapping (100% confidence)
PLC_SUFFIX_TO_TND = {
    ".SP": "Setpoint", ".PV": "Process Variable",
    ".OUT": "Control Variable", ".CV": "Control Variable",
    ".SWM": "Auto/Manual Mode", ".KP": "Proportional",
    ".KI": "Integral", ".KD": "Derivative",
    ".SO": "Manual Output", ".MAXO": "Maximum CV",
    ".MINO": "Minimum CV", ".PRE": "Sample Rate Setpoint",
}

# Default states for specific TNDs
DEFAULT_STATES = {
    "Lead/Lag Status": "1=P1 Lead;2=P2 Lead",
    "Lead Lag Status": "1=P1 Lead;2=P2 Lead",
    "Start Command": "1=Start", "Stop Command": "1=Stop",
    "Beacon Status": "0=On;1=Off", "State": "0=Off;1=On",
    "Solenoid Output Command": "0=De-energized;1=Energized",
    "Unit Loaded": "0=Loaded;1=Unloaded",
}

# Default scaling
DEFAULT_SCALING = {
    "Open Switch Status": "0=Not Open; 1=Open",
    "Closed Switch Status": "0=Not Closed; 1=Closed",
}


# =============================================================================
# CLASSIFICATION FUNCTIONS
# =============================================================================

def clean_tag_prefix(tag_id):
    """
    Remove invalid prefixes from tag_id like "1:" 
    
    Args:
        tag_id: Tag identifier string
    
    Returns:
        str: Cleaned tag_id without invalid prefixes
    """
    if not tag_id:
        return tag_id
    
    tag_str = str(tag_id)
    
    # Remove "1:" or any "N:" prefix at the start
    if re.match(r'^\d+:', tag_str):
        tag_str = re.sub(r'^\d+:', '', tag_str)
    
    return tag_str


def extract_plc_suffix(plc_path):
    """
    Extract suffix from PLC path (e.g., .SP, .PV, .OUT)
    
    Args:
        plc_path: PLC address string
    
    Returns:
        str or None: Suffix in uppercase (e.g., ".SP") or None
    """
    if not plc_path:
        return None
    match = re.search(r'\.([A-Za-z0-9_]+)$', str(plc_path))
    if match:
        return f".{match.group(1).upper()}"
    return None


def extract_plc_base(plc_path):
    """
    Extract base from PLC path (e.g., WRITEFLOAT, ALARM, INTEGER)
    
    Args:
        plc_path: PLC address string
    
    Returns:
        str or None: Base name in uppercase or None
    """
    if not plc_path:
        return None
    plc_upper = str(plc_path).upper()
    
    match = re.match(r'^([A-Z_]+)\[\d+\]', plc_upper)
    if match:
        return match.group(1)
    
    return None


def classify_by_plc_suffix(plc_path):
    """
    Classify TND by PLC path suffix.
    
    Args:
        plc_path: PLC address string
    
    Returns:
        str or None: TND if suffix matches, None otherwise
    """
    if not plc_path:
        return None
    
    match = re.search(r'\.([A-Za-z0-9_]+)$', str(plc_path))
    if match:
        suffix = f".{match.group(1).upper()}"
        return PLC_SUFFIX_TO_TND.get(suffix)
    
    return None


def classify_writefloat_setpoint(plc_path, description):
    """
    Classify WRITEFLOAT addresses based on description keywords.
    Detects Lead/Lag Start/Stop Setpoints.
    
    Args:
        plc_path: PLC address string
        description: Description text
    
    Returns:
        str or None: Specific setpoint TND or None
    """
    if not plc_path:
        return None
    
    plc_upper = str(plc_path).upper()
    
    # Only process WRITEFLOAT addresses
    if not plc_upper.startswith('WRITEFLOAT['):
        return None
    
    desc_upper = str(description).upper() if description else ""
    
    # Check for Lead/Lag patterns with Start/Stop
    # Priority: most specific first
    
    # Lag with number (Lag1, Lag2, Lag3)
    if re.search(r'LAG\s*1', desc_upper):
        if 'START' in desc_upper:
            return "Lag1 Start Setpoint"
        if 'STOP' in desc_upper:
            return "Lag1 Stop Setpoint"
    
    if re.search(r'LAG\s*2', desc_upper):
        if 'START' in desc_upper:
            return "Lag2 Start Setpoint"
        if 'STOP' in desc_upper:
            return "Lag2 Stop Setpoint"
    
    if re.search(r'LAG\s*3', desc_upper):
        if 'START' in desc_upper:
            return "Lag3 Start Setpoint"
        if 'STOP' in desc_upper:
            return "Lag3 Stop Setpoint"
    
    # Lead patterns
    if 'LEAD' in desc_upper:
        if 'START' in desc_upper:
            return "Lead Start Setpoint"
        if 'STOP' in desc_upper:
            return "Lead Stop Setpoint"
    
    # Generic Lag (without number)
    if 'LAG' in desc_upper:
        if 'START' in desc_upper:
            return "Lag Start Setpoint"
        if 'STOP' in desc_upper:
            return "Lag Stop Setpoint"
    
    # Start/Stop without Lead/Lag
    if 'START' in desc_upper and 'SETPOINT' in desc_upper:
        return "Start Setpoint"
    if 'STOP' in desc_upper and 'SETPOINT' in desc_upper:
        return "Stop Setpoint"
    
    # Check for alarm setpoint patterns
    if 'HIGH' in desc_upper and 'HIGH' in desc_upper[desc_upper.find('HIGH')+4:]:
        # HIGH HIGH
        if 'SETPOINT' in desc_upper or 'SET POINT' in desc_upper:
            return "High High Alarm Setpoint"
    if 'LOW' in desc_upper and 'LOW' in desc_upper[desc_upper.find('LOW')+3:]:
        # LOW LOW
        if 'SETPOINT' in desc_upper or 'SET POINT' in desc_upper:
            return "Low Low Alarm Setpoint"
    if 'HIGH' in desc_upper:
        if 'SETPOINT' in desc_upper or 'SET POINT' in desc_upper:
            return "High Alarm Setpoint"
    if 'LOW' in desc_upper:
        if 'SETPOINT' in desc_upper or 'SET POINT' in desc_upper:
            return "Low Alarm Setpoint"
    
    # Default for WRITEFLOAT: generic Setpoint
    return "Setpoint"


def detect_flow_rate(description):
    """
    Detect if description contains "Flow Rate" pattern.
    
    Args:
        description: Description text
    
    Returns:
        bool: True if Flow Rate detected
    """
    if not description:
        return False
    
    desc_upper = str(description).upper()
    
    # Check for "FLOW RATE" as a phrase
    if 'FLOW RATE' in desc_upper:
        return True
    
    # Check for "FLOWRATE" without space
    if 'FLOWRATE' in desc_upper:
        return True
    
    return False


def get_default_states(tnd, target_id=None):
    """
    Get default states based on TND.
    
    Args:
        tnd: Target name description
        target_id: Optional tag identifier for context
    
    Returns:
        str: Default states string or empty string
    """
    if tnd in DEFAULT_STATES:
        return DEFAULT_STATES[tnd]
    
    # Special case: Input states based on switch type
    if tnd == "Input" and target_id:
        tag_upper = str(target_id).upper()
        # High level switches (LSH, LSHH, PSH, etc.)
        if re.match(r'^[PLTFAV]X?S(HH|H)[-_]', tag_upper):
            return "1=Ok;0=High Level"
        # Low level switches (LSL, LSLL, PSL, etc.)
        elif re.match(r'^[PLTFAV]X?S(LL|L)[-_]', tag_upper):
            return "1=Ok;0=Low Level"
    
    return ""


def get_default_scaling(tnd):
    """
    Get default scaling based on TND.
    
    Args:
        tnd: Target name description
    
    Returns:
        str: Default scaling string or empty string
    """
    return DEFAULT_SCALING.get(tnd, "")


# =============================================================================
# ORIGINAL FUNCTIONS (preserved from original step3)
# =============================================================================

def identify_tag_type(description):
    """Identify tag type from description keywords"""
    if not description or not isinstance(description, str):
        return "Unclassified"
    
    desc_upper = description.upper()
    
    for tag_type, keywords in CLASSIFICATION_KEYWORDS.items():
        if any(kw in desc_upper for kw in keywords):
            return tag_type.replace('_', ' ').title()
    
    return "Unclassified"


def extract_tag_id_from_description(description):
    """Extract tag ID from description"""
    if not description or not isinstance(description, str):
        return None, ""
    
    match = re.match(r'^([A-Z]{2,6}[-_]\d+[A-Z]?)', description)
    if match:
        tag_id = match.group(1)
        equipment = description[len(tag_id):].strip()
        equipment = re.sub(r'^[-_:\s]+', '', equipment)
        return tag_id, equipment
    
    return None, description


def classify_by_pattern(original_tag, description):
    """Classify IO by ISA pattern matching"""
    if not description or not isinstance(description, str):
        description = ""
    
    desc_upper = description.upper()
    tag_upper = original_tag.upper()
    
    all_patterns = {}
    all_patterns.update(ALARM_PATTERNS)
    all_patterns.update(SWITCH_PATTERNS)
    
    sorted_patterns = sorted(all_patterns.items(), key=lambda x: len(x[0]), reverse=True)
    
    for pattern_name, pattern_info in sorted_patterns:
        if pattern_name in desc_upper or pattern_name in tag_upper:
            return {
                'pattern': pattern_name,
                'type': pattern_info['type'],
                'description': pattern_info['description'],
                'order': pattern_info['order'],
            }
    
    for pattern, meas_type in TRANSMITTER_PATTERNS.items():
        if pattern in desc_upper or pattern in tag_upper:
            return {
                'pattern': pattern,
                'type': meas_type,
                'description': 'Process Value',
                'order': 0,
            }
    
    for pattern, ctrl_type in CONTROLLER_PATTERNS.items():
        if pattern in desc_upper or pattern in tag_upper:
            return {
                'pattern': pattern,
                'type': ctrl_type,
                'description': 'Control Signal',
                'order': 0,
            }
    
    for pattern, valve_type in VALVE_PATTERNS.items():
        if pattern in desc_upper or pattern in tag_upper:
            return {
                'pattern': pattern,
                'type': valve_type,
                'description': 'Control Valve',
                'order': 0,
            }
    
    return None


def validate_target_name(target_name):
    """Validate target_name against approved list"""
    if not target_name:
        return "UNCLASSIFIED"
    
    for valid_name in VALID_TARGET_NAMES_MERGED:
        if target_name.upper() == valid_name.upper():
            return valid_name
    
    return "UNCLASSIFIED"


def detect_day_volume(address, description):
    """Detect DAY0 or DAY1 volume patterns."""
    address_upper = str(address).upper()
    desc_str = str(description) if description else ""
    desc_upper = desc_str.upper()
    
    if 'YESTERDAY' in desc_upper:
        return 'Day 1 Volume'
    
    if 'TODAY' in desc_upper:
        return 'Day 0 Volume'
    
    day0_pattern = re.compile(r'DAY\s*[_$-]?\s*0|DAY0', re.IGNORECASE)
    day1_pattern = re.compile(r'DAY\s*[_$-]?\s*1|DAY1', re.IGNORECASE)
    
    if 'FLOW' in address_upper:
        if 'DAY0' in address_upper or '.DAY0' in address_upper:
            return 'Day 0 Volume'
        if 'DAY1' in address_upper or '.DAY1' in address_upper:
            return 'Day 1 Volume'
    
    if day0_pattern.search(desc_str):
        return 'Day 0 Volume'
    if day1_pattern.search(desc_str):
        return 'Day 1 Volume'
    
    return None


def extract_volume_unit_from_description(description):
    """Extract engineering unit from description."""
    if not description or not isinstance(description, str):
        return None
    
    desc = str(description)
    
    known_units_pattern = re.compile(
        r'\((PSIG|PSIA|PSI|MCFD|MCF|BPD|BBLS|GPM|Vdc|VDC|VAC|mA|MA|Deg\s*[FC]|Inches|IN|%|Hz)\)\s*$',
        re.IGNORECASE
    )
    match = known_units_pattern.search(desc)
    if match:
        return match.group(1).lower()
    
    pattern2 = re.compile(r'\([^,]+,\s*([A-Za-z%]+)\)\s*$')
    match = pattern2.search(desc)
    if match:
        return match.group(1).lower()
    
    pattern3 = re.compile(r'(Deg\s*[FC])\.?\s*$', re.IGNORECASE)
    match = pattern3.search(desc)
    if match:
        return match.group(1).lower()
    
    if re.search(r'\d+-\d+%|\b\d+%', desc):
        return "%"
    
    volume_pattern = re.compile(r'\b(MSCFD|MCFD|MSCF|MCF|BPD|BBLS|GPM)\b', re.IGNORECASE)
    match = volume_pattern.search(desc)
    if match:
        return match.group(1).lower()
    
    pressure_pattern = re.compile(r'\b(PSIG|PSIA|PSI|BARG|BARA)\b', re.IGNORECASE)
    match = pressure_pattern.search(desc)
    if match:
        return match.group(1).lower()
    
    return None


def normalize_unit_lowercase(unit):
    """Normalize engineering units to lowercase."""
    if not unit:
        return ''
    
    unit = str(unit).strip()
    
    keep_uppercase = ['DEGF', 'DEGC']
    if unit.upper() in keep_uppercase:
        return unit.upper()
    
    special_cases = {
        '"': 'in', '" WC': 'in wc', '"WC': 'in wc', 'IN WC': 'in wc',
        'IN': 'in', 'PSI': 'psi', 'PSIG': 'psig', 'PSIA': 'psia',
        'GPM': 'gpm', 'BPD': 'bpd', 'MCF': 'mcf', 'MCFD': 'mcfd',
        'MSCF': 'mscf', 'MSCFD': 'mscfd', 'ACFM': 'acfm',
        'HZ': 'hz', 'MA': 'mA', 'M/A': '', '%': '%', 'BBLS': 'bbls',
        'AMPS': 'amps', 'FT': 'ft', 'SEC': 'sec', 'MIN': 'min', 'HR': 'hr',
    }
    
    upper_unit = unit.upper()
    if upper_unit in special_cases:
        return special_cases[upper_unit]
    
    return unit.lower()


def extract_transmitter_id(description):
    """Extract transmitter tag ID from description"""
    if not description or not isinstance(description, str):
        return None
    
    desc_upper = description.upper()
    
    for prefix in TRANSMITTER_PREFIXES:
        patterns = [
            rf'\b({prefix})[-_\s]?(\d+[A-Z]?)\b',
            rf'\b({prefix})(\d+[A-Z]?)\b',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, desc_upper)
            if match:
                prefix_part = match.group(1)
                number_part = match.group(2)
                return f"{prefix_part}-{number_part}"
    
    return None


def extract_alarm_switch_tag(description):
    """Extract alarm/switch tag from description."""
    if not description or not isinstance(description, str):
        return None, description
    
    alarm_tag_pattern = re.compile(
        r'^([DPLTFA][DPXIA]?(?:SHH|SH|SLL|SL|AHH|AH|ALL|AL))[-_]?([A-Z]?[-_]?\d+[A-Z]?(?:[-_][A-Z0-9]+)?)\s*',
        re.IGNORECASE
    )
    
    match = alarm_tag_pattern.match(description)
    if match:
        prefix = match.group(1).upper()
        number = match.group(2).upper().replace('_', '-')
        tag_id = f"{prefix}-{number}".replace('--', '-')
        remaining = description[match.end():].strip()
        return tag_id, remaining
    
    return None, description


def is_alarm_address(address):
    """Check if address is an ALARM type (ALARM[...])"""
    if not address:
        return False
    return bool(re.match(r'^ALARM\[\d+\]', str(address), re.IGNORECASE))


def detect_setpoint_type(description):
    """Detect specific setpoint type from description."""
    if not description or not isinstance(description, str):
        return None
    
    desc_upper = description.upper()
    
    if 'SETPOINT' not in desc_upper:
        return None
    
    setpoint_patterns = [
        (r'HIGH\s*HIGH\s*(?:ALARM\s*)?SETPOINT', 'High High Alarm Setpoint'),
        (r'(?:ALARM\s*)?HIGH\s*HIGH\s*SETPOINT', 'High High Alarm Setpoint'),
        (r'LOW\s*LOW\s*(?:ALARM\s*)?SETPOINT', 'Low Low Alarm Setpoint'),
        (r'(?:ALARM\s*)?LOW\s*LOW\s*SETPOINT', 'Low Low Alarm Setpoint'),
        (r'HIGH\s*(?:ALARM\s*)?SETPOINT', 'High Alarm Setpoint'),
        (r'(?:ALARM\s*)?HIGH\s*SETPOINT', 'High Alarm Setpoint'),
        (r'LOW\s*(?:ALARM\s*)?SETPOINT', 'Low Alarm Setpoint'),
        (r'(?:ALARM\s*)?LOW\s*SETPOINT', 'Low Alarm Setpoint'),
    ]
    
    for pattern, setpoint_type in sorted(setpoint_patterns, key=lambda x: len(x[0]), reverse=True):
        if re.search(pattern, desc_upper):
            return setpoint_type
    
    return 'Setpoint'


def is_writefloat_address(address):
    """Check if address is a WRITEFLOAT type"""
    if not address:
        return False
    return bool(re.match(r'^WRITEFLOAT\[\d+\]', str(address), re.IGNORECASE))


def convert_alarm_tag_to_transmitter(tag_id):
    """Convert alarm tag to transmitter tag."""
    if not tag_id:
        return tag_id, None, False
    
    switch_pattern = re.compile(r'^([PLTFAVD])([XI]?)S(HH|H|LL|L)-(.+)$', re.IGNORECASE)
    match = switch_pattern.match(str(tag_id))
    if match:
        alarm_level = match.group(3).upper()
        return tag_id, alarm_level, True
    
    alarm_pattern = re.compile(r'^([PLTFAVD])([XI]?)A(HH|H|LL|L)-(.+)$', re.IGNORECASE)
    match = alarm_pattern.match(str(tag_id))
    if not match:
        return tag_id, None, False
    
    meas_type = match.group(1).upper()
    modifier = match.group(2).upper() if match.group(2) else ''
    alarm_level = match.group(3).upper()
    number = match.group(4).upper()
    
    ALARM_TO_TRANSMITTER = {
        'P': 'PIT', 'T': 'TIT', 'L': 'LIT', 'F': 'FIT',
        'A': 'AIT', 'D': 'DIT', 'V': 'VIT',
    }
    
    base_prefix = ALARM_TO_TRANSMITTER.get(meas_type, f'{meas_type}IT')
    
    if modifier:
        transmitter_prefix = base_prefix[0] + modifier + base_prefix[1:]
    else:
        transmitter_prefix = base_prefix
    
    return f"{transmitter_prefix}-{number}", alarm_level, False


def get_alarm_tnd_from_level(alarm_level, has_setpoint, is_switch=False, plc_address=None):
    """Get target_name_description from alarm level."""
    if is_switch:
        if plc_address and re.match(r'^ALARM\[\d+\]', str(plc_address), re.IGNORECASE):
            return "Alarm"
        else:
            return "Input"
    else:
        level_to_tnd = {
            'HH': 'High High Alarm',
            'H': 'High Alarm',
            'L': 'Low Alarm',
            'LL': 'Low Low Alarm',
        }
        
        base_tnd = level_to_tnd.get(alarm_level, 'High Alarm')
        
        if has_setpoint:
            return f"{base_tnd} Setpoint"
        return base_tnd


def detect_hoa_pattern(description):
    """Detect Hand/Off/Auto (HOA) pattern in description."""
    if not description:
        return False
    
    desc_upper = str(description).upper()
    
    if re.search(r'\bHOA\b', desc_upper):
        return True
    if 'HAND' in desc_upper and 'OFF' in desc_upper and 'AUTO' in desc_upper:
        return True
    if re.search(r'HAND[/\-]OFF[/\-]AUTO', desc_upper):
        return True
    if re.search(r'\bH[/\-]O[/\-]A\b', desc_upper):
        return True
    
    return False


def detect_permissive_pattern(description):
    """Detect Permissive pattern in description."""
    if not description:
        return False
    
    desc_upper = str(description).upper()
    
    if 'PERMISSIVE' in desc_upper:
        return True
    
    return False


def classify_from_tag_id(tag_id, plc_address):
    """Classify TND based on tag_id when description is empty."""
    if not tag_id:
        return None, False
    
    tag_upper = str(tag_id).upper()
    
    switch_pattern = re.compile(r'^([PLTFAVD])([XI]?)S(HH|H|LL|L)?[-_]', re.IGNORECASE)
    if switch_pattern.match(tag_upper):
        is_switch = True
        if plc_address and re.match(r'^ALARM\[\d+\]', str(plc_address), re.IGNORECASE):
            return "Alarm", is_switch
        else:
            return "Input", is_switch
    
    transmitter_pattern = re.compile(r'^([PLTFAVD])([XI]?)IT[-_]', re.IGNORECASE)
    if transmitter_pattern.match(tag_upper):
        return "Process Value", False
    
    alarm_pattern = re.compile(r'^([PLTFAVD])([XI]?)A(HH|H|LL|L)[-_]', re.IGNORECASE)
    match = alarm_pattern.match(tag_upper)
    if match:
        level = match.group(3).upper()
        level_to_tnd = {
            'HH': 'High High Alarm', 'H': 'High Alarm',
            'L': 'Low Alarm', 'LL': 'Low Low Alarm',
        }
        return level_to_tnd.get(level, 'Alarm'), False
    
    controller_pattern = re.compile(r'^([PLTFAVD])([XI]?)IC[-_]', re.IGNORECASE)
    if controller_pattern.match(tag_upper):
        return "Control Signal", False
    
    valve_pattern = re.compile(r'^([PLTFAVD])?[XY]V?[-_]|^[PLTF]CV[-_]', re.IGNORECASE)
    if valve_pattern.match(tag_upper):
        return "Control Valve", False
    
    return None, False


def extract_alarm_level_from_description(description):
    """Extract alarm level from description when tag is at the end."""
    if not description:
        return None, False
    
    pattern = re.compile(
        r'([PLTFAVD])([XI]?)(S)?A?(HH|H|LL|L)-[A-Z]?\d+[A-Z]?(?:[-_]\d+)?\s*$',
        re.IGNORECASE
    )
    
    match = pattern.search(description)
    if match:
        is_switch = match.group(3) is not None
        alarm_level = match.group(4).upper()
        return alarm_level, is_switch
    
    return None, False


def extract_alarm_level_from_keywords(description):
    """Extract alarm level from keywords in description."""
    if not description:
        return None, False
    
    desc_upper = str(description).upper()
    
    is_switch = bool(re.search(r'\bSW\b|\bSWITCH\b|\bSWTICH\b', desc_upper))
    
    if 'HIGH HIGH' in desc_upper or 'HI HI' in desc_upper:
        return 'HH', is_switch
    elif 'LOW LOW' in desc_upper or 'LO LO' in desc_upper:
        return 'LL', is_switch
    elif re.search(r'\bHIGH\b', desc_upper) and 'HIGH HIGH' not in desc_upper:
        return 'H', is_switch
    elif re.search(r'\bLOW\b', desc_upper) and 'LOW LOW' not in desc_upper:
        return 'L', is_switch
    
    return None, is_switch


def clean_alarm_description(description, alarm_level, has_setpoint):
    """Clean description by removing Alarm, Setpoint."""
    if not description:
        return description
    
    if not alarm_level:
        return description
    
    cleaned = description
    
    patterns_to_remove = [
        r'\s+Alarm\s+Set\s*Point\s*$',
        r'\s+Alarm\s+Setpoint\s*$',
        r'\s+Set\s*Point\s*$',
        r'\s+Setpoint\s*$',
        r'\s+Alarm\s*$',
    ]
    
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()


def extract_setpoint_tag_from_description(description):
    """Extract transmitter tag from setpoint description."""
    if not description or not isinstance(description, str):
        return None
    
    if 'SETPOINT' not in description.upper():
        return None
    
    return extract_tag_from_alarm_description(description)


def extract_tag_from_alarm_description(description):
    """Extract tag from alarm/setpoint description."""
    if not description or not isinstance(description, str):
        return None
    
    ALARM_TO_TRANSMITTER = {
        'P': 'PIT', 'T': 'TIT', 'L': 'LIT', 'F': 'FIT',
        'A': 'AIT', 'D': 'DIT', 'V': 'VIT',
    }
    
    pattern1 = re.compile(
        r'^([PLTFAVD])IT[-_]([A-Z]?\d+(?:[-_]\d+)?)[-_](?:[PLTFAVD][XI]?(?:A|S)?(?:HH|H|LL|L))\s',
        re.IGNORECASE
    )
    match = pattern1.match(description)
    if match:
        meas_type = match.group(1).upper()
        number = match.group(2).upper().replace('_', '-')
        prefix = ALARM_TO_TRANSMITTER.get(meas_type, f'{meas_type}IT')
        return f"{prefix}-{number}"
    
    pattern2 = re.compile(
        r'([PLTFAVD])([XI]?)(S)?([AO])?(HH|H|LL|L)-([A-Z]?\d+[A-Z]?(?:[-_]\d+)?)\s*$',
        re.IGNORECASE
    )
    match = pattern2.search(description)
    if match:
        meas_type = match.group(1).upper()
        modifier = match.group(2).upper() if match.group(2) else ''
        is_switch = match.group(3) is not None
        alarm_level = match.group(5).upper()
        number = match.group(6).upper()
        
        if is_switch:
            if modifier:
                prefix = f"{meas_type}{modifier}S{alarm_level}"
            else:
                prefix = f"{meas_type}S{alarm_level}"
        else:
            base_prefix = ALARM_TO_TRANSMITTER.get(meas_type, f'{meas_type}IT')
            if modifier == 'X':
                prefix = base_prefix[0] + 'X' + base_prefix[1:]
            else:
                prefix = base_prefix
        
        return f"{prefix}-{number}"
    
    pattern3 = re.compile(
        r'\(([PLTFAVD])([XI]?)(S)?([AO])?(HH|H|LL|L)-([A-Z]?\d+[A-Z]?(?:[-_][A-Z]?\d+)?)-?(?:[Ss]etpoint|[Ss][Pp]|[Ss]et[- ][Pp]oint)',
        re.IGNORECASE
    )
    match = pattern3.search(description)
    if match:
        meas_type = match.group(1).upper()
        modifier = match.group(2).upper() if match.group(2) else ''
        is_switch = match.group(3) is not None
        alarm_level = match.group(5).upper()
        number = match.group(6).upper()
        
        if is_switch:
            if modifier:
                prefix = f"{meas_type}{modifier}S{alarm_level}"
            else:
                prefix = f"{meas_type}S{alarm_level}"
        else:
            base_prefix = ALARM_TO_TRANSMITTER.get(meas_type, f'{meas_type}IT')
            if modifier == 'X':
                prefix = base_prefix[0] + 'X' + base_prefix[1:]
            else:
                prefix = base_prefix
        
        return f"{prefix}-{number}"
    
    pattern4 = re.compile(
        r'\(([PLTFAVD])([XI]?)(S)?([AO])?(HH|H|LL|L)-([A-Z]?\d+[A-Z]?(?:[-_]\d+)?)\)',
        re.IGNORECASE
    )
    match = pattern4.search(description)
    if match:
        meas_type = match.group(1).upper()
        modifier = match.group(2).upper() if match.group(2) else ''
        is_switch = match.group(3) is not None
        alarm_level = match.group(5).upper()
        number = match.group(6).upper()
        
        if is_switch:
            if modifier:
                prefix = f"{meas_type}{modifier}S{alarm_level}"
            else:
                prefix = f"{meas_type}S{alarm_level}"
        else:
            base_prefix = ALARM_TO_TRANSMITTER.get(meas_type, f'{meas_type}IT')
            if modifier == 'X':
                prefix = base_prefix[0] + 'X' + base_prefix[1:]
            else:
                prefix = base_prefix
        
        return f"{prefix}-{number}"
    
    return None


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

