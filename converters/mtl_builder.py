"""
MTL Builder — Convert enriched IO rows into Master Tag List format.

Contains:
  - process_io_to_mtl(): Convert a single IO row to MTL entry
  - convert_to_mtl(): Process entire DataFrame and save output
"""

import re
import os
import pandas as pd
from collections import defaultdict

from config import OUTPUT_DIR, ENRICHED_PATH, FINAL_MTL_PATH
from converters.text_processor import capitalize_proper
from converters.tag_classifier import (
    clean_tag_prefix, extract_plc_suffix, extract_plc_base,
    classify_by_plc_suffix, classify_writefloat_setpoint,
    detect_flow_rate, get_default_states, get_default_scaling,
    identify_tag_type, extract_tag_id_from_description,
    classify_by_pattern, validate_target_name,
    detect_day_volume, extract_volume_unit_from_description,
    normalize_unit_lowercase, extract_transmitter_id,
    extract_alarm_switch_tag, is_alarm_address,
    detect_setpoint_type, is_writefloat_address,
    convert_alarm_tag_to_transmitter, get_alarm_tnd_from_level,
    detect_hoa_pattern, detect_permissive_pattern,
    classify_from_tag_id, extract_alarm_level_from_description,
    extract_alarm_level_from_keywords, clean_alarm_description,
    extract_tag_from_alarm_description,
    IO_SUFFIXES, PLC_SUFFIX_TO_TND, DEFAULT_STATES, DEFAULT_SCALING,
)


