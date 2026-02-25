# #!/usr/bin/env python3
# """
# Step 3: Convert enriched IOs to Master Tag List (MTL) format.
# """

# import os
# import sys

# from config import ENRICHED_PATH, FINAL_MTL_PATH, OUTPUT_DIR


# def main():
#     print("=" * 70)
#     print("STEP 3: CONVERT TO MASTER TAG LIST")
#     print("=" * 70)

#     if not os.path.exists(ENRICHED_PATH):
#         print(f"\nERROR: {ENRICHED_PATH} not found. Run step2 first.")
#         sys.exit(1)

#     os.makedirs(OUTPUT_DIR, exist_ok=True)

#     from converters.mtl_builder import convert_to_mtl
#     convert_to_mtl(ENRICHED_PATH, FINAL_MTL_PATH)

#     print("\n" + "=" * 70)
#     print("STEP 3 COMPLETE!")
#     print("=" * 70)
#     print(f"\n  Output: {FINAL_MTL_PATH}")


# if __name__ == '__main__':
#     main()


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3: Convert to Master Tag List - ENHANCED VERSION
Incorporates comprehensive classification rules from the L5K Parser to MTL suite.

New rules integrated:
- prefix_handler.py: transmitter prefix normalization (PT->PIT, LI->LIT, etc.),
  valve target_id resolution (LY->LV, ZSO->XV), switch detection by S count,
  motor prefix inference from descriptions, combined pump target_id generation
- equipment_classifier.py: unified valve/motor/switch classification priority,
  analog input metadata (Rate vs Process Value for flow meters), VFD fault detection
- alarm_severity.py: severity code detection from tag names and descriptions
  (IV-appended patterns, UDT patterns, free-text keywords)
- description_formatter.py: proper case with preserved caps (ESD, PLC, VFD...),
  scaling range stripping, ISA measurement type enhancement, motor/valve word stripping
- alarm_processor.py: alarm tag to transmitter conversion with switch awareness,
  setpoint type detection, alarm delay detection
