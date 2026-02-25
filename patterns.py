# """
# ISA Patterns, Abbreviations, and Classification Constants.

# Used primarily by Step 3 (MTL conversion) for tag classification.
# """

# # =============================================================================
# # ALARM PATTERNS  {pattern: {type, description, order}}
# # =============================================================================
# ALARM_PATTERNS = {
#     # Pressure
#     'PAHH': {'type': 'Pressure', 'description': 'High High Alarm', 'order': 1},
#     'PAH':  {'type': 'Pressure', 'description': 'High Alarm', 'order': 2},
#     'PAL':  {'type': 'Pressure', 'description': 'Low Alarm', 'order': 3},
#     'PALL': {'type': 'Pressure', 'description': 'Low Low Alarm', 'order': 4},
#     # Level
#     'LAHH': {'type': 'Level', 'description': 'High High Alarm', 'order': 1},
#     'LAH':  {'type': 'Level', 'description': 'High Alarm', 'order': 2},
#     'LAL':  {'type': 'Level', 'description': 'Low Alarm', 'order': 3},
#     'LALL': {'type': 'Level', 'description': 'Low Low Alarm', 'order': 4},
#     # Interface Level
#     'LXAHH': {'type': 'Interface Level', 'description': 'High High Alarm', 'order': 1},
#     'LXAH':  {'type': 'Interface Level', 'description': 'High Alarm', 'order': 2},
#     'LXAL':  {'type': 'Interface Level', 'description': 'Low Alarm', 'order': 3},
#     'LXALL': {'type': 'Interface Level', 'description': 'Low Low Alarm', 'order': 4},
#     # Temperature
#     'TAHH': {'type': 'Temperature', 'description': 'High High Alarm', 'order': 1},
#     'TAH':  {'type': 'Temperature', 'description': 'High Alarm', 'order': 2},
#     'TAL':  {'type': 'Temperature', 'description': 'Low Alarm', 'order': 3},
#     'TALL': {'type': 'Temperature', 'description': 'Low Low Alarm', 'order': 4},
#     # Flow
#     'FAHH': {'type': 'Flow', 'description': 'High High Alarm', 'order': 1},
#     'FAH':  {'type': 'Flow', 'description': 'High Alarm', 'order': 2},
#     'FAL':  {'type': 'Flow', 'description': 'Low Alarm', 'order': 3},
#     'FALL': {'type': 'Flow', 'description': 'Low Low Alarm', 'order': 4},
# }

# # =============================================================================
# # SWITCH PATTERNS
# # =============================================================================
# SWITCH_PATTERNS = {
#     # Level
#     'LSHH': {'type': 'Level', 'description': 'Switch', 'order': 1},
#     'LSH':  {'type': 'Level', 'description': 'Switch', 'order': 2},
#     'LSL':  {'type': 'Level', 'description': 'Switch', 'order': 3},
#     'LSLL': {'type': 'Level', 'description': 'Switch', 'order': 4},
#     # Interface Level
#     'LXSHH': {'type': 'Interface Level', 'description': 'Switch', 'order': 1},
#     'LXSH':  {'type': 'Interface Level', 'description': 'Switch', 'order': 2},
#     'LXSL':  {'type': 'Interface Level', 'description': 'Switch', 'order': 3},
#     'LXSLL': {'type': 'Interface Level', 'description': 'Switch', 'order': 4},
#     # Pressure
#     'PSHH': {'type': 'Pressure', 'description': 'Switch', 'order': 1},
#     'PSH':  {'type': 'Pressure', 'description': 'Switch', 'order': 2},
#     'PSL':  {'type': 'Pressure', 'description': 'Switch', 'order': 3},
#     'PSLL': {'type': 'Pressure', 'description': 'Switch', 'order': 4},
#     # Temperature
#     'TSHH': {'type': 'Temperature', 'description': 'Switch', 'order': 1},
#     'TSH':  {'type': 'Temperature', 'description': 'Switch', 'order': 2},
#     'TSL':  {'type': 'Temperature', 'description': 'Switch', 'order': 3},
#     'TSLL': {'type': 'Temperature', 'description': 'Switch', 'order': 4},
# }

# # =============================================================================
# # TRANSMITTER / CONTROLLER / VALVE PATTERNS
# # =============================================================================
# TRANSMITTER_PATTERNS = {
#     'PIT': 'Pressure', 'LIT': 'Level', 'LXIT': 'Interface Level',
#     'TIT': 'Temperature', 'FIT': 'Flow', 'AT': 'Analysis',
#     'DPIT': 'Differential Pressure',
# }

