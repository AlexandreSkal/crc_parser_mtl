#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTL Converter — Interactive CLI
================================
Run with:  python -m crc_parser_mtl     (if installed as package)
           python __main__.py           (from project root)
           uv run python __main__.py    (via uv)

Replaces the old run_all.py — guides you step-by-step through the
full pipeline with interactive prompts.
"""

import os
import sys
import glob
import subprocess
import importlib

# ── Ensure we're running from the project root ──────────────────────────────
# This makes all imports (config, step1_extract, etc.) work regardless of
# how the script is invoked.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


# ── Pretty helpers ──────────────────────────────────────────────────────────
BLUE   = "\033[94m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# On Windows CMD, ANSI might not be enabled — fall back gracefully
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        BLUE = GREEN = YELLOW = RED = BOLD = RESET = ""


def banner():
    print(f"""
{BOLD}╔══════════════════════════════════════════════════════════╗
║          MTL Converter — Master Tag List Generator       ║
║          Interactive CLI                                 ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")


def section(title: str):
    width = 60
    print(f"\n{BOLD}{BLUE}{'─' * width}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─' * width}{RESET}")


def ok(msg: str):
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {msg}")


def err(msg: str):
    print(f"  {RED}✗{RESET} {msg}")


def ask(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        raw = input(f"  {prompt} [{default}]: ").strip()
        return raw if raw else default
    else:
        return input(f"  {prompt}: ").strip()


def ask_choice(prompt: str, options: list, default: int = 1) -> int:
    """Display numbered options and return the chosen index (1-based)."""
    print(f"\n  {prompt}")
    for i, opt in enumerate(options, 1):
        marker = f"{BOLD}→{RESET}" if i == default else " "
        print(f"  {marker} {i}) {opt}")
    while True:
        raw = input(f"  Choice [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if 1 <= val <= len(options):
                return val
        except ValueError:
            pass
        print(f"  {RED}Invalid choice. Pick 1-{len(options)}.{RESET}")


def confirm(prompt: str, default_yes: bool = True) -> bool:
    hint = "Y/n" if default_yes else "y/N"
    raw = input(f"  {prompt} [{hint}]: ").strip().lower()
    if not raw:
        return default_yes
    return raw in ("y", "yes", "s", "sim")


# ── File scanning ───────────────────────────────────────────────────────────
def scan_input_files(input_dir: str) -> dict:
    """Scan data/input/ and return categorized file lists."""
    files = {"cpa": [], "neoproj_zip": [], "neoproj_dir": [], "csv": [], "l5k": [], "xls": []}
    if not os.path.isdir(input_dir):
        return files
    for entry in os.listdir(input_dir):
        full = os.path.join(input_dir, entry)
        low = entry.lower()
        if low.endswith(".cpa"):
            files["cpa"].append(entry)
        elif low.endswith(".zip"):
            files["neoproj_zip"].append(entry)
        elif os.path.isdir(full) and glob.glob(os.path.join(full, "*.neoproj")):
            files["neoproj_dir"].append(entry)
        elif low.endswith(".csv"):
            files["csv"].append(entry)
        elif low.endswith(".l5k") or low.endswith(".l5x"):
            files["l5k"].append(entry)
        elif low.endswith(".xls") or low.endswith(".xlsx") or low.endswith(".xlsm"):
            files["xls"].append(entry)
    return files


# ── Config writer ───────────────────────────────────────────────────────────
def write_config_values(config_path: str, updates: dict):
    """Rewrite specific variable assignments in config.py.
    
    updates: dict of {VAR_NAME: new_value_string}
    e.g. {"HMI_TYPE": '"NEOPROJ"', "CPA_FILE": '"my_file.cpa"'}
    """
    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        replaced = False
        for var, val in updates.items():
            # Match: VAR_NAME = ... (with optional spaces)
            stripped = line.lstrip()
            if stripped.startswith(f"{var} ") or stripped.startswith(f"{var}="):
                indent = line[:len(line) - len(stripped)]
                new_lines.append(f"{indent}{var} = {val}\n")
                replaced = True
                break
        if not replaced:
            new_lines.append(line)

    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# ── Step runner ─────────────────────────────────────────────────────────────
def run_step(script_name: str, step_num: int, step_desc: str) -> bool:
    """Run a step script as a subprocess using the same Python interpreter."""
    section(f"Step {step_num}: {step_desc}")

    script_path = os.path.join(PROJECT_ROOT, script_name)
    if not os.path.isfile(script_path):
        err(f"Script not found: {script_path}")
        return False

    print(f"  Running {script_name}...\n")
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=PROJECT_ROOT,
    )

    if result.returncode != 0:
        err(f"Step {step_num} failed (exit code {result.returncode})")
        return False

    ok(f"Step {step_num} completed successfully!")
    return True


# ── Main menu actions ───────────────────────────────────────────────────────

def action_configure():
    """Interactive configuration wizard."""
    section("Configuration Wizard")

    config_path = os.path.join(PROJECT_ROOT, "config.py")
    input_dir = os.path.join(PROJECT_ROOT, "data", "input")

    # Ensure directories exist
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, "data", "output"), exist_ok=True)

    # Scan available files
    files = scan_input_files(input_dir)

    # ── HMI Type ──
    hmi_options = ["CPA  — PanelBuilder / CIMREX (.cpa)", "NeoProj — IX Developer (.zip or folder)"]
    hmi_choice = ask_choice("Select HMI type:", hmi_options)
    hmi_type = "CPA" if hmi_choice == 1 else "NEOPROJ"
    updates = {"HMI_TYPE": f'"{hmi_type}"'}

    # ── HMI File ──
    if hmi_type == "CPA":
        candidates = files["cpa"]
        if candidates:
            print(f"\n  Found CPA files in data/input/:")
            for i, f_name in enumerate(candidates, 1):
                print(f"    {i}) {f_name}")
            idx = ask_choice("Select CPA file:", candidates)
            cpa_file = candidates[idx - 1]
        else:
            warn("No .cpa files found in data/input/")
            cpa_file = ask("Enter CPA filename (place in data/input/)", "my_project.cpa")
        updates["CPA_FILE"] = f'"{cpa_file}"'
        ok(f"CPA file: {cpa_file}")
    else:
        candidates = files["neoproj_zip"] + files["neoproj_dir"]
        if candidates:
            print(f"\n  Found NeoProj files in data/input/:")
            for i, f_name in enumerate(candidates, 1):
                print(f"    {i}) {f_name}")
            idx = ask_choice("Select NeoProj file/folder:", candidates)
            neo_file = candidates[idx - 1]
        else:
            warn("No .zip or NeoProj folders found in data/input/")
            neo_file = ask("Enter NeoProj filename (place in data/input/)", "my_project.zip")
        updates["NEOPROJ_FILE"] = f'"{neo_file}"'
        ok(f"NeoProj file: {neo_file}")

    # ── CSV (optional) ──
    if files["csv"]:
        print(f"\n  Found CSV files: {', '.join(files['csv'])}")
        if confirm("Use CSV for enrichment?"):
            if len(files["csv"]) == 1:
                csv_file = files["csv"][0]
            else:
                idx = ask_choice("Select CSV file:", files["csv"])
                csv_file = files["csv"][idx - 1]
            updates["CSV_FILE"] = f'"{csv_file}"'
            updates["ENABLE_CSV"] = "True"
            ok(f"CSV file: {csv_file}")
        else:
            updates["ENABLE_CSV"] = "False"
    else:
        warn("No CSV files found — skipping CSV enrichment")
        updates["ENABLE_CSV"] = "False"

    # ── L5K (optional) ──
    if files["l5k"]:
        print(f"\n  Found L5K files: {', '.join(files['l5k'])}")
        if confirm("Use L5K for enrichment?"):
            if len(files["l5k"]) == 1:
                l5k_file = files["l5k"][0]
            else:
                idx = ask_choice("Select L5K file:", files["l5k"])
                l5k_file = files["l5k"][idx - 1]
            updates["L5K_FILE"] = f'"{l5k_file}"'
            updates["ENABLE_L5K"] = "True"
            ok(f"L5K file: {l5k_file}")
        else:
            updates["ENABLE_L5K"] = "False"
    else:
        warn("No L5K files found — skipping L5K enrichment")
        updates["ENABLE_L5K"] = "False"

    # ── Write config ──
    print()
    write_config_values(config_path, updates)
    ok("config.py updated!")

    # Show summary
    print(f"\n  {BOLD}Summary:{RESET}")
    print(f"    HMI Type : {hmi_type}")
    if hmi_type == "CPA":
        print(f"    CPA File : {updates.get('CPA_FILE', '—')}")
    else:
        print(f"    NeoProj  : {updates.get('NEOPROJ_FILE', '—')}")
    print(f"    CSV      : {updates.get('CSV_FILE', 'disabled')}")
    print(f"    L5K      : {updates.get('L5K_FILE', 'disabled')}")
    print(f"    Output   : data/output/")