def process_io_to_mtl(row):
    """
    Process a single IO row to MTL format.
    """
    original_tag = row['IO Address']
    description = row['Description']
    
    # GET RACK DATA
    rack_target_id = row.get('target_id_rack', '')
    rack_units = row.get('target_units', '')
    rack_description = row.get('rack_description', '')
    
    # Handle NaN
    if pd.isna(description):
        description = ""
    if pd.isna(rack_target_id):
        rack_target_id = ""
    if pd.isna(rack_units):
        rack_units = ""
    if pd.isna(rack_description):
        rack_description = ""
    
    # Check address types
    is_alarm = is_alarm_address(original_tag)
    is_writefloat = is_writefloat_address(original_tag)
    
    # PLC suffix classification (highest priority)
    plc_suffix_tnd = classify_by_plc_suffix(original_tag)
    
    # WRITEFLOAT setpoint classification
    writefloat_tnd = None
    if is_writefloat:
        writefloat_tnd = classify_writefloat_setpoint(original_tag, description)
    
    # Day volume detection
    day_volume = detect_day_volume(original_tag, description)
    
    # Flow Rate detection
    is_flow_rate = detect_flow_rate(description)
    
    # Extract volume unit
    final_units = rack_units
    if not final_units:
        volume_unit = extract_volume_unit_from_description(description)
        if volume_unit:
            final_units = volume_unit
    
    final_units = normalize_unit_lowercase(final_units)
    
    # Determine tag_id
    tag_id = None
    equipment = description
    alarm_level_from_tag = None
    
    if rack_target_id:
        tag_id = rack_target_id
        equipment = rack_description if rack_description else description
    else:
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
    
    # If still no tag_id, generate from address
    if not tag_id:
        array_match = re.search(r'([A-Z_]+)\[(\d+)\]', original_tag)
        if array_match:
            base = array_match.group(1)
            index = array_match.group(2)
            tag_id = f"{base}-{index}"
        else:
            tag_match = re.search(r'([A-Z]+)[-_](\d+)', original_tag)
            if tag_match:
                prefix = tag_match.group(1)
                number = tag_match.group(2)
                tag_id = f"{prefix}-{number}"
            else:
                tag_id = original_tag
                for suffix in IO_SUFFIXES:
                    if tag_id.endswith(suffix):
                        tag_id = tag_id[:-len(suffix)]
    
    # CLEAN TAG PREFIX - Remove "1:" or similar
    tag_id = clean_tag_prefix(tag_id)
    
    # Convert alarm tag to transmitter
    converted_tag, alarm_level_from_tag, is_switch = convert_alarm_tag_to_transmitter(tag_id)
    if converted_tag != tag_id:
        tag_id = converted_tag
    
    if not alarm_level_from_tag:
        alarm_level_from_tag, is_switch = extract_alarm_level_from_description(description)
    
    if not alarm_level_from_tag:
        alarm_level_from_tag, is_switch = extract_alarm_level_from_keywords(description)
    
    has_setpoint = bool(re.search(r'set\s*point|setpoint', str(description), re.IGNORECASE))
    
    # Determine target_name_description
    target_name = None
    
    # Priority 1: PLC suffix (100% confidence)
    if plc_suffix_tnd:
        target_name = plc_suffix_tnd
    # Priority 2: Day volume
    elif day_volume:
        target_name = day_volume
    # Priority 3: Flow Rate
    elif is_flow_rate:
        target_name = "Rate"
    # Priority 4: WRITEFLOAT setpoint with Lead/Lag/Start/Stop
    elif writefloat_tnd:
        target_name = writefloat_tnd
    # Priority 5: Permissive pattern
    elif detect_permissive_pattern(description):
        target_name = "Permissive Status"
    # Priority 6: Alarm level from tag
    elif alarm_level_from_tag:
        target_name = get_alarm_tnd_from_level(alarm_level_from_tag, has_setpoint, is_switch, original_tag)
    # Priority 7: Setpoint type from description
    elif 'SETPOINT' in str(description).upper() or 'SET POINT' in str(description).upper():
        setpoint_type = detect_setpoint_type(description)
        if setpoint_type:
            target_name = setpoint_type
        else:
            target_name = 'Setpoint'
    # Priority 8: ALARM address
    elif is_alarm:
        target_name = "Alarm"
    # Priority 9: ISA pattern classification
    else:
        classification = classify_by_pattern(original_tag, description)
        if classification:
            target_name = classification['description']
        else:
            target_name = identify_tag_type(description)
    
    # Validate target_name
    target_name_validated = validate_target_name(target_name)
    
    # Fallback: classify from tag_id
    if target_name_validated in ['UNCLASSIFIED', 'Spare'] and tag_id:
        tnd_from_tag, is_switch_from_tag = classify_from_tag_id(tag_id, original_tag)
        if tnd_from_tag:
            target_name_validated = tnd_from_tag
            if is_switch_from_tag:
                is_switch = is_switch_from_tag
    
    # Clean equipment description
    if alarm_level_from_tag:
        equipment = clean_alarm_description(equipment, alarm_level_from_tag, has_setpoint)
    
    equipment_final = capitalize_proper(equipment) if equipment else ""
    
    # Get classification for sort order
    classification = classify_by_pattern(original_tag, description)
    
    # Get default states and scaling
    default_states = get_default_states(target_name_validated, tag_id)
    default_scaling = get_default_scaling(target_name_validated)
    
    # Build MTL entry
    mtl_entry = {
        'target_id': tag_id,
        'target_units': final_units,
        'equipment_description': equipment_final,
        'target_name_description': target_name_validated,
        'target_scaling': default_scaling,
        'states': default_states,
        'iconics_plc_path': original_tag,
        'target_description': capitalize_proper(description) if description else "",
        'description_source': row.get('Description Source', 'Unknown'),
        'screens': row.get('Screens', ''),
        'sort_order': classification['order'] if classification else 999,
    }
    
    return mtl_entry