# CONTROLLER_PATTERNS = {
#     'PIC': 'Pressure', 'LIC': 'Level', 'LXIC': 'Interface Level',
#     'TIC': 'Temperature', 'FIC': 'Flow',
# }

# VALVE_PATTERNS = {
#     'PY': 'Pressure Control Valve', 'LY': 'Level Control Valve',
#     'LXY': 'Interface Level Control Valve', 'TY': 'Temperature Control Valve',
#     'FY': 'Flow Control Valve',
# }

# # =============================================================================
# # TRANSMITTER PREFIXES (for tag extraction from descriptions)
# # =============================================================================
# TRANSMITTER_PREFIXES = [
#     'PIT', 'PI', 'FIT', 'FI', 'TIT', 'TI', 'LIT', 'LI',
#     'LXIT', 'LXI', 'AT', 'AI', 'DPIT', 'DPI', 'FCU', 'TE', 'P',
# ]

# # =============================================================================
# # ABBREVIATION EXPANSION  {regex: replacement}
# # =============================================================================
# ABBREVIATIONS = {
#     # Equipment
#     r'\bSEP\b': 'Separator', r'\bSEPERATOR\b': 'Separator',
#     r'\bVESS\b': 'Vessel', r'\bTNK\b': 'Tank',
#     r'\bPMP\b': 'Pump', r'\bPMPS\b': 'Pumps',
#     r'\bVLV\b': 'Valve', r'\bVLVS\b': 'Valves',
#     # Process
#     r'\bDISC\b': 'Discharge', r'\bSUCT\b': 'Suction',
#     r'\bINLET\b': 'Inlet', r'\bOUTLET\b': 'Outlet',
#     r'\bRETURN\b': 'Return', r'\bRECYCLE\b': 'Recycle',
#     # Pressure
#     r'\bLP\b': 'Low Pressure', r'\bHP\b': 'High Pressure',
#     r'\bMP\b': 'Medium Pressure',
#     # Instrumentation
#     r'\bXMTR\b': 'Transmitter', r'\bXDUCER\b': 'Transducer',
#     r'\bINDIC\b': 'Indication', r'\bCTRL\b': 'Control',
#     r'\bSIG\b': 'Signal', r'\bSP\b': 'Setpoint',
#     # Measurement
#     r'\bLVL\b': 'Level', r'\bTEMP\b': 'Temperature',
#     r'\bPRESS\b': 'Pressure', r'\bFLOW\b': 'Flow',
#     # Fluids
#     r'\bWTR\b': 'Water', r'\bWW\b': 'Waste Water',
#     # Conditions
#     r'\bNORM\b': 'Normal', r'\bEMERG\b': 'Emergency',
#     r'\bSTDBY\b': 'Standby',
#     # Types
#     r'\bINTERF\b': 'Interface', r'\bOVER-ALL\b': 'Overall',
#     r'\bOVERALL\b': 'Overall', r'\bMANU\b': 'Manual',
#     r'\bAUTO\b': 'Automatic',
#     # Other
#     r'\bALM\b': 'Alarm', r'\bSHUT\b': 'Shutdown',
#     r'\bSTART\b': 'Startup', r'\bOPER\b': 'Operation',
#     r'\bCOMMON\b': 'Common', r'\bPRI\b': 'Primary',
#     r'\bSEC\b': 'Secondary', r'\bAUX\b': 'Auxiliary',
# }

# # =============================================================================
# # ACRONYMS TO PRESERVE (not expanded by capitalize_proper)
# # =============================================================================
# PRESERVED_ACRONYMS = [
#     # ISA Tags
#     'PIT', 'LIT', 'TIT', 'FIT', 'LXIT',
#     'PIC', 'LIC', 'TIC', 'FIC', 'LXIC',
#     'PY', 'LY', 'TY', 'FY', 'LXY',
#     # Systems
#     'IO', 'ID', 'PLC', 'VFD', 'PID', 'HMI', 'SCADA', 'RTU',
#     'AI', 'AO', 'DI', 'DO',
#     # Standards
#     'API', 'ANSI', 'ISA', 'BS&W',
#     # Units
#     'Hz', 'kW', 'MW', 'GW',
#     'PSI', 'PSIG', 'PSIA', 'BARG', 'BARA',
#     'BBL', 'BBLS', 'MCF', 'MCFD', 'MMCFD', 'GPM', 'BPD',
#     # Electrical
#     'AC', 'DC', 'USB', 'CPU', 'RAM', 'ROM',
# ]