"""

import re
import os
import pandas as pd
from collections import defaultdict
from config import *
from patterns import *


# =============================================================================
# TEXT PROCESSING (from description_formatter.py)
# =============================================================================

def to_proper_case(text):
    """Convert text to proper case, preserving words with digits and specific acronyms."""
    if not text or not isinstance(text, str):
        return text or ""

    ORDINAL_RE = re.compile(r'^(1|2|3|4|5)(ST|ND|RD|TH)$', re.IGNORECASE)

    def smart_cap(word):
        word_stripped = word.strip('()[]{}.,;:!?').upper()
        if word_stripped in PRESERVE_CAPS_WORDS:
            return word.upper()
        m = ORDINAL_RE.match(word)
        if m:
            return m.group(1) + m.group(2).lower()
        if any(ch.isdigit() for ch in word):
            return word
        letter_start = 0
        for i, ch in enumerate(word):
            if ch.isalpha():
                letter_start = i
                break
        else:
            return word
        return word[:letter_start] + word[letter_start].upper() + word[letter_start+1:].lower()

    return ' '.join(
        '-'.join(smart_cap(part) for part in token.split('-'))
        for token in text.strip().split()
    )


def expand_abbreviations(text):
    """Expand common abbreviations."""
    if not text or not isinstance(text, str):
        return text
    if not EXPAND_ABBREVIATIONS:
        return text
    result = text
    for abbrev_pattern, full_form in ABBREVIATIONS.items():
        result = re.sub(abbrev_pattern, full_form, result, flags=re.IGNORECASE)
    return result


def capitalize_proper(text):
    """Apply proper capitalization with abbreviation expansion."""
    if not text or not isinstance(text, str):
        return text
    if not APPLY_CAPITALIZATION:
        return text
    text = expand_abbreviations(text)
    result = to_proper_case(text)
    if PRESERVE_ACRONYMS:
        for acronym in PRESERVED_ACRONYMS:
            pattern = r'\b' + re.escape(acronym.title()) + r'\b'
            result = re.sub(pattern, acronym, result, flags=re.IGNORECASE)
    return result


def strip_scaling_range(description):
    """Remove scaling range patterns, units, and 'Transmitter' from description."""
    if not description:
        return description
    cleaned = re.sub(r'\s*\(\s*-?\d+(?:\.\d+)?\s*[-\u2013]\s*-?\d+(?:\.\d+)?\s*[A-Za-z%]*\s*\)', '', description)
    cleaned = re.sub(r'\s*\(\s*(?:psig|ma|gpm|bpd|ips|degf|psid|%)\s*\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*-?\d+(?:\.\d+)?\s+(?:to|TO|To)\s+-?\d+(?:\.\d+)?(?:.*)?$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bdegrees(?:\s+celsius)?\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(?:psig|ma|gpm|bpd|ips|degf|psid)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\bTransmitter\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+%(?:\s|$)', ' ', cleaned)
    cleaned = re.sub(r'\(\s*\)', '', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned.strip()


def strip_motor_status_words(description):
    """Remove motor-specific tag prefixes and status trigger words from description."""
    if not description:
        return description
    desc = description.strip()
    # Remove motor tag prefixes like HS-101, XS-202
    desc = re.sub(r'^[HX][ISC][-_]\s+', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'^[HX][ISC]\s*[-_]\s+', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'^[HX][ISC][-_]?[A-Z]?\d+[A-Z]?\s+', '', desc, flags=re.IGNORECASE)
    # Remove common motor phrases
    phrases = [
        "Hand Switch In Auto", "Hand Switch In", "Hand Switch", "Status Switch",
        "Run Status Relay", "Run Status", "Auto Status", "Running Indication",
        "Run Indication", "Start Command", "Run Command", "Output Command",
    ]
    for phrase in phrases:
        desc = re.sub(rf'\b{re.escape(phrase)}\b', '', desc, flags=re.IGNORECASE)
    # Remove trigger words
    all_triggers = (AUTO_STATUS_TRIGGERS or []) + (RUN_STATUS_TRIGGERS or []) + (RUN_COMMAND_TRIGGERS or [])
    for trigger in all_triggers:
        if trigger:
            desc = re.sub(rf'\b{re.escape(trigger)}\b', '', desc, flags=re.IGNORECASE)
    # Remove residual motor words
    for word in ["motor", "status", "relay", "indication", "switch", "command", "run"]:
        desc = re.sub(rf'\b{re.escape(word)}\b', '', desc, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', desc).strip()


def strip_valve_status_words(description):
    """Remove valve-specific tag prefixes and status words from description."""
    if not description:
        return description
    desc = description.strip()
    desc = re.sub(r'^Z[ISO][OC][-_]?\d+\s*', '', desc, flags=re.IGNORECASE)
    for phrase in ["Open Status Limit Switch", "Closed Status Limit Switch",
                    "Open Status", "Closed Status", "Limit Switch", "Status Switch"]:
        desc = re.sub(rf'\b{re.escape(phrase)}\b', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\bStatus\b', '', desc, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', desc).strip()


def strip_alarm_suffix_from_description(description):
    """Remove alarm type suffixes from equipment description."""
    if not description:
        return ""
    cleaned = description.replace("$N", " ").replace("$n", " ")
    alarm_match = re.search(r'\s*\bALARM\b.*$', cleaned, re.IGNORECASE)
    if alarm_match:
        cleaned = cleaned[:alarm_match.start()]
    cleaned = re.sub(r'^[TPLF]A?(?:HH?|LL?)?[-_]?[A-Z0-9]+[A-Z]?\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^PDA?(?:HH?|LL?)?[-_]?[A-Z0-9]+[A-Z]?\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*\bTransmitter\b', '', cleaned, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', cleaned).strip()


# =============================================================================
# TARGET ID NORMALIZATION (from prefix_handler.py)
# =============================================================================

def normalize_target_id(s):
    """Normalize target ID: uppercase, underscores to dashes, add dash between prefix/number."""
    if not s:
        return s
    normalized = s.replace("_", "-").upper().strip()
    if "-" in normalized:
        return normalized
    match = re.match(r'^([A-Z]+)(\d+[A-Z]*)$', normalized)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return normalized


def normalize_transmitter_prefix(target_id):
    """Normalize transmitter prefixes: PT->PIT, LI->LIT, etc."""
    if not target_id:
        return target_id
    parts = target_id.split('-', 1)
    if len(parts) != 2:
        return target_id
    prefix, suffix = parts
    prefix_upper = prefix.upper()
    if prefix_upper in TWO_LETTER_TRANSMITTER_PREFIXES:
        return f"{TWO_LETTER_TRANSMITTER_PREFIXES[prefix_upper]}-{suffix}"
    return target_id


def resolve_valve_target_id(tag_id):
    """Normalize valve target_id: Y->V conversion, ZSO/ZSC->XV."""
    if not tag_id:
        return ""
    parts = tag_id.split('-', 1) if '-' in tag_id else tag_id.split('_', 1)
    if len(parts) != 2:
        return tag_id
    prefix, suffix = parts
    prefix_upper = prefix.upper()
    if prefix_upper in VALVE_SWITCH_TO_XV:
        return f"XV-{suffix}"
    if prefix_upper in VALVE_Y_TO_V:
        return f"{VALVE_Y_TO_V[prefix_upper]}-{suffix}"
    if 'Y' in prefix_upper and prefix_upper not in ('LXY',):
        return f"{prefix_upper.replace('Y', 'V')}-{suffix}"
    return tag_id


def is_switch_tag(target_id):
    """Determine if a target_id represents a switch (S after initiating variable)."""
    if not target_id:
        return False
    pre = target_id.split('-')[0] if '-' in target_id else target_id
    pre_upper = pre.upper()
    switch_pattern = re.compile(r'^([PLTFAVD])([XI]?)S(HH|H|LL|L)?$', re.IGNORECASE)
    if switch_pattern.match(pre_upper):
        return True
    if re.match(r'^PDS(HH|H|LL|L)?$', pre_upper, re.IGNORECASE):
        return True
    return False


def is_valve_position_switch(target_id):
    """Check if target_id is a valve position switch (ZSO, ZSC, ZIO, ZIC, XSO, XSC)."""
    if not target_id:
        return False
    return bool(re.match(r'^[ZX][SI][OC][-_]', target_id.upper()))


def is_valve_tag(target_id, description=""):
    """Check if target_id represents a valve."""
    if not target_id:
        return False
    prefix = target_id.split('-')[0].upper() if '-' in target_id else target_id.split('_')[0].upper()
    if prefix in VALVE_PATTERNS or prefix in VALVE_SWITCH_PATTERNS:
        return True
    if prefix in VALVE_SWITCH_TO_XV:
        return True
    if prefix.endswith('V') and len(prefix) <= 4 and prefix not in ('PV',):
        return True
    if description and re.search(r'\b[ZX][IS][OC][-_]?\d+', description.upper()):
        return True
    return False


def has_motor_equipment_word(text):
    """Check if text contains pump/fan/compressor/motor/blower."""
    if not text:
        return False
    text_upper = text.upper()
    for word in MOTOR_EQUIPMENT_WORDS:
        pattern = rf'(?<![A-Z]){word}S?(?![A-Z])'
        if re.search(pattern, text_upper):
            return True
    return False


def has_motor_trigger_word(tag_name, description):
    """Check if tag name or description has motor trigger words."""
    tag_upper = (tag_name or "").upper()
    desc_upper = (description or "").upper()
    all_triggers = (RUN_COMMAND_TRIGGERS or []) + (RUN_STATUS_TRIGGERS or []) + (AUTO_STATUS_TRIGGERS or [])
    for trigger in all_triggers:
        t = trigger.upper()
        if t in tag_upper or t in desc_upper:
            return True
    return False


def is_motor_io(tag_name, description, target_id):
    """Detect if a tag represents motor I/O."""
    if target_id:
        prefix = target_id.split('-')[0] if '-' in target_id else target_id.split('_')[0]
        if prefix.upper() in MOTOR_KEYWORD_TO_PREFIX.values():
            return True
    return has_motor_equipment_word(description) and has_motor_trigger_word(tag_name, description)


def is_vfd_fault(tag_name, description=""):
    """Check if tag represents a VFD/VSD fault."""
    combined = f"{tag_name} {description}".upper()
    return any(v in combined for v in ['VFD', 'VSD']) and any(f in combined for f in ['FAULT', 'FAIL'])


# =============================================================================
# SEVERITY DETECTION (from alarm_severity.py)
# =============================================================================

def detect_severity_code(text):
    """Detect alarm severity code (HH, H, L, LL) from text."""
    if not text:
        return None
    t_raw = text.upper()
    t = re.sub(r"[_\-\./]", " ", t_raw)
    # IV-appended patterns
    iv_tokens = list(INSTRUMENT_INITIATING_VARIABLES.keys())
    all_pat = "|".join(sorted(map(re.escape, iv_tokens), key=len, reverse=True))
    if re.search(rf"\b(?:{all_pat})[-_]A?HH", t_raw): return "HH"
    if re.search(rf"\b(?:{all_pat})[-_]A?LL", t_raw): return "LL"
    if re.search(rf"\b(?:{all_pat})[-_]A?H(?!H)", t_raw): return "H"
    if re.search(rf"\b(?:{all_pat})[-_]A?L(?!L)", t_raw): return "L"
    # Single-char IV + A + level
    for iv in iv_tokens:
        if len(iv) == 1:
            if re.search(rf"\b{iv}AHH", t_raw): return "HH"
            if re.search(rf"\b{iv}ALL", t_raw): return "LL"
            if re.search(rf"\b{iv}AH(?!H)", t_raw): return "H"
            if re.search(rf"\b{iv}AL(?!L)", t_raw): return "L"
    # UDT patterns
    if re.search(r'\bHHSetpoint\b', t_raw, re.IGNORECASE): return "HH"
    if re.search(r'\bLLSetpoint\b', t_raw, re.IGNORECASE): return "LL"
    if re.search(r'\bHSetpoint\b', t_raw, re.IGNORECASE): return "H"
    if re.search(r'\bLSetpoint\b', t_raw, re.IGNORECASE): return "L"
    # Alarm prefix patterns
    if re.search(r"\bALARM[-_](?:HIGH[-_]HIGH|HIHI|HI[-_]HI)", t_raw): return "HH"
    if re.search(r"\bALARM[-_](?:LOW[-_]LOW|LOLO|LO[-_]LO)", t_raw): return "LL"
    if re.search(r"\bALARM[-_]?A?HH", t_raw): return "HH"
    if re.search(r"\bALARM[-_]?A?LL", t_raw): return "LL"
    if re.search(r"\bALARM[-_]?A?H(?!H|IGH)", t_raw): return "H"
    if re.search(r"\bALARM[-_]?A?L(?!L|OW)", t_raw): return "L"
    # Free-text tokens
    if re.search(r"(HI\s*HI|HIGH\s*HIGH|HIHI|HH\b)", t): return "HH"
    if re.search(r"(LO\s*LO|LOW\s*LOW|LOLO|\bLL\b)", t): return "LL"
    if re.search(r"\b(HI|HIGH)(?!\s*(?:HI|HIGH))\b", t): return "H"
    if re.search(r"\b(LO|LOW)(?!\s*(?:LO|LOW))\b", t): return "L"
    return None


def severity_code_to_label(code):
    """Convert severity code to human-readable label."""
    return {'HH': 'High High', 'H': 'High', 'LL': 'Low Low', 'L': 'Low'}.get(code, code or "")


# =============================================================================
# ALARM TAG CONVERSION (from prefix_handler.py)
# =============================================================================

def convert_alarm_tag_to_transmitter(tag_id):
    """Convert alarm tag to transmitter tag. Switches keep their tag.
    Returns (converted_tag, alarm_level, is_switch)."""
    if not tag_id:
        return tag_id, None, False

    # Check switch first: has S before alarm level
    switch_pattern = re.compile(r'^([PLTFAVD])([XI]?)S(HH|H|LL|L)?-(.+)$', re.IGNORECASE)
    match = switch_pattern.match(str(tag_id))
    if match:
        return tag_id, match.group(3).upper() if match.group(3) else None, True

    # Alarm tags (not switches): XAH, XAHH, XAL, XALL
    alarm_pattern = re.compile(r'^([PLTFAVD])([XI]?)A(HH|H|LL|L)-(.+)$', re.IGNORECASE)
    match = alarm_pattern.match(str(tag_id))
    if not match:
        # Try DP/PD differential pressure
        dp_alarm = re.compile(r'^(PD|DP)A(HH|H|LL|L)-(.+)$', re.IGNORECASE)
        match_dp = dp_alarm.match(str(tag_id))
        if match_dp:
            level = match_dp.group(2).upper()
            number = match_dp.group(3).upper()
            return f"PDIT-{number}", level, False
        return tag_id, None, False

    meas_type = match.group(1).upper()
    modifier = match.group(2).upper() if match.group(2) else ''
    alarm_level = match.group(3).upper()
    number = match.group(4).upper()

    base_prefix = ALARM_TO_TRANSMITTER.get(meas_type, f'{meas_type}IT')
    if modifier:
        transmitter_prefix = base_prefix[0] + modifier + base_prefix[1:]
    else:
        transmitter_prefix = base_prefix

    return f"{transmitter_prefix}-{number}", alarm_level, False


# =============================================================================
# EQUIPMENT CLASSIFICATION (from equipment_classifier.py)
# =============================================================================

def classify_equipment_type(tag_name, description, target_id):
    """Unified equipment classification.
    Priority: valve_position_switch > switch > motor > valve > generic."""
    is_vps = is_valve_position_switch(target_id)
    is_sw = False if is_vps else is_switch_tag(target_id)
    is_mot = False if (is_sw or is_vps) else is_motor_io(tag_name, description, target_id)
    is_vlv = is_valve_tag(target_id, description)

    if is_vps or is_vlv:
        return 'valve'
    elif is_sw:
        return 'switch'
    elif is_mot:
        return 'motor'
    else:
        return 'generic'


def resolve_motor_tnd(tag_name, description, is_output=False):
    """Resolve target_name_description for motor tags."""
    if is_output:
        return "Run Command", "0=Off;1=On"
    if is_vfd_fault(tag_name, description):
        return "VFD Fault Status", "0=Ok;1=Fault"
    desc_upper = (description or "").upper()
    tag_upper = (tag_name or "").upper()
    for trigger in (AUTO_STATUS_TRIGGERS or []):
        if trigger.upper() in tag_upper or trigger.upper() in desc_upper:
            return "Auto Status", "0=Not in Auto;1=Auto"
    for trigger in (RUN_STATUS_TRIGGERS or []):
        if trigger.upper() in tag_upper or trigger.upper() in desc_upper:
            return "Run Status", "0=Off;1=Running"
    return "Run Status", "0=Off;1=Running"


def resolve_valve_tnd(tag_name, target_id, description, is_output=False):
    """Resolve target_name_description for valve tags."""
    if is_output:
        return "Output Command", "0=Closed;1=Open"
    prefix = target_id.split('-')[0].upper() if target_id and '-' in target_id else (target_id or "").upper()
    if prefix in ('ZSO', 'XSO'):
        return "Open Switch Status", "0=Not Open;1=Open"
    if prefix in ('ZSC', 'XSC'):
        return "Closed Switch Status", "0=Not Closed;1=Closed"
    desc_upper = (description or "").upper()
    tag_upper = (tag_name or "").upper()
    if re.search(r'\bOPEN\b', desc_upper) or re.match(r'^[ZX]SO[-_]', tag_upper):
        return "Open Switch Status", "0=Not Open;1=Open"
    if re.search(r'\bCLOS', desc_upper) or re.match(r'^[ZX]SC[-_]', tag_upper):
        return "Closed Switch Status", "0=Not Closed;1=Closed"
    return "Switch Status", ""


def resolve_analog_input_tnd(target_id):
    """Determine TND for analog input: 'Rate' for flow, 'Process Value' otherwise."""
    if target_id and target_id.upper().startswith('F'):
        return "Rate"
    return "Process Value"


# =============================================================================
# CORE CLASSIFICATION FUNCTIONS
# =============================================================================

def identify_tag_type(description):
    """Identify tag type from description keywords."""
    if not description or not isinstance(description, str):
        return "UNCLASSIFIED"
    desc_upper = description.upper()
    for tag_type, keywords in CLASSIFICATION_KEYWORDS.items():
        if any(kw in desc_upper for kw in keywords):
            return tag_type.replace('_', ' ').title()
    return "UNCLASSIFIED"


def extract_tag_id_from_description(description):
    """Extract tag ID from start of description."""
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
    """Classify IO by ISA pattern matching."""
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
            return {'pattern': pattern, 'type': meas_type, 'description': 'Process Value', 'order': 0}
    for pattern, ctrl_type in CONTROLLER_PATTERNS.items():
        if pattern in desc_upper or pattern in tag_upper:
            return {'pattern': pattern, 'type': ctrl_type, 'description': 'Control Signal', 'order': 0}
    for pattern, valve_type in VALVE_PATTERNS.items():
        if pattern in desc_upper or pattern in tag_upper:
            return {'pattern': pattern, 'type': valve_type, 'description': 'Control Valve', 'order': 0}
    return None


def validate_target_name(target_name):
    """Validate target_name against approved list."""
    if not target_name:
        return "UNCLASSIFIED"
    for valid_name in VALID_TARGET_NAMES:
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
    if 'TODAY' in desc_upper and 'VOLUME' in desc_upper:
        return 'Day 0 Volume'
    day0_pattern = re.compile(r'DAY\s*[_$-]?\s*0|DAY0', re.IGNORECASE)
    day1_pattern = re.compile(r'DAY\s*[_$-]?\s*1|DAY1', re.IGNORECASE)
    if 'FLOW' in address_upper:
        if 'DAY0' in address_upper or '.DAY0' in address_upper: return 'Day 0 Volume'
        if 'DAY1' in address_upper or '.DAY1' in address_upper: return 'Day 1 Volume'
    if day0_pattern.search(desc_str): return 'Day 0 Volume'
    if day1_pattern.search(desc_str): return 'Day 1 Volume'
    return None


def extract_volume_unit_from_description(description):
    """Extract engineering unit from description."""
    if not description or not isinstance(description, str):
        return None
    desc = str(description)
    known_units = re.compile(
        r'\((PSIG|PSIA|PSI|MCFD|MCF|BPD|BBLS|GPM|Vdc|VDC|VAC|mA|MA|Deg\s*[FC]|Inches|IN|%|Hz)\)\s*$',
        re.IGNORECASE)
    match = known_units.search(desc)
    if match: return match.group(1).lower()
    p2 = re.compile(r'\([^,]+,\s*([A-Za-z%]+)\)\s*$')
    match = p2.search(desc)
    if match: return match.group(1).lower()
    p3 = re.compile(r'(Deg\s*[FC])\.?\s*$', re.IGNORECASE)
    match = p3.search(desc)
    if match: return match.group(1).lower()
    if re.search(r'\d+-\d+%|\b\d+%', desc): return "%"
    for pat in [r'\b(MSCFD|MCFD|MSCF|MCF|BPD|BBLS|GPM)\b', r'\b(PSIG|PSIA|PSI|BARG|BARA)\b']:
        match = re.search(pat, desc, re.IGNORECASE)
        if match: return match.group(1).lower()
    return None


def normalize_unit_lowercase(unit):
    """Normalize engineering units to lowercase."""
    if not unit: return ''
    unit = str(unit).strip()
    keep_uppercase = ['DEGF', 'DEGC']
    if unit.upper() in keep_uppercase: return unit.upper()
    special = {
        '"': 'in', '" WC': 'in wc', '"WC': 'in wc', 'IN WC': 'in wc',
        'IN': 'in', 'PSI': 'psi', 'PSIG': 'psig', 'PSIA': 'psia',
        'GPM': 'gpm', 'BPD': 'bpd', 'MCF': 'mcf', 'MCFD': 'mcfd',
        'MSCF': 'mscf', 'MSCFD': 'mscfd', 'ACFM': 'acfm', 'HZ': 'hz',
        'MA': 'ma', 'M/A': '', '%': '%', 'BBLS': 'bpd',
    }
    return special.get(unit.upper(), unit.lower())


def detect_hoa_pattern(description):
    """Detect Hand/Off/Auto (HOA) pattern."""
    if not description: return False
    desc_upper = str(description).upper()
    if re.search(r'\bHOA\b', desc_upper): return True
    if 'HAND' in desc_upper and 'OFF' in desc_upper and 'AUTO' in desc_upper: return True
    if re.search(r'HAND[/\-]OFF[/\-]AUTO', desc_upper): return True
    if re.search(r'\bH[/\-]O[/\-]A\b', desc_upper): return True
    return False


def detect_permissive_pattern(description):
    """Detect Permissive pattern in description."""
    if not description: return False
    return 'PERMISSIVE' in str(description).upper()


def detect_setpoint_type(description):
    """Detect specific setpoint type from description."""
    if not description: return None
    desc_upper = str(description).upper()
    if 'SETPOINT' not in desc_upper and 'SET POINT' not in desc_upper:
        return None
    patterns = [
        (r'HIGH\s*HIGH\s*(?:ALARM\s*)?SET\s*POINT', 'High High Alarm Setpoint'),
        (r'(?:ALARM\s*)?HIGH\s*HIGH\s*SET\s*POINT', 'High High Alarm Setpoint'),
        (r'LOW\s*LOW\s*(?:ALARM\s*)?SET\s*POINT', 'Low Low Alarm Setpoint'),
        (r'(?:ALARM\s*)?LOW\s*LOW\s*SET\s*POINT', 'Low Low Alarm Setpoint'),
        (r'HIGH\s*(?:ALARM\s*)?SET\s*POINT', 'High Alarm Setpoint'),
        (r'(?:ALARM\s*)?HIGH\s*SET\s*POINT', 'High Alarm Setpoint'),
        (r'LOW\s*(?:ALARM\s*)?SET\s*POINT', 'Low Alarm Setpoint'),
        (r'(?:ALARM\s*)?LOW\s*SET\s*POINT', 'Low Alarm Setpoint'),
    ]
    for pattern, sp_type in sorted(patterns, key=lambda x: len(x[0]), reverse=True):
        if re.search(pattern, desc_upper):
            return sp_type
    return 'Setpoint'


def is_alarm_address(address):
    """Check if address is ALARM[...] type."""
    if not address: return False
    return bool(re.match(r'^ALARM\[\d+\]', str(address), re.IGNORECASE))


def is_writefloat_address(address):
    """Check if address is WRITEFLOAT[...] type."""
    if not address: return False
    return bool(re.match(r'^WRITEFLOAT\[\d+\]', str(address), re.IGNORECASE))


# =============================================================================
# ENHANCED TAG EXTRACTION
# =============================================================================

def extract_tag_from_alarm_description(description):
    """Extract tag from alarm/setpoint description - handles multiple patterns."""
    if not description or not isinstance(description, str):
        return None

    ALARM_TO_TX = ALARM_TO_TRANSMITTER

    # PATTERN 1: Tag_Number_Alarm at start
    p1 = re.compile(r'^([PLTFAVD])IT[-_]([A-Z]?\d+(?:[-_]\d+)?)[-_](?:[PLTFAVD][XI]?(?:A|S)?(?:HH|H|LL|L))\s', re.IGNORECASE)
    match = p1.match(description)
    if match:
        meas = match.group(1).upper()
        number = match.group(2).upper().replace('_', '-')
        return f"{ALARM_TO_TX.get(meas, f'{meas}IT')}-{number}"

    # PATTERN 2: Alarm-Tag at end
    p2 = re.compile(r'([PLTFAVD])([XI]?)(S)?([AO])?(HH|H|LL|L)-([A-Z]?\d+[A-Z]?(?:[-_]\d+)?)\s*$', re.IGNORECASE)
    match = p2.search(description)
    if match:
        meas = match.group(1).upper()
        mod = match.group(2).upper() if match.group(2) else ''
        is_sw = match.group(3) is not None
        level = match.group(5).upper()
        number = match.group(6).upper()
        if is_sw:
            prefix = f"{meas}{mod}S{level}" if mod else f"{meas}S{level}"
        else:
            base = ALARM_TO_TX.get(meas, f'{meas}IT')
            prefix = base[0] + 'X' + base[1:] if mod == 'X' else base
        return f"{prefix}-{number}"

    # PATTERN 3: (Alarm-Tag-Setpoint in parentheses
    p3 = re.compile(r'\(([PLTFAVD])([XI]?)(S)?([AO])?(HH|H|LL|L)-([A-Z]?\d+[A-Z]?(?:[-_][A-Z]?\d+)?)-?(?:[Ss]etpoint|[Ss][Pp]|[Ss]et[- ][Pp]oint)', re.IGNORECASE)
    match = p3.search(description)
    if match:
        meas = match.group(1).upper()
        mod = match.group(2).upper() if match.group(2) else ''
        is_sw = match.group(3) is not None
        level = match.group(5).upper()
        number = match.group(6).upper()
        if is_sw:
            prefix = f"{meas}{mod}S{level}" if mod else f"{meas}S{level}"
        else:
            base = ALARM_TO_TX.get(meas, f'{meas}IT')
            prefix = base[0] + 'X' + base[1:] if mod == 'X' else base
        return f"{prefix}-{number}"

    # PATTERN 4: (Alarm-Tag) in parentheses
    p4 = re.compile(r'\(([PLTFAVD])([XI]?)(S)?([AO])?(HH|H|LL|L)-([A-Z]?\d+[A-Z]?(?:[-_]\d+)?)\)', re.IGNORECASE)
    match = p4.search(description)
    if match:
        meas = match.group(1).upper()
        mod = match.group(2).upper() if match.group(2) else ''
        is_sw = match.group(3) is not None
        level = match.group(5).upper()
        number = match.group(6).upper()
        if is_sw:
            prefix = f"{meas}{mod}S{level}" if mod else f"{meas}S{level}"
        else:
            base = ALARM_TO_TX.get(meas, f'{meas}IT')
            prefix = base[0] + 'X' + base[1:] if mod == 'X' else base
        return f"{prefix}-{number}"

    return None


def extract_alarm_switch_tag(description):
    """Extract alarm/switch tag from start of description."""
    if not description or not isinstance(description, str):
        return None, description
    alarm_tag_pattern = re.compile(
        r'^([DPLTFA][DPXIA]?(?:SHH|SH|SLL|SL|AHH|AH|ALL|AL))[-_]?([A-Z]?[-_]?\d+[A-Z]?(?:[-_][A-Z0-9]+)?)\s*',
        re.IGNORECASE)
    match = alarm_tag_pattern.match(description)
    if match:
        prefix = match.group(1).upper()
        number = match.group(2).upper().replace('_', '-')
        tag_id = f"{prefix}-{number}".replace('--', '-')
        remaining = description[match.end():].strip()
        return tag_id, remaining
    return None, description


def extract_transmitter_id(description):
    """Extract transmitter tag ID from description."""
    if not description or not isinstance(description, str):
        return None
    desc_upper = description.upper()
    for prefix in TRANSMITTER_PREFIXES:
        for pattern in [rf'\b({prefix})[-_\s]?(\d+[A-Z]?)\b', rf'\b({prefix})(\d+[A-Z]?)\b']:
            match = re.search(pattern, desc_upper)
            if match:
                return f"{match.group(1)}-{match.group(2)}"
    return None


def extract_alarm_level_from_description(description):
    """Extract alarm level from description tag pattern at end."""
    if not description: return None, False
    pattern = re.compile(r'([PLTFAVD])([XI]?)(S)?A?(HH|H|LL|L)-[A-Z]?\d+[A-Z]?(?:[-_]\d+)?\s*$', re.IGNORECASE)
    match = pattern.search(description)
    if match:
        return match.group(4).upper(), match.group(3) is not None
    return None, False


def extract_alarm_level_from_keywords(description):
    """Extract alarm level from keywords."""
    if not description: return None, False
    desc_upper = str(description).upper()
    is_sw = bool(re.search(r'\bSW\b|\bSWITCH\b|\bSWTICH\b', desc_upper))
    if 'HIGH HIGH' in desc_upper or 'HI HI' in desc_upper: return 'HH', is_sw
    if 'LOW LOW' in desc_upper or 'LO LO' in desc_upper: return 'LL', is_sw
    if re.search(r'\bHIGH\b', desc_upper) and 'HIGH HIGH' not in desc_upper: return 'H', is_sw
    if re.search(r'\bLOW\b', desc_upper) and 'LOW LOW' not in desc_upper: return 'L', is_sw
    return None, is_sw


def classify_from_tag_id(tag_id, plc_address):
    """Classify TND based on tag_id when description is empty."""
    if not tag_id: return None, False
    tag_upper = str(tag_id).upper()

    # Valve position switches
    if re.match(r'^[ZX][SI][OC][-_]', tag_upper):
        return resolve_valve_tnd(None, tag_id, "", False)[0], False

    # Switches
    if re.match(r'^([PLTFAVD])([XI]?)S(HH|H|LL|L)?[-_]', tag_upper):
        if plc_address and re.match(r'^ALARM\[\d+\]', str(plc_address), re.IGNORECASE):
            return "Alarm", True
        return "Input", True

    # Transmitters
    if re.match(r'^([PLTFAVD])([XI]?)IT[-_]', tag_upper):
        return resolve_analog_input_tnd(tag_id), False

    # Alarm tags
    alarm_match = re.match(r'^([PLTFAVD])([XI]?)A(HH|H|LL|L)[-_]', tag_upper)
    if alarm_match:
        level = alarm_match.group(3).upper()
        return {'HH': 'High High Alarm', 'H': 'High Alarm', 'L': 'Low Alarm', 'LL': 'Low Low Alarm'}.get(level, 'Alarm'), False

    # Controllers
    if re.match(r'^([PLTFAVD])([XI]?)IC[-_]', tag_upper):
        return "Control Signal", False

    # Valves
    if re.match(r'^([PLTFAVD])?[XY]V?[-_]|^[PLTF]CV[-_]', tag_upper):
        return "Control Valve", False

    return None, False


def get_alarm_tnd_from_level(alarm_level, has_setpoint, is_switch=False, plc_address=None):
    """Get target_name_description from alarm level."""
    if is_switch:
        if plc_address and re.match(r'^ALARM\[\d+\]', str(plc_address), re.IGNORECASE):
            return "Alarm"
        return "Input"
    level_to_tnd = {'HH': 'High High Alarm', 'H': 'High Alarm', 'L': 'Low Alarm', 'LL': 'Low Low Alarm'}
    base = level_to_tnd.get(alarm_level, 'High Alarm')
    if has_setpoint:
        return f"{base} Setpoint"
    return base


def clean_alarm_description(description, alarm_level, has_setpoint):
    """Clean description by removing Alarm, Setpoint when confident."""
    if not description or not alarm_level:
        return description
    cleaned = description
    for pat in [r'\s+Alarm\s+Set\s*Point\s*$', r'\s+Alarm\s+Setpoint\s*$',
                r'\s+Set\s*Point\s*$', r'\s+Setpoint\s*$', r'\s+Alarm\s*$']:
        cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def enhance_with_isa_measurement(equipment_desc, target_id):
    """Add ISA measurement type to equipment description if missing.
    (from description_formatter.py)
    E.g., if target_id starts with P and description doesn't have 'Pressure', prepend it."""
    if not target_id or not equipment_desc:
        return equipment_desc
    prefix = target_id.split('-')[0].upper() if '-' in target_id else target_id.upper()
    first_letter = prefix[0] if prefix else ''

    ISA_MEASUREMENT = {
        'P': 'Pressure', 'T': 'Temperature', 'L': 'Level',
        'F': 'Flow', 'A': 'Analytical', 'V': 'Vibration',
    }
    meas = ISA_MEASUREMENT.get(first_letter)
    if not meas:
        return equipment_desc
    if meas.upper() in equipment_desc.upper():
        return equipment_desc
    return f"{equipment_desc} {meas}" if equipment_desc else meas