def action_run_pipeline():
    """Run the full 3-step pipeline."""
    section("Full Pipeline")

    # Quick check config
    try:
        # Force reload in case user just edited config
        if "config" in sys.modules:
            importlib.reload(sys.modules["config"])
        import config
        print(f"  HMI Type : {config.HMI_TYPE}")
        print(f"  HMI Path : {config.HMI_PATH}")
        if not config.HMI_PATH or not os.path.exists(config.HMI_PATH):
            warn(f"HMI file not found: {config.HMI_PATH}")
            if not confirm("Continue anyway?", default_yes=False):
                return
    except Exception as e:
        warn(f"Could not read config: {e}")

    print()
    if not confirm("Run all 3 steps?"):
        return

    steps = [
        ("step1_extract.py", 1, "Extract IOs from HMI"),
        ("step2_enrich.py",  2, "Enrich descriptions"),
        ("step3_convert.py", 3, "Convert to Master Tag List"),
    ]

    for script, num, desc in steps:
        success = run_step(script, num, desc)
        if not success:
            err("Pipeline stopped due to error.")
            if confirm("Continue to next step anyway?", default_yes=False):
                continue
            return

    section("Pipeline Complete!")
    ok("Output files in data/output/:")
    output_dir = os.path.join(PROJECT_ROOT, "data", "output")
    if os.path.isdir(output_dir):
        for f_name in sorted(os.listdir(output_dir)):
            if f_name.startswith("0"):
                print(f"    📄 {f_name}")