# # =============================================================================
# # CLASSIFICATION KEYWORDS (fallback when ISA pattern doesn't match)
# # =============================================================================
# CLASSIFICATION_KEYWORDS = {
#     'spare': ['SPARE', 'UNUSED', 'RESERVED'],
#     'indication': ['SPEED', 'CURRENT', 'VOLTAGE', 'FREQUENCY', 'Hz', 'AMP', 'AMPS'],
#     'control_signal': ['CTRL', 'CONTROL', 'SIGNAL', 'OUTPUT'],
#     'selection': ['SELECTION', 'SELECT', 'MODE', 'CHOOSE'],
#     'display': ['DISPLAY', 'TEXT', 'MESSAGE', 'SHOW'],
# }

# # =============================================================================
# # VALID TARGET NAME DESCRIPTIONS (for the MTL output)
# # =============================================================================
# VALID_TARGET_NAMES = [
#     # Alarms
#     'Alarm', 'High Alarm', 'High High Alarm', 'Low Alarm', 'Low Low Alarm',
#     # Alarm Setpoints
#     'High Alarm Setpoint', 'High High Alarm Setpoint',
#     'Low Alarm Setpoint', 'Low Low Alarm Setpoint',
#     # Alarm Related
#     'Alarm Delay', 'High Alarm Delay', 'Alarm Reset', 'Fail to Open Alarm',
#     # Process Values
#     'Process Value', 'Process Variable', 'Input',
#     'Analog Input', 'Digital Input', 'Analog Output', 'Digital Output',
#     # Control
#     'Control Signal', 'Control Output', 'Control Variable',
#     'Setpoint', 'Manual Output', 'Process Value Setpoint', 'Control Setpoint',
#     # PID Parameters
#     'Proportional', 'Integral', 'Derivative', 'Maximum CV', 'Minimum CV',
#     # Flow / Volume
#     'Rate', 'Rate Day 0 Average', 'Day 0 Volume', 'Day 1 Volume',
#     'Current Volume', 'Volume at Midnight', 'Day 0 Inventory Change', 'Preset Volume',
#     # Pump / Motor
#     'Run Status', 'Run Command', 'Run Fail', 'Auto Status', 'Auto/Manual Mode',
#     'Hand/Off/Auto Status', 'Motor Current', 'Speed Feedback', 'VFD Fail', 'Runtime',
#     # Pump Setpoints
#     'Start Setpoint', 'Stop Setpoint', 'Start Command', 'Stop Command',
#     'Lead Start Setpoint', 'Lead Stop Setpoint',
#     'Lag Start Setpoint', 'Lag Stop Setpoint',
#     'Lag1 Start Setpoint', 'Lag1 Stop Setpoint',
#     'Lag2 Start Setpoint', 'Lag2 Stop Setpoint',
#     'Lag3 Start Setpoint', 'Lag3 Stop Setpoint',
#     'Level Start Setpoint', 'Level Stop Setpoint', 'Load Start Setpoint',
#     # Lead/Lag
#     'Lead/Lag Status', 'Lead Lag Status',
#     # Valve
#     'Control Valve', 'Pressure Control Valve', 'Level Control Valve',
#     'Temperature Control Valve', 'Flow Control Valve', 'Interface Level Control Valve',
#     'Open Switch Status', 'Closed Switch Status',
#     'Open Setpoint', 'Close Setpoint',
#     'Output Command', 'Solenoid Output Command',
#     # Switches
#     'Switch', 'High Switch', 'Low Switch',
#     # Status / Indication
#     'Status', 'Indication', 'Running Status', 'Fault Status',
#     'Permissive Status',
#     # Selection / State
#     'Selection', 'Mode', 'State', 'Selected Tank', 'Unit Loaded',
#     # Site / System
#     'Beacon Status', 'Site ESD Status', 'Site Well Shutdown Active',
#     'Power Fail', 'UPS Fail', 'Meter Fail', 'Sampler Fail', 'Sample Rate Setpoint',
#     # Measurement Types
#     'Temperature', 'Differential Pressure', 'Display',
#     # Other
#     'Spare', 'Unclassified', 'UNCLASSIFIED',
# ]

# # =============================================================================
# # IO ADDRESS SUFFIXES (to strip when cleaning addresses)
# # =============================================================================
# IO_SUFFIXES = ['!RD', '!WR', '!SC', '!BI', '!BO', '!AI', '!AO', '!DI', '!DO']

# # =============================================================================
# # DAY VOLUME PATTERNS
# # =============================================================================
# DAY_VOLUME_PATTERNS = {
#     'DAY0': 'Day 0 Volume',
#     'DAY1': 'Day 1 Volume',
# }

