"""
ISA Patterns, Abbreviations, and Classification Constants.

Used primarily by Step 3 (MTL conversion) for tag classification.
"""

# =============================================================================
# ALARM PATTERNS  {pattern: {type, description, order}}
# =============================================================================
ALARM_PATTERNS = {
    # Pressure
    'PAHH': {'type': 'Pressure', 'description': 'High High Alarm', 'order': 1},
    'PAH':  {'type': 'Pressure', 'description': 'High Alarm', 'order': 2},
    'PAL':  {'type': 'Pressure', 'description': 'Low Alarm', 'order': 3},
    'PALL': {'type': 'Pressure', 'description': 'Low Low Alarm', 'order': 4},
    # Level
    'LAHH': {'type': 'Level', 'description': 'High High Alarm', 'order': 1},
    'LAH':  {'type': 'Level', 'description': 'High Alarm', 'order': 2},
    'LAL':  {'type': 'Level', 'description': 'Low Alarm', 'order': 3},
    'LALL': {'type': 'Level', 'description': 'Low Low Alarm', 'order': 4},
    # Interface Level
    'LXAHH': {'type': 'Interface Level', 'description': 'High High Alarm', 'order': 1},
    'LXAH':  {'type': 'Interface Level', 'description': 'High Alarm', 'order': 2},
    'LXAL':  {'type': 'Interface Level', 'description': 'Low Alarm', 'order': 3},
    'LXALL': {'type': 'Interface Level', 'description': 'Low Low Alarm', 'order': 4},
    # Temperature
    'TAHH': {'type': 'Temperature', 'description': 'High High Alarm', 'order': 1},
    'TAH':  {'type': 'Temperature', 'description': 'High Alarm', 'order': 2},
    'TAL':  {'type': 'Temperature', 'description': 'Low Alarm', 'order': 3},
    'TALL': {'type': 'Temperature', 'description': 'Low Low Alarm', 'order': 4},
    # Flow
    'FAHH': {'type': 'Flow', 'description': 'High High Alarm', 'order': 1},
    'FAH':  {'type': 'Flow', 'description': 'High Alarm', 'order': 2},
    'FAL':  {'type': 'Flow', 'description': 'Low Alarm', 'order': 3},
    'FALL': {'type': 'Flow', 'description': 'Low Low Alarm', 'order': 4},
}

# =============================================================================
# SWITCH PATTERNS
# =============================================================================
SWITCH_PATTERNS = {
    # Level
    'LSHH': {'type': 'Level', 'description': 'Switch', 'order': 1},
    'LSH':  {'type': 'Level', 'description': 'Switch', 'order': 2},
    'LSL':  {'type': 'Level', 'description': 'Switch', 'order': 3},
    'LSLL': {'type': 'Level', 'description': 'Switch', 'order': 4},
    # Interface Level
    'LXSHH': {'type': 'Interface Level', 'description': 'Switch', 'order': 1},
    'LXSH':  {'type': 'Interface Level', 'description': 'Switch', 'order': 2},
    'LXSL':  {'type': 'Interface Level', 'description': 'Switch', 'order': 3},
    'LXSLL': {'type': 'Interface Level', 'description': 'Switch', 'order': 4},
    # Pressure
    'PSHH': {'type': 'Pressure', 'description': 'Switch', 'order': 1},
    'PSH':  {'type': 'Pressure', 'description': 'Switch', 'order': 2},
    'PSL':  {'type': 'Pressure', 'description': 'Switch', 'order': 3},
    'PSLL': {'type': 'Pressure', 'description': 'Switch', 'order': 4},
    # Temperature
    'TSHH': {'type': 'Temperature', 'description': 'Switch', 'order': 1},
    'TSH':  {'type': 'Temperature', 'description': 'Switch', 'order': 2},
    'TSL':  {'type': 'Temperature', 'description': 'Switch', 'order': 3},
    'TSLL': {'type': 'Temperature', 'description': 'Switch', 'order': 4},
}

# =============================================================================
# TRANSMITTER / CONTROLLER / VALVE PATTERNS
# =============================================================================
TRANSMITTER_PATTERNS = {
    'PIT': 'Pressure', 'LIT': 'Level', 'LXIT': 'Interface Level',
    'TIT': 'Temperature', 'FIT': 'Flow', 'AT': 'Analysis',
    'DPIT': 'Differential Pressure',
}