# =============================================================================
# MAIN PROCESSING FUNCTION
# =============================================================================

def process_io_to_mtl(row):
    """Process a single IO row to MTL format.
    ENHANCED with all L5K parser classification rules."""
    original_tag = str(row['IO Address'])
    description = row.get('Description', '')
    rack_target_id = str(row.get('target_id_rack', '') or '')
    rack_units = str(row.get('target_units', '') or '')
    rack_description = str(row.get('rack_description', '') or '')

    if pd.isna(description): description = ""
    if pd.isna(rack_target_id) or rack_target_id == 'nan': rack_target_id = ""
    if pd.isna(rack_units) or rack_units == 'nan': rack_units = ""
    if pd.isna(rack_description) or rack_description == 'nan': rack_description = ""

    is_alarm = is_alarm_address(original_tag)
    is_writefloat = is_writefloat_address(original_tag)

    # STEP 1: Day volume detection
    day_volume = detect_day_volume(original_tag, description)

    # STEP 2: Units
    final_units = rack_units
    if not final_units:
        volume_unit = extract_volume_unit_from_description(description)
        if volume_unit:
            final_units = volume_unit
    final_units = normalize_unit_lowercase(final_units)

    # STEP 3: Tag ID resolution
    tag_id = None
    equipment = description
    alarm_level_from_tag = None
    is_switch = False

    if rack_target_id:
        tag_id = rack_target_id
        equipment = rack_description if rack_description else description
    else:
        # Try alarm description patterns
        alarm_tag = extract_tag_from_alarm_description(description)
        if alarm_tag:
            tag_id = alarm_tag
            equipment = description
        else:
            alarm_tag, remaining_desc = extract_alarm_switch_tag(description)
            if alarm_tag:
                tag_id = alarm_tag
                equipment = remaining_desc
            else:
                transmitter_id = extract_transmitter_id(description)
                if transmitter_id:
                    tag_id = transmitter_id
                    _, equipment = extract_tag_id_from_description(description)
                else:
                    extracted_tag, equipment = extract_tag_id_from_description(description)
                    if extracted_tag:
                        tag_id = extracted_tag

    # STEP 4: Generate tag_id from address if still empty
    if not tag_id:
        array_match = re.search(r'([A-Z_]+)\[(\d+)\]', original_tag)
        if array_match:
            tag_id = f"{array_match.group(1)}-{array_match.group(2)}"
        else:
            tag_match = re.search(r'([A-Z]+)[-_](\d+)', original_tag)
            if tag_match:
                tag_id = f"{tag_match.group(1)}-{tag_match.group(2)}"
            else:
                tag_id = original_tag
                for suffix in IO_SUFFIXES:
                    if tag_id.endswith(suffix):
                        tag_id = tag_id[:-len(suffix)]

    # STEP 5: Normalize tag_id
    tag_id = normalize_target_id(tag_id)

    # STEP 5a: Convert alarm tag to transmitter
    converted_tag, alarm_level_from_tag, is_switch = convert_alarm_tag_to_transmitter(tag_id)
    if converted_tag != tag_id:
        tag_id = converted_tag

    # STEP 5b: Normalize transmitter prefix (PT->PIT, LI->LIT, etc.)
    tag_id = normalize_transmitter_prefix(tag_id)

    # STEP 5c: Resolve valve target_id (LY->LV, ZSO->XV)
    if is_valve_tag(tag_id):
        tag_id = resolve_valve_target_id(tag_id)

    # STEP 5d: Extract alarm level from description if not from tag
    if not alarm_level_from_tag:
        alarm_level_from_tag, is_switch = extract_alarm_level_from_description(description)
    if not alarm_level_from_tag:
        alarm_level_from_tag, is_switch = extract_alarm_level_from_keywords(description)

    # STEP 5e: Try severity detection from full tag+description
    if not alarm_level_from_tag:
        severity = detect_severity_code(f"{original_tag} {description}")
        if severity:
            alarm_level_from_tag = severity

    has_setpoint = bool(re.search(r'set\s*point|setpoint', str(description), re.IGNORECASE))

    # STEP 6: Equipment classification and TND determination
    eq_type = classify_equipment_type(original_tag, description, tag_id)
    states = ''
    target_name = None

    # Priority: Day volume > HOA > Permissive > equipment type > alarm level > setpoint > ISA
    if day_volume:
        target_name = day_volume
    elif detect_hoa_pattern(description):
        target_name = "Hand/Off/Auto Status"
    elif detect_permissive_pattern(description):
        target_name = "Permissive Status"
    elif eq_type == 'motor' and not alarm_level_from_tag:
        target_name, states = resolve_motor_tnd(original_tag, description)
        equipment = strip_motor_status_words(equipment)
    elif eq_type == 'valve' and not alarm_level_from_tag:
        target_name, states = resolve_valve_tnd(original_tag, tag_id, description)
        equipment = strip_valve_status_words(equipment)
    elif alarm_level_from_tag:
        target_name = get_alarm_tnd_from_level(alarm_level_from_tag, has_setpoint, is_switch, original_tag)
    elif 'SETPOINT' in str(description).upper() or 'SET POINT' in str(description).upper():
        setpoint_type = detect_setpoint_type(description)
        target_name = setpoint_type if setpoint_type else 'Setpoint'
    elif is_alarm:
        target_name = "Alarm"
    else:
        # ISA pattern classification
        classification = classify_by_pattern(original_tag, description)
        if classification:
            target_name = classification['description']
        else:
            target_name = identify_tag_type(description)

    # STEP 7: Validate target_name
    target_name_validated = validate_target_name(target_name)

    # STEP 7.5: Fallback - classify from tag_id if still UNCLASSIFIED
    if target_name_validated in ['UNCLASSIFIED', 'Spare'] and tag_id:
        tnd_from_tag, is_switch_from_tag = classify_from_tag_id(tag_id, original_tag)
        if tnd_from_tag:
            target_name_validated = tnd_from_tag
            if is_switch_from_tag:
                is_switch = is_switch_from_tag

    # STEP 8: Clean equipment description based on type
    if alarm_level_from_tag:
        equipment = clean_alarm_description(equipment, alarm_level_from_tag, has_setpoint)
        equipment = strip_alarm_suffix_from_description(equipment)
    
    # Strip scaling range from equipment description
    equipment = strip_scaling_range(equipment)

    # Enhance with ISA measurement type
    equipment = enhance_with_isa_measurement(equipment, tag_id)

    # STEP 9: Process equipment description (proper case)
    equipment_final = capitalize_proper(equipment) if equipment else ""

    # Get classification for sort order
    classification = classify_by_pattern(original_tag, description)

    # STEP 10: Build MTL entry
    mtl_entry = {
        'target_id': tag_id,
        'target_units': final_units,
        'equipment_description': equipment_final,
        'target_name_description': target_name_validated,
        'target_scaling': '',
        'states': states,
        'iconics_plc_path': original_tag,
        'target_description': capitalize_proper(description) if description else "",
        'description_source': row.get('Description Source', 'Unknown'),
        'screens': row.get('Screens', ''),
        'sort_order': classification['order'] if classification else 999,
    }

    return mtl_entry