"""
Business Logic Patterns - ENHANCED VERSION
All ISA patterns, abbreviations, constants, and classification rules.

Incorporates rules from the L5K Parser to MTL suite:
- alarm_processor.py: alarm tag parsing, severity detection
- prefix_handler.py: target_id normalization, transmitter prefix normalization,
  valve target_id resolution, switch detection, motor prefix inference
- equipment_classifier.py: valve/motor/switch classification, VFD fault detection,
  analog input metadata resolution
- alarm_severity.py: severity code detection (HH/H/L/LL)
- description_formatter.py: proper case, scaling range stripping, 
  description enhancement with ISA measurement types
"""

import re

# =============================================================================
# ISA TAG PATTERNS
# =============================================================================

# Alarm Patterns (sorted by length for proper matching)
ALARM_PATTERNS = {
    # Pressure Alarms
    'PAHH': {'type': 'Pressure', 'description': 'High High Alarm', 'order': 1},
    'PAH': {'type': 'Pressure', 'description': 'High Alarm', 'order': 2},
    'PAL': {'type': 'Pressure', 'description': 'Low Alarm', 'order': 3},
    'PALL': {'type': 'Pressure', 'description': 'Low Low Alarm', 'order': 4},
    # Differential Pressure Alarms
    'PDAHH': {'type': 'Differential Pressure', 'description': 'High High Alarm', 'order': 1},
    'PDAH': {'type': 'Differential Pressure', 'description': 'High Alarm', 'order': 2},
    'PDAL': {'type': 'Differential Pressure', 'description': 'Low Alarm', 'order': 3},
    'PDALL': {'type': 'Differential Pressure', 'description': 'Low Low Alarm', 'order': 4},
    # Level Alarms
    'LAHH': {'type': 'Level', 'description': 'High High Alarm', 'order': 1},
    'LAH': {'type': 'Level', 'description': 'High Alarm', 'order': 2},
    'LAL': {'type': 'Level', 'description': 'Low Alarm', 'order': 3},
    'LALL': {'type': 'Level', 'description': 'Low Low Alarm', 'order': 4},
    # Interface Level Alarms
    'LXAHH': {'type': 'Interface Level', 'description': 'High High Alarm', 'order': 1},
    'LXAH': {'type': 'Interface Level', 'description': 'High Alarm', 'order': 2},
    'LXAL': {'type': 'Interface Level', 'description': 'Low Alarm', 'order': 3},
    'LXALL': {'type': 'Interface Level', 'description': 'Low Low Alarm', 'order': 4},
    # Temperature Alarms
    'TAHH': {'type': 'Temperature', 'description': 'High High Alarm', 'order': 1},
    'TAH': {'type': 'Temperature', 'description': 'High Alarm', 'order': 2},
    'TAL': {'type': 'Temperature', 'description': 'Low Alarm', 'order': 3},
    'TALL': {'type': 'Temperature', 'description': 'Low Low Alarm', 'order': 4},
    # Flow Alarms
    'FAHH': {'type': 'Flow', 'description': 'High High Alarm', 'order': 1},
    'FAH': {'type': 'Flow', 'description': 'High Alarm', 'order': 2},
    'FAL': {'type': 'Flow', 'description': 'Low Alarm', 'order': 3},
    'FALL': {'type': 'Flow', 'description': 'Low Low Alarm', 'order': 4},
    # Vibration Alarms
    'VAHH': {'type': 'Vibration', 'description': 'High High Alarm', 'order': 1},
    'VAH': {'type': 'Vibration', 'description': 'High Alarm', 'order': 2},
    'VAL': {'type': 'Vibration', 'description': 'Low Alarm', 'order': 3},
    'VALL': {'type': 'Vibration', 'description': 'Low Low Alarm', 'order': 4},
    # Analysis Alarms
    'AAHH': {'type': 'Analysis', 'description': 'High High Alarm', 'order': 1},
    'AAH': {'type': 'Analysis', 'description': 'High Alarm', 'order': 2},
    'AAL': {'type': 'Analysis', 'description': 'Low Alarm', 'order': 3},
    'AALL': {'type': 'Analysis', 'description': 'Low Low Alarm', 'order': 4},
}