def convert_to_mtl(input_path, output_path):
    """Main conversion function"""
    print("="*80)
    print("STEP 3: CONVERT TO MTL (MERGED VERSION v2)")
    print("="*80)
    
    print(f"\nLoading enriched IOs: {input_path}")
    df = pd.read_excel(input_path)
    print(f"  -> Loaded {len(df)} IOs")
    
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
    
    print("\nConverting IOs to MTL format...")
    
    mtl_entries = []
    classification_stats = defaultdict(int)
    units_filled = 0
    units_from_description = 0
    day_volume_count = 0
    states_filled = 0
    scaling_filled = 0
    
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
        
        if mtl_entry['states']:
            states_filled += 1
        if mtl_entry['target_scaling']:
            scaling_filled += 1
    
    df_mtl = pd.DataFrame(mtl_entries)
    
    df_mtl = df_mtl.sort_values(['target_id', 'sort_order'])
    df_mtl = df_mtl.drop('sort_order', axis=1)

    # Insert 'delete' column between G (iconics_plc_path) and H (target_description)
    insert_pos = df_mtl.columns.get_loc('target_description')
    df_mtl.insert(insert_pos, 'delete', '')

    print(f"\nSaving MTL: {output_path}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_mtl.to_excel(writer, sheet_name='MASTER TAG LIST', index=False)
        
        worksheet = writer.sheets['MASTER TAG LIST']

        # Column widths — H agora é 'delete', I em diante deslocadas
        worksheet.column_dimensions['A'].width = 15
        worksheet.column_dimensions['B'].width = 12
        worksheet.column_dimensions['C'].width = 50
        worksheet.column_dimensions['D'].width = 30
        worksheet.column_dimensions['E'].width = 25
        worksheet.column_dimensions['F'].width = 30
        worksheet.column_dimensions['G'].width = 35
        worksheet.column_dimensions['H'].width = 12   # delete
        worksheet.column_dimensions['I'].width = 60   # target_description
        worksheet.column_dimensions['J'].width = 20   # description_source
        worksheet.column_dimensions['K'].width = 80   # screens

        # Auto-filter no cabeçalho
        worksheet.auto_filter.ref = worksheet.dimensions

        # Freeze primeira linha
        worksheet.freeze_panes = 'A2'

    print(f"  -> Saved: {output_path}")
    
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    
    print(f"Total entries: {len(df_mtl)}")
    
    print(f"\nUnits filled:")
    print(f"  -> Total with target_units: {units_filled} ({units_filled/len(df_mtl)*100:.1f}%)")
    print(f"  -> From RACK screens: {units_filled - units_from_description}")
    print(f"  -> From description: {units_from_description}")
    
    print(f"\nDay Volume detection:")
    print(f"  -> Day 0/Day 1 Volume entries: {day_volume_count}")
    
    print(f"\nAuto-filled fields:")
    print(f"  -> States filled: {states_filled} ({states_filled/len(df_mtl)*100:.1f}%)")
    print(f"  -> Scaling filled: {scaling_filled} ({scaling_filled/len(df_mtl)*100:.1f}%)")
    
    unclassified_count = len(df_mtl[df_mtl['target_name_description'] == 'UNCLASSIFIED'])
    if unclassified_count > 0:
        print(f"\n⚠️  UNCLASSIFIED entries: {unclassified_count} ({unclassified_count/len(df_mtl)*100:.1f}%)")
    
    print("\nClassification breakdown:")
    for category, count in sorted(classification_stats.items(), key=lambda x: -x[1]):
        percentage = (count / len(df_mtl) * 100) if len(df_mtl) > 0 else 0
        prefix = "⚠️ " if category == "UNCLASSIFIED" else "  "
        print(f"{prefix}- {category}: {count} ({percentage:.1f}%)")


def main():
    print("\n" + "="*80)
    print("ICONICS MTL CONVERTER - MERGED VERSION v2")
    print("="*80)
    
    if not os.path.exists(ENRICHED_PATH):
        print(f"ERROR: {ENRICHED_PATH} not found. Run step2 first.")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    convert_to_mtl(ENRICHED_PATH, FINAL_MTL_PATH)
    
    print("\n" + "="*80)
    print("STEP 3 COMPLETED!")
    print("="*80)
    print(f"\nFinal output: {FINAL_MTL_PATH}")


if __name__ == '__main__':
    main()