CONTROLLER_PATTERNS = {
    'PIC': 'Pressure', 'LIC': 'Level', 'LXIC': 'Interface Level',
    'TIC': 'Temperature', 'FIC': 'Flow',
}

VALVE_PATTERNS = {
    'PY': 'Pressure Control Valve', 'LY': 'Level Control Valve',
    'LXY': 'Interface Level Control Valve', 'TY': 'Temperature Control Valve',
    'FY': 'Flow Control Valve',
}

# =============================================================================
# TRANSMITTER PREFIXES (for tag extraction from descriptions)
# =============================================================================
TRANSMITTER_PREFIXES = [
    'PIT', 'PI', 'FIT', 'FI', 'TIT', 'TI', 'LIT', 'LI',
    'LXIT', 'LXI', 'AT', 'AI', 'DPIT', 'DPI', 'FCU', 'TE', 'P',
]

# =============================================================================
# ABBREVIATION EXPANSION  {regex: replacement}
# =============================================================================
ABBREVIATIONS = {
    # Equipment
    r'\bSEP\b': 'Separator', r'\bSEPERATOR\b': 'Separator',
    r'\bVESS\b': 'Vessel', r'\bTNK\b': 'Tank',
    r'\bPMP\b': 'Pump', r'\bPMPS\b': 'Pumps',
    r'\bVLV\b': 'Valve', r'\bVLVS\b': 'Valves',
    # Process
    r'\bDISC\b': 'Discharge', r'\bSUCT\b': 'Suction',
    r'\bINLET\b': 'Inlet', r'\bOUTLET\b': 'Outlet',
    r'\bRETURN\b': 'Return', r'\bRECYCLE\b': 'Recycle',
    # Pressure
    r'\bLP\b': 'Low Pressure', r'\bHP\b': 'High Pressure',
    r'\bMP\b': 'Medium Pressure',
    # Instrumentation
    r'\bXMTR\b': 'Transmitter', r'\bXDUCER\b': 'Transducer',
    r'\bINDIC\b': 'Indication', r'\bCTRL\b': 'Control',
    r'\bSIG\b': 'Signal', r'\bSP\b': 'Setpoint',
    # Measurement
    r'\bLVL\b': 'Level', r'\bTEMP\b': 'Temperature',
    r'\bPRESS\b': 'Pressure', r'\bFLOW\b': 'Flow',
    # Fluids
    r'\bWTR\b': 'Water', r'\bWW\b': 'Waste Water',
    # Conditions
    r'\bNORM\b': 'Normal', r'\bEMERG\b': 'Emergency',
    r'\bSTDBY\b': 'Standby',
    # Types
    r'\bINTERF\b': 'Interface', r'\bOVER-ALL\b': 'Overall',
    r'\bOVERALL\b': 'Overall', r'\bMANU\b': 'Manual',
    r'\bAUTO\b': 'Automatic',
    # Other
    r'\bALM\b': 'Alarm', r'\bSHUT\b': 'Shutdown',
    r'\bSTART\b': 'Startup', r'\bOPER\b': 'Operation',
    r'\bCOMMON\b': 'Common', r'\bPRI\b': 'Primary',
    r'\bSEC\b': 'Secondary', r'\bAUX\b': 'Auxiliary',
}

# =============================================================================
# ACRONYMS TO PRESERVE (not expanded by capitalize_proper)
# =============================================================================
PRESERVED_ACRONYMS = [
    # ISA Tags
    'PIT', 'LIT', 'TIT', 'FIT', 'LXIT',
    'PIC', 'LIC', 'TIC', 'FIC', 'LXIC',
    'PY', 'LY', 'TY', 'FY', 'LXY',
    # Systems
    'IO', 'ID', 'PLC', 'VFD', 'PID', 'HMI', 'SCADA', 'RTU',
    'AI', 'AO', 'DI', 'DO',
    # Standards
    'API', 'ANSI', 'ISA', 'BS&W',
    # Units
    'Hz', 'kW', 'MW', 'GW',
    'PSI', 'PSIG', 'PSIA', 'BARG', 'BARA',
    'BBL', 'BBLS', 'MCF', 'MCFD', 'MMCFD', 'GPM', 'BPD',
    # Electrical
    'AC', 'DC', 'USB', 'CPU', 'RAM', 'ROM',
]