# Switch Patterns
SWITCH_PATTERNS = {
    # Level Switches
    'LSHH': {'type': 'Level', 'description': 'Switch', 'order': 1},
    'LSH': {'type': 'Level', 'description': 'Switch', 'order': 2},
    'LSL': {'type': 'Level', 'description': 'Switch', 'order': 3},
    'LSLL': {'type': 'Level', 'description': 'Switch', 'order': 4},
    # Interface Level Switches
    'LXSHH': {'type': 'Interface Level', 'description': 'Switch', 'order': 1},
    'LXSH': {'type': 'Interface Level', 'description': 'Switch', 'order': 2},
    'LXSL': {'type': 'Interface Level', 'description': 'Switch', 'order': 3},
    'LXSLL': {'type': 'Interface Level', 'description': 'Switch', 'order': 4},
    # Pressure Switches
    'PSHH': {'type': 'Pressure', 'description': 'Switch', 'order': 1},
    'PSH': {'type': 'Pressure', 'description': 'Switch', 'order': 2},
    'PSL': {'type': 'Pressure', 'description': 'Switch', 'order': 3},
    'PSLL': {'type': 'Pressure', 'description': 'Switch', 'order': 4},
    # Differential Pressure Switches
    'PDSHH': {'type': 'Differential Pressure', 'description': 'Switch', 'order': 1},
    'PDSH': {'type': 'Differential Pressure', 'description': 'Switch', 'order': 2},
    'PDSL': {'type': 'Differential Pressure', 'description': 'Switch', 'order': 3},
    'PDSLL': {'type': 'Differential Pressure', 'description': 'Switch', 'order': 4},
    # Temperature Switches
    'TSHH': {'type': 'Temperature', 'description': 'Switch', 'order': 1},
    'TSH': {'type': 'Temperature', 'description': 'Switch', 'order': 2},
    'TSL': {'type': 'Temperature', 'description': 'Switch', 'order': 3},
    'TSLL': {'type': 'Temperature', 'description': 'Switch', 'order': 4},
    # Flow Switches
    'FSHH': {'type': 'Flow', 'description': 'Switch', 'order': 1},
    'FSH': {'type': 'Flow', 'description': 'Switch', 'order': 2},
    'FSL': {'type': 'Flow', 'description': 'Switch', 'order': 3},
    'FSLL': {'type': 'Flow', 'description': 'Switch', 'order': 4},
    # Vibration Switches
    'VSHH': {'type': 'Vibration', 'description': 'Switch', 'order': 1},
    'VSH': {'type': 'Vibration', 'description': 'Switch', 'order': 2},
    'VSL': {'type': 'Vibration', 'description': 'Switch', 'order': 3},
    'VSLL': {'type': 'Vibration', 'description': 'Switch', 'order': 4},
}

# Transmitter Patterns
TRANSMITTER_PATTERNS = {
    'PIT': 'Pressure',
    'LIT': 'Level',
    'LXIT': 'Interface Level',
    'TIT': 'Temperature',
    'FIT': 'Flow',
    'AT': 'Analysis',
    'AIT': 'Analysis',
    'DPIT': 'Differential Pressure',
    'PDIT': 'Differential Pressure',
    'VIT': 'Vibration',
    'DIT': 'Density',
}

# Controller Patterns
CONTROLLER_PATTERNS = {
    'PIC': 'Pressure',
    'LIC': 'Level',
    'LXIC': 'Interface Level',
    'TIC': 'Temperature',
    'FIC': 'Flow',
    'VIC': 'Vibration',
}

# Valve Patterns
VALVE_PATTERNS = {
    'PCV': 'Pressure Control Valve',
    'LCV': 'Level Control Valve',
    'LXCV': 'Interface Level Control Valve',
    'TCV': 'Temperature Control Valve',
    'FCV': 'Flow Control Valve',
    'PY': 'Pressure Control Valve',
    'LY': 'Level Control Valve',
    'LXY': 'Interface Level Control Valve',
    'TY': 'Temperature Control Valve',
    'FY': 'Flow Control Valve',
    'XV': 'Shutoff Valve',
    'PV': 'Pressure Valve',
    'LV': 'Level Valve',
    'TV': 'Temperature Valve',
    'FV': 'Flow Valve',
}

# Valve Position Switch Patterns (from equipment_classifier.py)
VALVE_SWITCH_PATTERNS = {
    'ZSO': 'Open Switch Status',
    'ZSC': 'Closed Switch Status',
    'ZIO': 'Open Switch Status',
    'ZIC': 'Closed Switch Status',
    'XSO': 'Open Switch Status',
    'XSC': 'Closed Switch Status',
    'XIO': 'Open Switch Status',
    'XIC': 'Closed Switch Status',
}

