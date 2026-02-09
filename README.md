# MTL Converter — Master Tag List Generator

Converts HMI project files (CPA / NeoProj) into a standardized **Master Tag List (MTL)** spreadsheet.

## Project Structure

```
mtl_converter/
├── config.py                  # All paths and settings
├── patterns.py                # ISA patterns, abbreviations, valid names
├── run_all.py                 # Run the full 3-step pipeline
│
├── parsers/                   # Step 1 — Extract IOs from HMI files
│   ├── __init__.py
│   ├── cpa_parser.py          # PanelBuilder / CIMREX (.cpa)
│   └── neoproj_parser.py      # IX Developer (.neoproj / .zip)
│
├── enrichers/                 # Step 2 — Enrich with additional sources
│   ├── __init__.py
│   ├── cpa_screen_enricher.py # RACK / AI / AO / DI / DO screens (CPA)
│   ├── neoproj_rack_enricher.py # RACK screens (NeoProj XAML)
│   ├── csv_enricher.py        # Rockwell CSV export
│   └── l5k_enricher.py        # Rockwell L5K export
│
├── converters/                # Step 3 — Convert to MTL format
│   ├── __init__.py
│   ├── tag_classifier.py      # ISA tag classification logic
│   ├── text_processor.py      # Abbreviation expansion, capitalization
│   └── mtl_builder.py         # Main IO → MTL row conversion
│
├── utils/                     # Shared utilities
│   ├── __init__.py
│   ├── io_address.py          # Address cleaning, suffix removal
│   ├── cpa_text_library.py    # CPA TextW decoder + text library
│   ├── cpa_screen_reader.py   # Generic CPA screen object parser
│   └── neoproj_zip.py         # NeoProj ZIP extraction
│
├── step1_extract.py           # CLI entry point for Step 1
├── step2_enrich.py            # CLI entry point for Step 2
├── step3_convert.py           # CLI entry point for Step 3
│
└── data/
    ├── input/                 # Place input files here
    └── output/                # Generated files appear here
```

## Quick Start

1. Edit `config.py` — set `HMI_TYPE`, input file names
2. Place input files in `data/input/`
3. Run:

```bash
# Full pipeline
python run_all.py

# Or step by step
python step1_extract.py
python step2_enrich.py
python step3_convert.py
```

## Supported HMI Types

| Type      | Format           | Parser               |
|-----------|------------------|-----------------------|
| **CPA**   | `.cpa`           | `parsers/cpa_parser`  |
| **NeoProj** | `.zip` or folder | `parsers/neoproj_parser` |

## Pipeline Overview

```
Step 1: Extract IOs       →  01_extracted_ios.xlsx
Step 2: Enrich descriptions →  02_enriched_ios.xlsx
Step 3: Convert to MTL     →  03_MASTER_TAG_LIST.xlsx
```

## Output Columns (MTL)

| Column                    | Description                          |
|---------------------------|--------------------------------------|
| `target_id`               | ISA tag (PIT-801, LIT-3692)         |
| `target_units`            | Engineering unit (psig, degf, %)    |
| `equipment_description`   | Equipment name                       |
| `target_name_description` | Classification (Process Value, etc.) |
| `target_scaling`          | Scaling info                         |
| `states`                  | Digital states                       |
| `iconics_plc_path`        | Original PLC address                 |
| `target_description`      | Full description text                |
| `description_source`      | Where description came from          |
| `screens`                 | HMI screens where IO appears         |