# =============================================================================
# CLASSIFICATION KEYWORDS (fallback when ISA pattern doesn't match)
# =============================================================================
CLASSIFICATION_KEYWORDS = {
    'spare': ['SPARE', 'UNUSED', 'RESERVED'],
    'indication': ['SPEED', 'CURRENT', 'VOLTAGE', 'FREQUENCY', 'Hz', 'AMP', 'AMPS'],
    'control_signal': ['CTRL', 'CONTROL', 'SIGNAL', 'OUTPUT'],
    'selection': ['SELECTION', 'SELECT', 'MODE', 'CHOOSE'],
    'display': ['DISPLAY', 'TEXT', 'MESSAGE', 'SHOW'],
}

# =============================================================================
# VALID TARGET NAME DESCRIPTIONS (for the MTL output)
# =============================================================================
VALID_TARGET_NAMES = [
    # Alarms
    'Alarm', 'High Alarm', 'High High Alarm', 'Low Alarm', 'Low Low Alarm',
    # Alarm Setpoints
    'High Alarm Setpoint', 'High High Alarm Setpoint',
    'Low Alarm Setpoint', 'Low Low Alarm Setpoint',
    # Alarm Related
    'Alarm Delay', 'High Alarm Delay', 'Alarm Reset', 'Fail to Open Alarm',
    # Process Values
    'Process Value', 'Process Variable', 'Input',
    'Analog Input', 'Digital Input', 'Analog Output', 'Digital Output',
    # Control
    'Control Signal', 'Control Output', 'Control Variable',
    'Setpoint', 'Manual Output', 'Process Value Setpoint', 'Control Setpoint',
    # PID Parameters
    'Proportional', 'Integral', 'Derivative', 'Maximum CV', 'Minimum CV',
    # Flow / Volume
    'Rate', 'Rate Day 0 Average', 'Day 0 Volume', 'Day 1 Volume',
    'Current Volume', 'Volume at Midnight', 'Day 0 Inventory Change', 'Preset Volume',
    # Pump / Motor
    'Run Status', 'Run Command', 'Run Fail', 'Auto Status', 'Auto/Manual Mode',
    'Hand/Off/Auto Status', 'Motor Current', 'Speed Feedback', 'VFD Fail', 'Runtime',
    # Pump Setpoints
    'Start Setpoint', 'Stop Setpoint', 'Start Command', 'Stop Command',
    'Lead Start Setpoint', 'Lead Stop Setpoint',
    'Lag Start Setpoint', 'Lag Stop Setpoint',
    'Lag1 Start Setpoint', 'Lag1 Stop Setpoint',
    'Lag2 Start Setpoint', 'Lag2 Stop Setpoint',
    'Lag3 Start Setpoint', 'Lag3 Stop Setpoint',
    'Level Start Setpoint', 'Level Stop Setpoint', 'Load Start Setpoint',
    # Lead/Lag
    'Lead/Lag Status', 'Lead Lag Status',
    # Valve
    'Control Valve', 'Pressure Control Valve', 'Level Control Valve',
    'Temperature Control Valve', 'Flow Control Valve', 'Interface Level Control Valve',
    'Open Switch Status', 'Closed Switch Status',
    'Open Setpoint', 'Close Setpoint',
    'Output Command', 'Solenoid Output Command',
    # Switches
    'Switch', 'High Switch', 'Low Switch',
    # Status / Indication
    'Status', 'Indication', 'Running Status', 'Fault Status',
    'Permissive Status',
    # Selection / State
    'Selection', 'Mode', 'State', 'Selected Tank', 'Unit Loaded',
    # Site / System
    'Beacon Status', 'Site ESD Status', 'Site Well Shutdown Active',
    'Power Fail', 'UPS Fail', 'Meter Fail', 'Sampler Fail', 'Sample Rate Setpoint',
    # Measurement Types
    'Temperature', 'Differential Pressure', 'Display',
    # Other
    'Spare', 'Unclassified', 'UNCLASSIFIED',
]

# =============================================================================
# IO ADDRESS SUFFIXES (to strip when cleaning addresses)
# =============================================================================
IO_SUFFIXES = ['!RD', '!WR', '!SC', '!BI', '!BO', '!AI', '!AO', '!DI', '!DO']

# =============================================================================
# DAY VOLUME PATTERNS
# =============================================================================
DAY_VOLUME_PATTERNS = {
    'DAY0': 'Day 0 Volume',
    'DAY1': 'Day 1 Volume',
}