# =============================================================================
# INSTRUMENT INITIATING VARIABLES (from L5K config.py)
# =============================================================================
INSTRUMENT_INITIATING_VARIABLES = {
    'P': ['Pressure', 'Press'],
    'F': ['Flow'],
    'V': ['Vibration', 'Vibe'],
    'T': ['Temperature', 'Temp'],
    'L': ['Level'],
    'DP': ['Differential Pressure', 'dP', 'Diff Press', 'Diff Pressure'],
    'PD': ['Differential Pressure', 'dP', 'Diff Press', 'Diff Pressure'],
    'A': ['Analysis'],
}

# =============================================================================
# MOTOR / EQUIPMENT DETECTION (from equipment_classifier.py)
# =============================================================================
RUN_STATUS_TRIGGERS = ["Run Status", "RUN_STATUS", "AUX", "Running Indication",
                       "RUNNING", "XI", "MOTOR_RUNNING"]
AUTO_STATUS_TRIGGERS = ["Auto Status", "AUTO_STATUS", "AUTO", "HOA", "HS"]
RUN_COMMAND_TRIGGERS = ["Run Command", "RUN_COMMAND", "Output", "Relay",
                        "START", "XS", "XC", "CR", "MOTOR_RUN_BIT"]

MOTOR_EQUIPMENT_WORDS = ['PUMP', 'FAN', 'COMPRESSOR', 'MOTOR', 'BLOWER']

# Motor prefix inference (from prefix_handler.py infer_motor_prefix_from_descriptions)
MOTOR_KEYWORD_TO_PREFIX = {
    'COMPRESSOR': 'K',
    'PUMP': 'P',
    'FAN': 'E',
    'BLOWER': 'B',
    'MOTOR': 'M',
}

# Motor role suffixes to strip from target_id (from equipment_classifier.py)
MOTOR_ROLE_SUFFIXES = [
    "-RUN-STATUS", "-RUNNING-INDICATION", "-RUNNING",
    "-AUTO-STATUS", "-AUTO",
    "-RUN-COMMAND", "-OUTPUT", "-RELAY", "-START",
]

# Words to preserve as uppercase (from description_formatter.py)
PRESERVE_CAPS_WORDS = {
    "ESD", "PLC", "BOP", "IR", "UV", "VFD", "LEL", "MPR", "HOA", "JOA", "SD", "TEG"
}

# =============================================================================
# ALARM TO TRANSMITTER CONVERSION (from prefix_handler.py)
# =============================================================================
ALARM_TO_TRANSMITTER = {
    'P': 'PIT', 'T': 'TIT', 'L': 'LIT', 'F': 'FIT',
    'A': 'AIT', 'D': 'DIT', 'V': 'VIT',
}

# Two-letter transmitter prefix normalization (from prefix_handler.py normalize_transmitter_prefix)
# PT->PIT, LT->LIT, TT->TIT, FT->FIT, VT->VIT, PI->PIT, LI->LIT, etc.
TWO_LETTER_TRANSMITTER_PREFIXES = {
    'PT': 'PIT', 'PI': 'PIT',
    'LT': 'LIT', 'LI': 'LIT',
    'TT': 'TIT', 'TI': 'TIT',
    'FT': 'FIT', 'FI': 'FIT',
    'VT': 'VIT', 'VI': 'VIT',
    'AT': 'AIT',
    'DT': 'DIT',
}

# Valve Y->V normalization (from prefix_handler.py resolve_valve_target_id)
VALVE_Y_TO_V = {
    'LY': 'LV', 'PY': 'PV', 'TY': 'TV', 'FY': 'FV', 'XY': 'XV',
    'LXY': 'LXV',
}

# ZSO/ZSC/ZIO/ZIC -> XV fallback (from prefix_handler.py)
VALVE_SWITCH_TO_XV = {'ZSO', 'ZSC', 'ZIO', 'ZIC', 'XSO', 'XSC', 'XIO', 'XIC'}

# =============================================================================
# ABBREVIATION EXPANSION
# =============================================================================

