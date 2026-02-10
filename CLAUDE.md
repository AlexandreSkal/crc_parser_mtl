# MTL Converter — HMI to Master Tag List

## What This Project Does
Converts HMI project files (CPA/NeoProj) into standardized Master Tag Lists (XLSX).
Pipeline: Extract IOs → Enrich Descriptions → Classify & Export MTL.

## Architecture (4 packages)
```
parsers/       → Step 1: Extract IOs from HMI files (cpa_parser, neoproj_parser)
enrichers/     → Step 2: Add metadata (cpa_screen, neoproj_rack, csv, l5k)
converters/    → Step 3: ISA classification + MTL output (tag_classifier, text_processor, mtl_builder)
utils/         → Shared code (io_address, cpa_text_library, cpa_screen_reader, neoproj_zip)
```

## Key Commands
```bash
python step1_extract.py    # Extract IOs
python step2_enrich.py     # Enrich descriptions
python step3_convert.py    # Generate MTL
python run_all.py          # Full pipeline
```

## Configuration
All settings in `config.py`. Set `HMI_TYPE = "CPA"` or `"NEOPROJ"`.
Input files go in `data/input/`, outputs appear in `data/output/`.

## Code Conventions
- Python 3.10+, pandas, openpyxl
- ISA tag format: PREFIX-NUMBER (e.g. PIT-701, LXIT-801A)
- Functions return DataFrames; enrichers mutate df in-place and return it
- No external API calls; all processing is local/offline

## Testing
No test framework yet. Verify by running the pipeline and checking output XLSX.

## Important Rules
- NEVER modify patterns.py constants without understanding ISA S5.1 classification
- Tag suffixes (!RD, !WR, !BI) must be cleaned via utils/io_address.py
- RACK screen column detection is dynamic — don't hardcode pixel positions
- Alarm tags (PAH, LAHH) convert to transmitter tags (PIT, LIT) in tag_classifier.py