def action_run_step():
    """Run a single step."""
    steps = [
        ("step1_extract.py", "Extract IOs from HMI file"),
        ("step2_enrich.py",  "Enrich descriptions (RACK, CSV, L5K)"),
        ("step3_convert.py", "Convert to Master Tag List"),
    ]
    options = [f"{s[1]}  ({s[0]})" for s in steps]
    choice = ask_choice("Which step to run?", options)
    script, desc = steps[choice - 1][0], steps[choice - 1][1]
    run_step(script, choice, desc)


def action_show_config():
    """Show current configuration."""
    section("Current Configuration")
    try:
        if "config" in sys.modules:
            importlib.reload(sys.modules["config"])
        import config
        config.print_config()
    except Exception as e:
        err(f"Error reading config: {e}")


def action_tag_matcher():
    """Launch the Tag Matcher GUI tool."""
    section("Tag Matcher GUI")

    tool_path = os.path.join(PROJECT_ROOT, "tools", "tag_matcher.py")
    if not os.path.isfile(tool_path):
        err("tools/tag_matcher.py not found!")
        warn("Make sure you have the tools/ directory in your project.")
        return

    print("  Launching Tag Matcher...\n")
    subprocess.Popen(
        [sys.executable, tool_path],
        cwd=PROJECT_ROOT,
    )
    ok("Tag Matcher launched in a separate window.")
    print("  (You can continue using this CLI)")


def action_check_files():
    """Check what files are available."""
    section("File Check")

    input_dir = os.path.join(PROJECT_ROOT, "data", "input")
    output_dir = os.path.join(PROJECT_ROOT, "data", "output")

    print(f"\n  {BOLD}Input directory:{RESET} {input_dir}")
    if os.path.isdir(input_dir):
        entries = os.listdir(input_dir)
        if entries:
            for entry in sorted(entries):
                full = os.path.join(input_dir, entry)
                size = ""
                if os.path.isfile(full):
                    mb = os.path.getsize(full) / (1024 * 1024)
                    size = f"  ({mb:.1f} MB)" if mb >= 1 else f"  ({os.path.getsize(full)} bytes)"
                icon = "📁" if os.path.isdir(full) else "📄"
                print(f"    {icon} {entry}{size}")
        else:
            warn("Empty — place your input files here")
    else:
        warn("Directory does not exist yet (will be created on first run)")

    print(f"\n  {BOLD}Output directory:{RESET} {output_dir}")
    if os.path.isdir(output_dir):
        entries = [e for e in os.listdir(output_dir) if not e.startswith(".")]
        if entries:
            for entry in sorted(entries):
                full = os.path.join(output_dir, entry)
                size = ""
                if os.path.isfile(full):
                    mb = os.path.getsize(full) / (1024 * 1024)
                    size = f"  ({mb:.1f} MB)" if mb >= 1 else f"  ({os.path.getsize(full)} bytes)"
                print(f"    📄 {entry}{size}")
        else:
            print("    (empty — run the pipeline to generate output)")
    else:
        print("    (will be created on first run)")


# ── Main loop ───────────────────────────────────────────────────────────────

def main():
    banner()

    menu_options = [
        "Configure project        (set HMI type, file names)",
        "Run full pipeline        (steps 1 → 2 → 3)",
        "Run a single step        (pick one step)",
        "Show current config      (display config.py settings)",
        "Check files              (list input/output files)",
        "Launch Tag Matcher GUI   (visual tag matching tool)",
        "Exit",
    ]

    actions = [
        action_configure,
        action_run_pipeline,
        action_run_step,
        action_show_config,
        action_check_files,
        action_tag_matcher,
    ]

    while True:
        section("Main Menu")
        choice = ask_choice("What would you like to do?", menu_options)

        if choice == len(menu_options):  # Exit
            print(f"\n  {GREEN}Goodbye!{RESET}\n")
            break

        try:
            actions[choice - 1]()
        except KeyboardInterrupt:
            print(f"\n  {YELLOW}Cancelled.{RESET}")
        except Exception as e:
            err(f"Error: {e}")

        print()  # breathing room before next menu


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {YELLOW}Interrupted. Goodbye!{RESET}\n")
        sys.exit(0)