ABBREVIATIONS = {
    r'\bDISC\b': 'Discharge',
    r'\bSUCT\b': 'Suction',
    r'\bRETURN\b': 'Return',
    r'\bRECYCLE\b': 'Recycle',
    r'\bINLET\b': 'Inlet',
    r'\bOUTLET\b': 'Outlet',
    r'\bLP\b': 'Low Pressure',
    r'\bHP\b': 'High Pressure',
    r'\bMP\b': 'Medium Pressure',
    r'\bXMTR\b': 'Transmitter',
    r'\bXDUCER\b': 'Transducer',
    r'\bINDIC\b': 'Indication',
    r'\bCTRL\b': 'Control',
    r'\bSIG\b': 'Signal',
    r'\bSEP\b': 'Separator',
    r'\bSEPERATOR\b': 'Separator',
    r'\bVESS\b': 'Vessel',
    r'\bTNK\b': 'Tank',
    r'\bPMP\b': 'Pump',
    r'\bPMPS\b': 'Pumps',
    r'\bVLV\b': 'Valve',
    r'\bVLVS\b': 'Valves',
    r'\bWTR\b': 'Water',
    r'\bWW\b': 'Waste Water',
    r'\bINTERF\b': 'Interface',
    r'\bOVERALL\b': 'Overall',
    r'\bMANU\b': 'Manual',
    r'\bLVL\b': 'Level',
    r'\bTEMP\b': 'Temperature',
    r'\bPRESS\b': 'Pressure',
    r'\bFLOW\b': 'Flow',
    r'\bNORM\b': 'Normal',
    r'\bEMERG\b': 'Emergency',
    r'\bSTDBY\b': 'Standby',
    r'\bALM\b': 'Alarm',
    r'\bSHUT\b': 'Shutdown',
    r'\bOPER\b': 'Operation',
    r'\bCOMMON\b': 'Common',
    r'\bPRI\b': 'Primary',
    r'\bSEC\b': 'Secondary',
    r'\bAUX\b': 'Auxiliary',
    r'\bComp\b': 'Compressor',
}

# =============================================================================
# ACRONYMS TO PRESERVE (DO NOT EXPAND)
# =============================================================================

PRESERVED_ACRONYMS = [
    'PIT', 'LIT', 'TIT', 'FIT', 'LXIT', 'VIT', 'AIT', 'DPIT', 'PDIT',
    'PIC', 'LIC', 'TIC', 'FIC', 'LXIC',
    'PY', 'LY', 'TY', 'FY', 'LXY',
    'PCV', 'LCV', 'TCV', 'FCV',
    'IO', 'ID', 'PLC', 'VFD', 'PID', 'VSD',
    'HMI', 'SCADA', 'RTU',
    'AI', 'AO', 'DI', 'DO',
    'API', 'ANSI', 'ISA',
    'Hz', 'kW', 'MW', 'GW',
    'PSI', 'PSIG', 'PSIA', 'BARG', 'BARA',
    'BBL', 'BBLS', 'MCF', 'MCFD', 'MMCFD', 'MSCF', 'MSCFD',
    'GPM', 'BPD', 'ACFM',
    'AC', 'DC', 'ESD', 'BOP', 'IR', 'UV', 'LEL', 'MPR', 'HOA', 'TEG',
]

# =============================================================================
# CLASSIFICATION KEYWORDS
# =============================================================================

CLASSIFICATION_KEYWORDS = {
    'spare': ['SPARE', 'UNUSED', 'RESERVED'],
    'indication': ['SPEED', 'CURRENT', 'VOLTAGE', 'FREQUENCY', 'Hz', 'AMP', 'AMPS'],
    'control_signal': ['CTRL', 'CONTROL SIGNAL'],
    'selection': ['SELECTION', 'SELECT', 'MODE', 'CHOOSE'],
    'display': ['DISPLAY', 'TEXT', 'MESSAGE', 'SHOW'],
    'vfd_fault': ['VFD FAULT', 'VSD FAULT', 'VFD FAIL', 'VSD FAIL'],
    'transmitter_fail': ['TRANSMITTER FAIL', 'XMTR FAIL', 'TRANSMITTER FAULT'],
    'permissive': ['PERMISSIVE'],
}

# =============================================================================
# SPECIAL PATTERNS
# =============================================================================

DAY_VOLUME_PATTERNS = {
    'DAY0': 'Day 0 Volume',
    'DAY1': 'Day 1 Volume',
}

TRANSMITTER_PREFIXES = [
    'PDIT', 'DPIT',
    'LXIT', 'LXI',
    'PIT', 'PI',
    'FIT', 'FI',
    'TIT', 'TI',
    'LIT', 'LI',
    'VIT', 'VI',
    'AIT',
    'AT',
    'FCU',
    'TE',
]

# =============================================================================
# VALID TARGET NAME DESCRIPTIONS (MASTER TAG LIST)
# Enhanced with additional classifications from L5K parser
# =============================================================================