# =============================================================================
# CONVERSION AND OUTPUT
# =============================================================================

def convert_to_mtl(input_path, output_path):
    """Main conversion function."""
    print("=" * 80)
    print("STEP 3: CONVERT TO MTL (ENHANCED WITH L5K PARSER RULES)")
    print("=" * 80)

    # Load enriched IOs
    print(f"\nLoading enriched IOs: {input_path}")
    df = pd.read_excel(input_path)
    print(f"  -> Loaded {len(df)} IOs")

    # Check for RACK columns
    has_rack_target = 'target_id_rack' in df.columns
    has_rack_units = 'target_units' in df.columns
    has_rack_desc = 'rack_description' in df.columns

    print(f"\n  RACK data columns:")
    print(f"    -> target_id_rack: {'YES' if has_rack_target else 'NO'}")
    print(f"    -> target_units: {'YES' if has_rack_units else 'NO'}")
    print(f"    -> rack_description: {'YES' if has_rack_desc else 'NO'}")

    if has_rack_target:
        rack_count = len(df[df['target_id_rack'].notna() & (df['target_id_rack'] != '')])
        print(f"    -> IOs with RACK target_id: {rack_count}")
    if has_rack_units:
        unit_count = len(df[df['target_units'].notna() & (df['target_units'] != '')])
        print(f"    -> IOs with RACK units: {unit_count}")

    # Process each IO
    print("\nConverting IOs to MTL format...")

    mtl_entries = []
    classification_stats = defaultdict(int)
    units_filled = 0
    units_from_description = 0
    day_volume_count = 0
    motor_count = 0
    valve_count = 0

    for idx, row in df.iterrows():
        mtl_entry = process_io_to_mtl(row)
        mtl_entries.append(mtl_entry)

        classification_stats[mtl_entry['target_name_description']] += 1
        if mtl_entry['target_units']:
            units_filled += 1
            rack_unit = row.get('target_units', '')
            if pd.isna(rack_unit) or rack_unit == '':
                units_from_description += 1

        if 'Day' in mtl_entry['target_name_description'] and 'Volume' in mtl_entry['target_name_description']:
            day_volume_count += 1
        if mtl_entry['states'] and 'Running' in mtl_entry['states']:
            motor_count += 1
        if mtl_entry['states'] and 'Open' in mtl_entry['states']:
            valve_count += 1

    # Create DataFrame
    df_mtl = pd.DataFrame(mtl_entries)

    # Sort
    df_mtl = df_mtl.sort_values(['target_id', 'sort_order'])
    df_mtl = df_mtl.drop('sort_order', axis=1)

    # Save
    print(f"\nSaving MTL: {output_path}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_mtl.to_excel(writer, sheet_name='MASTER TAG LIST', index=False)

        worksheet = writer.sheets['MASTER TAG LIST']
        worksheet.column_dimensions['A'].width = 15  # target_id
        worksheet.column_dimensions['B'].width = 12  # target_units
        worksheet.column_dimensions['C'].width = 50  # equipment_description
        worksheet.column_dimensions['D'].width = 30  # target_name_description
        worksheet.column_dimensions['E'].width = 15  # target_scaling
        worksheet.column_dimensions['F'].width = 25  # states
        worksheet.column_dimensions['G'].width = 35  # iconics_plc_path
        worksheet.column_dimensions['H'].width = 60  # target_description
        worksheet.column_dimensions['I'].width = 20  # description_source
        worksheet.column_dimensions['J'].width = 80  # screens

    print(f"  -> Saved: {output_path}")

    # Statistics
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    print(f"Total entries: {len(df_mtl)}")
    print(f"\nUnits filled:")
    print(f"  -> Total with target_units: {units_filled} ({units_filled/max(len(df_mtl),1)*100:.1f}%)")
    print(f"  -> From RACK screens: {units_filled - units_from_description}")
    print(f"  -> From description: {units_from_description}")

    print(f"\nEquipment classification (NEW):")
    print(f"  -> Motor IOs detected: {motor_count}")
    print(f"  -> Valve IOs detected: {valve_count}")
    print(f"  -> Day Volume entries: {day_volume_count}")

    unclassified_count = len(df_mtl[df_mtl['target_name_description'] == 'UNCLASSIFIED'])
    if unclassified_count > 0:
        print(f"\n⚠️  UNCLASSIFIED entries: {unclassified_count} ({unclassified_count/max(len(df_mtl),1)*100:.1f}%)")

    print("\nClassification breakdown:")
    for category, count in sorted(classification_stats.items(), key=lambda x: -x[1]):
        percentage = (count / len(df_mtl) * 100) if len(df_mtl) > 0 else 0
        prefix = "⚠️ " if category == "UNCLASSIFIED" else "  "
        print(f"{prefix}- {category}: {count} ({percentage:.1f}%)")


def main():
    print("\n" + "=" * 80)
    print("ICONICS MTL CONVERTER - ENHANCED WITH L5K PARSER RULES")
    print("=" * 80)

    if not os.path.exists(ENRICHED_PATH):
        print(f"ERROR: {ENRICHED_PATH} not found. Run step2 first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    convert_to_mtl(ENRICHED_PATH, FINAL_MTL_PATH)

    print("\n" + "=" * 80)
    print("STEP 3 COMPLETED!")
    print("=" * 80)
    print(f"\nFinal output: {FINAL_MTL_PATH}")


if __name__ == '__main__':
    main()