VALID_TARGET_NAMES = [
    # Alarms
    'High High Alarm',
    'High Alarm',
    'Low Alarm',
    'Low Low Alarm',
    'Alarm',
    # Process Values
    'Process Value',
    'Rate',                    # Flow meters (from equipment_classifier.py)
    'Analog Input',
    'Digital Input',
    'Input',
    # Volumes (DAY0/DAY1)
    'Day 0 Volume',
    'Day 1 Volume',
    # Control
    'Control Signal',
    'Control Output',
    'Analog Output',
    'Digital Output',
    'Output Command',          # Valve/motor output (from equipment_classifier.py)
    # Setpoints
    'High High Alarm Setpoint',
    'High Alarm Setpoint',
    'Low Alarm Setpoint',
    'Low Low Alarm Setpoint',
    'Setpoint',
    'Process Value Setpoint',
    'Control Setpoint',
    'PV Min',                  # Scaling (from mtl_analog_scaling_builder.py)
    'PV Max',
    # Switches
    'Switch',
    'High Switch',
    'Low Switch',
    # Valve specifics (from equipment_classifier.py)
    'Control Valve',
    'Pressure Control Valve',
    'Level Control Valve',
    'Temperature Control Valve',
    'Flow Control Valve',
    'Interface Level Control Valve',
    'Open Switch Status',      # ZSO valve (from equipment_classifier.py)
    'Closed Switch Status',    # ZSC valve
    'Switch Status',
    'Shutoff Valve',
    # Motor specifics (from equipment_classifier.py)
    'Run Status',
    'Run Command',
    'Auto Status',
    'VFD Fault Status',        # (from equipment_classifier.py)
    # Status/Indication
    'Status',
    'Indication',
    'Running Status',
    'Fault Status',
    'Hand/Off/Auto Status',
    'Permissive Status',
    # Alarm Delay (from alarm_processor.py)
    'High High Alarm Delay',
    'High Alarm Delay',
    'Low Alarm Delay',
    'Low Low Alarm Delay',
    'Alarm Delay',
    # PID tags (from pid_tag_tracer.py)
    'PID Setpoint',
    'PID Process Variable',
    'PID Control Variable',
    'PID Output',
    'PID Manual Output',
    'PID Auto/Manual Mode',
    # Selection/Mode
    'Selection',
    'Mode',
    # Transmitter Fail
    'Transmitter Fail',
    # Other
    'Spare',
    'Display',
    'UNCLASSIFIED',
]

# =============================================================================
# IO ADDRESS SUFFIXES
# =============================================================================

IO_SUFFIXES = ['!RD', '!WR', '!SC']

# =============================================================================
# PLC ARRAY PATTERNS
# =============================================================================

PLC_ARRAY_PATTERNS = [
    'ALARM', 'WRITEFLOAT', 'READFLOAT', 'EXTER_READFLOAT',
    'INTEGER', 'BIT', 'RACK00_SLOT', 'DataAcquisitionRead', 'MSG_',
]

# =============================================================================
# I/O MODULE CATALOG NUMBERS (from L5K config.py)
# =============================================================================

ANALOG_INPUT_MODULES = [
    "1756-IF16", "1756-IF8", "1756-IF6I", "1756-IF8H",
    "1756-IF6CIS", "1756-IF8I", "1756-IR6I", "1756-IR12",
]
ANALOG_OUTPUT_MODULES = [
    "1756-OF8", "1756-OF4", "1756-OF8H", "1756-OF8I",
    "1756-OF6CI", "1756-OF6VI",
]
DISCRETE_INPUT_MODULES = [
    "1756-IB16", "1756-IB32", "1756-IC16", "1756-IB16D",
    "1756-IB16I", "1756-IH16I", "1756-IA16", "1756-IA8D",
]
DISCRETE_OUTPUT_MODULES = [
    "1756-OB16I", "1756-OB16E", "1756-OB32", "1756-OB16D",
    "1756-OB8", "1756-OB8EI", "1756-OA16", "1756-OA8",
]
THERMOCOUPLE_MODULES = [
    "1756-IT6I", "1756-IT6I2",
]

# =============================================================================
# SCALING RANGE PATTERN (from description_formatter.py strip_scaling_range)
# =============================================================================

SCALING_UNITS = [
    'PSIG', 'PSIA', 'PSI', 'BARG', 'BARA',
    'DEGF', 'DEGC',
    'GPM', 'BPD', 'MCF', 'MCFD', 'MSCF', 'MSCFD', 'BBLS', 'ACFM',
    'MA', 'VDC', 'VAC', 'HZ',
    'IN', 'IN WC', '"WC',
    '%',
]

# Global bits to ignore as equipment (from L5K config.py)
NON_EQUIP_GLOBALS = {
    "ACKNOWLEDGE", "RESET", "FIRST_OUT", "ACK",
    "NO_FIRST_OUT_FOUND", "SHUTDOWN_FLAG", "ALARM_FLAG"
}