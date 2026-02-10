#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLC Tag Matcher - Visual Tool v3
================================
Interactive GUI for loading CPA/NeoProj HMI files, visualizing PLC tags
on screen layouts, and manually matching tags to their metadata
(target_id, units, description).

Features:
- Load CPA, NeoProj ZIP, or pre-parsed CSV files
- Visual scatter plot of all screen elements with zoom/pan
- Filter by element type (PLC_Tag, Text, Unit, Description)
- Search PLC tags by name
- Click-to-select items and create matches
- Auto-match nearest text to each PLC tag
- Export matches to CSV for use in the MTL pipeline
- Tag name formatting (removes Tags. prefix, __RD suffix, converts _N_ to [N])
- Pan with middle mouse button, scroll to zoom

Usage:
    python -m tools.tag_matcher
    # or
    python tools/tag_matcher.py
"""

import os
import re
import shutil
import sys
import tempfile
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd 
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Allow running both as `python tools/tag_matcher.py` and `python -m tools.tag_matcher`
# by ensuring the project root is on sys.path so we can import parsers/utils.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Optional: reuse project parsers when available
try:
    from parsers.cpa_parser import extract_ios_from_cpa  # noqa: F401
    from parsers.neoproj_parser import extract_ios_from_neoproj  # noqa: F401
    _HAS_PROJECT_PARSERS = True
except ImportError:
    _HAS_PROJECT_PARSERS = False


# ============================================================================
# TagMatcherApp
# ============================================================================

class TagMatcherApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("PLC Tag Matcher v3 - Filtros, Busca, CPA e Formatação")
        self.geometry("1700x1000")
        self.minsize(1200, 800)

        # ----- data -----
        self.df: Optional[pd.DataFrame] = None
        self.filtered_df: Optional[pd.DataFrame] = None
        self.selected_screen = tk.StringVar()

        self.selection_order: List[int] = []
        self.assigned_roles: Dict[int, str] = {}
        self.original_types: Dict[int, str] = {}

        self.matched_rows: List[Dict] = []
        self.match_to_indices: Dict[int, List[int]] = {}
        self.index_to_matches: Dict[int, Set[int]] = {}
        self.locked_indices_by_screen: Dict[str, Set[int]] = {}
        self.no_unit_var = tk.BooleanVar(value=False)

        # ----- plot -----
        self.figure = None
        self.ax = None
        self.canvas = None

        # ----- pan (middle mouse button) -----
        self._pan_start = None
        self._pan_xlim = None
        self._pan_ylim = None

        # ----- temp dirs -----
        self._temp_project_dir: Optional[str] = None

        # ----- column schema for match export -----
        self.match_columns = [
            "screen",
            "plc_path", "plc_x", "plc_y",
            "target_id", "target_id_x", "target_id_y",
            "target_units", "target_units_x", "target_units_y",
            "equipment_description", "equipment_description_x", "equipment_description_y",
        ]

        # ----- visual config -----
        self.type_colors = {
            "PLC_Tag": "blue",
            "Text": "green",
            "Unit": "black",
            "Description": "orange",
        }

        self.text_size_var = tk.IntVar(value=8)
        self.show_all_text_var = tk.BooleanVar(value=True)

        # type filter checkboxes
        self.filter_plc_tag_var = tk.BooleanVar(value=True)
        self.filter_text_var = tk.BooleanVar(value=True)
        self.filter_unit_var = tk.BooleanVar(value=True)
        self.filter_description_var = tk.BooleanVar(value=True)

        # search state
        self.search_plc_var = tk.StringVar()
        self.search_results: List[int] = []
        self.current_search_index = 0

        # auto-match
        self.auto_radius_var = tk.DoubleVar(value=140.0)

        # learning / templates (kept for future use)
        self.use_learned_templates_var = tk.BooleanVar(value=True)
        self.role_global_offsets: Dict[str, Dict[str, float]] = {
            "target_id": {"dx": 0.0, "dy": 0.0, "n": 0},
            "target_units": {"dx": 0.0, "dy": 0.0, "n": 0},
            "equipment_description": {"dx": 0.0, "dy": 0.0, "n": 0},
        }
        self.plc_templates: Dict[str, Dict[str, Dict[str, float]]] = {}

        # table edit state
        self._edit_entry: Optional[tk.Entry] = None
        self._edit_item_id: Optional[str] = None
        self._edit_col: Optional[str] = None

        # UI references (set during create_widgets)
        self.screen_dropdown = None
        self.match_table = None
        self.selection_info = None
        self.item_dropdown = None
        self.selected_item_for_type_change = tk.StringVar()
        self.no_unit_check = None
        self.current_item_var = tk.StringVar(value="Select an item to change its type")
        self.type_buttons: Dict[str, tk.Button] = {}
        self.search_status_label = None

        self.create_widgets()
        self.bind_events()

        self.no_unit_check.configure(command=self.update_selection_display)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def _on_close(self):
        try:
            if self._temp_project_dir and os.path.isdir(self._temp_project_dir):
                shutil.rmtree(self._temp_project_dir, ignore_errors=True)
        finally:
            self.destroy()

    # ================================================================== #
    #  Tag-name formatting
    # ================================================================== #
    @staticmethod
    def format_tag_name(tag_value: str) -> str:
        """Pretty-print a PLC tag name for display.

        1. Strip leading ``Tags.``
        2. Strip trailing ``__RD`` (keep one ``_``) or ``_RD``
        3. Convert ``_NNN_`` / ``_NNN$`` to ``[NNN]``
        """
        if not tag_value:
            return tag_value

        result = tag_value

        # 1 – remove "Tags." prefix
        if result.startswith("Tags."):
            result = result[5:]

        # 2 – remove trailing read-direction suffix
        if result.endswith("__RD"):
            result = result[:-4] + "_"
        elif result.endswith("_RD"):
            result = result[:-3] + "_"

        # 3 – _NNN_ → [NNN]  and  _NNN$ → [NNN]
        result = re.sub(r"_(\d+)_", r"[\1]", result)
        result = re.sub(r"_(\d+)$", r"[\1]", result)

        return result

    # ================================================================== #
    #  CPA parsing (self-contained)
    # ================================================================== #
    @staticmethod
    def _decode_textw(textw: str) -> str:
        if not isinstance(textw, str):
            return ""
        parts = re.findall(r"\b[0-9A-Fa-f]{4}\b", textw)
        chars = []
        for p in parts:
            try:
                chars.append(chr(int(p, 16)))
            except ValueError:
                continue
        return "".join(chars).strip()

    @staticmethod
    def _parse_cpa_text_library(cpa_path: str) -> Dict[int, str]:
        text_map: Dict[int, str] = {}
        current_is_text_entry = False
        current_no: Optional[int] = None

        with open(cpa_path, "r", errors="ignore") as fh:
            for raw in fh:
                line = raw.strip()
                if line.startswith("[[[[") and line.endswith("]]]]"):
                    name = line[4:-4].strip()
                    current_is_text_entry = name == "Text language library text"
                    current_no = None
                    continue
                if not current_is_text_entry:
                    continue
                if line.startswith("No="):
                    try:
                        current_no = int(line.split("=", 1)[1].strip())
                    except ValueError:
                        current_no = None
                    continue
                if line.startswith("TextW=") and current_no is not None:
                    textw = line.split("=", 1)[1].strip()
                    decoded = TagMatcherApp._decode_textw(textw)
                    text_map[current_no] = decoded
        return text_map

    @staticmethod
    def _parse_cpa_to_dataframe(cpa_path: str) -> pd.DataFrame:
        text_map = TagMatcherApp._parse_cpa_text_library(cpa_path)

        in_graphic_block = False
        current_screen: Optional[str] = None
        current_obj_type: Optional[str] = None
        obj_data: Dict[str, str] = {}
        records: List[Dict] = []

        def flush_object():
            nonlocal obj_data, current_obj_type, current_screen, in_graphic_block
            if not in_graphic_block or not current_screen or not current_obj_type:
                obj_data = {}
                current_obj_type = None
                return
            if "x" not in obj_data or "y" not in obj_data:
                obj_data = {}
                current_obj_type = None
                return
            try:
                x = float(obj_data["x"])
                y = float(obj_data["y"])
            except ValueError:
                obj_data = {}
                current_obj_type = None
                return

            io_val = obj_data.get("IO")
            if io_val:
                records.append({"x": x, "y": y, "value": str(io_val).strip(),
                                "type": "PLC_Tag", "Screen": current_screen})
                obj_data = {}
                current_obj_type = None
                return

            text_val = obj_data.get("Text")
            if text_val and isinstance(text_val, str):
                m = re.match(r"@(\d+)$", text_val.strip())
                if m:
                    tid = int(m.group(1))
                    resolved = text_map.get(tid, f"@{tid}")
                    records.append({"x": x, "y": y, "value": resolved,
                                    "type": "Text", "Screen": current_screen})
                else:
                    records.append({"x": x, "y": y, "value": text_val.strip(),
                                    "type": "Text", "Screen": current_screen})
            obj_data = {}
            current_obj_type = None

        with open(cpa_path, "r", errors="ignore") as fh:
            for raw in fh:
                s = raw.strip()
                if s.startswith("[[[") and s.endswith("]]]") and not s.startswith("[[[["):
                    flush_object()
                    name = s[3:-3].strip()
                    if name == "GraphicBlock":
                        in_graphic_block = True
                        current_screen = None
                    else:
                        in_graphic_block = False
                        current_screen = None
                    continue
                if not in_graphic_block:
                    continue
                if current_screen is None and s.startswith("Name="):
                    current_screen = s.split("=", 1)[1].strip()
                    continue
                if s.startswith("[[[[") and s.endswith("]]]]"):
                    flush_object()
                    current_obj_type = s[4:-4].strip()
                    obj_data = {}
                    continue
                if not current_obj_type:
                    continue
                if "=" in s:
                    k, v = s.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k in ("x", "y", "IO", "Text"):
                        obj_data[k] = v

        flush_object()

        df = pd.DataFrame(records)
        if df.empty:
            return df
        df["x"] = pd.to_numeric(df["x"], errors="coerce")
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
        df = df.dropna(subset=["x", "y", "value", "type", "Screen"])
        return df

    # ================================================================== #
    #  NeoProj parsing (self-contained)
    # ================================================================== #
    @staticmethod
    def _xml_localname(tag: str) -> str:
        if tag.startswith("{") and "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @staticmethod
    def _safe_extract_zip(zip_path: str, dest_dir: str) -> None:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                name = member.filename.replace("\\", "/")
                norm = os.path.normpath(name)
                if os.path.isabs(norm) or norm.startswith(".."):
                    raise ValueError(f"Unsafe path in zip: {member.filename}")
                target_path = os.path.join(dest_dir, norm)
                if member.is_dir():
                    os.makedirs(target_path, exist_ok=True)
                    continue
                parent = os.path.dirname(target_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with zf.open(member, "r") as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    @staticmethod
    def _find_first_file(root_dir: str, ext: str) -> Optional[str]:
        ext = ext.lower()
        for r, _, files in os.walk(root_dir):
            for fn in files:
                if fn.lower().endswith(ext):
                    return os.path.join(r, fn)
        return None

    @staticmethod
    def _parse_neoproj_screens(neoproj_path: str) -> List[Dict[str, str]]:
        tree = ET.parse(neoproj_path)
        root = tree.getroot()
        screens: List[Dict[str, str]] = []
        for el in root.iter("Object"):
            attrib_values = list(el.attrib.values())
            if any("ScreenDesignerProjectItem" in str(v) for v in attrib_values):
                name = el.attrib.get("Name", "").strip()
                filename = el.attrib.get("Filename", "").strip()
                group = el.attrib.get("Group", "").strip()
                if group.lower() == "screens" and filename and name:
                    screens.append({"screen": name, "file": filename})
        return screens

    @staticmethod
    def _extract_coords_from_element(el: ET.Element) -> Tuple[Optional[float], Optional[float]]:
        x, y = None, None
        for k, v in el.attrib.items():
            lk = TagMatcherApp._xml_localname(k)
            if lk in ("Canvas.Left", "Left"):
                try:
                    x = float(str(v).strip())
                except ValueError:
                    pass
            elif lk in ("Canvas.Top", "Top"):
                try:
                    y = float(str(v).strip())
                except ValueError:
                    pass
        return x, y

    @staticmethod
    def _extract_tags_from_text(text: str) -> List[str]:
        tags: Set[str] = set()
        if not text:
            return []
        for m in re.finditer(r"\[Tags\.([^\]]+)\]", text):
            tags.add("Tags." + m.group(1).strip())
        for m in re.finditer(r"\bTags\.[A-Za-z0-9_\.]+", text):
            tags.add(m.group(0).strip())
        return sorted(tags)

    @staticmethod
    def _parse_xaml_points(xaml_path: str, screen_name: str) -> List[Dict]:
        records: List[Dict] = []
        try:
            tree = ET.parse(xaml_path)
            root = tree.getroot()
        except Exception:
            return records

        text_attr_candidates = {"Text", "Content", "Caption", "Title"}
        tag_attr_candidates = {"DataSourceName"}

        for el in root.iter():
            x, y = TagMatcherApp._extract_coords_from_element(el)
            if x is None or y is None:
                continue

            tag_value = None
            for k, v in el.attrib.items():
                lk = TagMatcherApp._xml_localname(k)
                if lk in tag_attr_candidates:
                    vv = str(v).strip()
                    if vv:
                        tag_value = vv
                        break

            if not tag_value:
                for _, v in el.attrib.items():
                    tags = TagMatcherApp._extract_tags_from_text(str(v))
                    if tags:
                        tag_value = tags[0]
                        break

            if not tag_value:
                try:
                    blob = ET.tostring(el, encoding="unicode", method="xml")
                    tags = TagMatcherApp._extract_tags_from_text(blob)
                    if tags:
                        tag_value = tags[0]
                except Exception:
                    pass

            if tag_value:
                records.append({"x": x, "y": y, "value": tag_value,
                                "type": "PLC_Tag", "Screen": screen_name})
                continue

            for k, v in el.attrib.items():
                lk = TagMatcherApp._xml_localname(k)
                if lk in text_attr_candidates:
                    vv = str(v).strip()
                    if vv:
                        records.append({"x": x, "y": y, "value": vv,
                                        "type": "Text", "Screen": screen_name})
                        break
        return records

    @staticmethod
    def _parse_neoproj_to_dataframe(neoproj_path: str) -> pd.DataFrame:
        project_dir = os.path.dirname(os.path.abspath(neoproj_path))
        screens = TagMatcherApp._parse_neoproj_screens(neoproj_path)

        records: List[Dict] = []
        missing_files: List[str] = []

        for item in screens:
            screen_name = item["screen"]
            rel = item["file"]
            base, _ = os.path.splitext(rel)

            candidates = [
                os.path.join(project_dir, base + ".xaml"),
                os.path.join(project_dir, rel),
                os.path.join(project_dir, base + ".neoxaml"),
            ]

            found = None
            for p in candidates:
                if os.path.isfile(p):
                    found = p
                    break

            if not found:
                missing_files.append(rel)
                continue

            records.extend(TagMatcherApp._parse_xaml_points(found, screen_name))

        df = pd.DataFrame(records)
        df.attrs["missing_screen_files"] = missing_files
        df.attrs["screen_count_in_project"] = len(screens)
        return df

    # ================================================================== #
    #  Helpers
    # ================================================================== #
    def _get_visible_types(self) -> Set[str]:
        visible = set()
        if self.filter_plc_tag_var.get():
            visible.add("PLC_Tag")
        if self.filter_text_var.get():
            visible.add("Text")
        if self.filter_unit_var.get():
            visible.add("Unit")
        if self.filter_description_var.get():
            visible.add("Description")
        return visible

    def get_match_count_for_index(self, idx):
        return len(self.index_to_matches.get(idx, set()))

    def get_effective_type(self, idx):
        if self.filtered_df is not None and idx in self.filtered_df.index:
            return self.assigned_roles.get(idx, self.filtered_df.loc[idx, "type"])
        return "Unknown"

    # ================================================================== #
    #  Search
    # ================================================================== #
    def search_plc_tag(self):
        term = self.search_plc_var.get().strip().lower()
        if not term:
            messagebox.showwarning("Search", "Enter a search term.")
            return
        if self.filtered_df is None or self.filtered_df.empty:
            messagebox.showwarning("Search", "No data loaded for the current screen.")
            return

        plc_tags = self.filtered_df[self.filtered_df["type"] == "PLC_Tag"]

        def _matches(value):
            return term in str(value).lower() or term in self.format_tag_name(str(value)).lower()

        matches = plc_tags[plc_tags["value"].apply(_matches)]
        if matches.empty:
            self.search_results = []
            self.current_search_index = 0
            self.search_status_label.config(text="0 results")
            messagebox.showinfo("Search", f"No PLC_Tag matching '{term}'.")
            return

        self.search_results = matches.index.tolist()
        self.current_search_index = 0
        self._select_search_result()

    def search_next(self):
        if not self.search_results:
            messagebox.showwarning("Search", "No results. Run a search first.")
            return
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self._select_search_result()

    def _select_search_result(self):
        if not self.search_results or self.filtered_df is None:
            return
        idx = self.search_results[self.current_search_index]
        if idx not in self.selection_order:
            self.selection_order.append(idx)

        total = len(self.search_results)
        current = self.current_search_index + 1
        self.search_status_label.config(text=f"{current}/{total}")

        if idx in self.filtered_df.index:
            row = self.filtered_df.loc[idx]
            x, y = float(row["x"]), float(row["y"])
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            xsz = xlim[1] - xlim[0]
            ysz = ylim[1] - ylim[0]
            self.ax.set_xlim(x - xsz / 2, x + xsz / 2)
            self.ax.set_ylim(y - ysz / 2, y + ysz / 2)

        self.update_plot()
        self.update_selection_display()

    def clear_search(self):
        self.search_plc_var.set("")
        self.search_results = []
        self.current_search_index = 0
        self.search_status_label.config(text="")
        self.update_plot()

    # ================================================================== #
    #  Data refresh helpers
    # ================================================================== #
    def _reset_all_state_for_new_data(self):
        self.clear_selection()
        for item in self.match_table.get_children():
            self.match_table.delete(item)
        self.matched_rows.clear()
        self.match_to_indices.clear()
        self.index_to_matches.clear()
        self.locked_indices_by_screen.clear()
        self.search_results = []
        self.current_search_index = 0
        if self.search_status_label:
            self.search_status_label.config(text="")

    def _set_df_and_refresh(self, df: pd.DataFrame, source_name: str):
        if df is None or df.empty:
            messagebox.showerror("No Data", f"No valid data found in {source_name}.")
            return

        required = {"x", "y", "value", "type", "Screen"}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            messagebox.showerror("Missing Columns", f"Data must contain: {', '.join(sorted(missing))}")
            return

        df = df.dropna(subset=["x", "y", "value", "type", "Screen"]).copy()
        df["x"] = pd.to_numeric(df["x"], errors="coerce")
        df["y"] = pd.to_numeric(df["y"], errors="coerce")
        df = df.dropna(subset=["x", "y"])
        if df.empty:
            messagebox.showerror("No Data", f"No valid coordinates in {source_name}.")
            return

        self._reset_all_state_for_new_data()
        self.df = df

        screens = sorted(df["Screen"].dropna().unique())
        self.screen_dropdown["values"] = screens
        if screens:
            self.selected_screen.set(screens[0])
            self.update_plot()

        messagebox.showinfo("Success", f"Loaded {len(df)} records from {len(screens)} screens ({source_name}).")

    # ================================================================== #
    #  Loaders
    # ================================================================== #
    def load_csv(self):
        path = filedialog.askopenfilename(title="Select CSV file",
                                          filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
            if "Screen" not in df.columns and "screen" in df.columns:
                df = df.rename(columns={"screen": "Screen"})
            self._set_df_and_refresh(df, os.path.basename(path))
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def load_cpa(self):
        path = filedialog.askopenfilename(title="Select CPA file",
                                          filetypes=[("CPA", "*.cpa"), ("All", "*.*")])
        if not path:
            return
        try:
            df = self._parse_cpa_to_dataframe(path)
            self._set_df_and_refresh(df, os.path.basename(path))
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def load_neoproj_zip(self):
        path = filedialog.askopenfilename(title="Select NeoProj ZIP",
                                          filetypes=[("ZIP", "*.zip"), ("All", "*.*")])
        if not path:
            return
        try:
            if self._temp_project_dir and os.path.isdir(self._temp_project_dir):
                shutil.rmtree(self._temp_project_dir, ignore_errors=True)
            self._temp_project_dir = tempfile.mkdtemp(prefix="neo_project_")
            self._safe_extract_zip(path, self._temp_project_dir)

            neoproj_path = self._find_first_file(self._temp_project_dir, ".neoproj")
            if not neoproj_path:
                messagebox.showerror("NeoProj ZIP", "No .neoproj file found in ZIP.")
                return

            df = self._parse_neoproj_to_dataframe(neoproj_path)
            if df is None or df.empty:
                messagebox.showwarning("NeoProj ZIP", "No data extracted.")
                return

            self._set_df_and_refresh(df, os.path.basename(path))
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    # ================================================================== #
    #  UI creation
    # ================================================================== #
    def create_widgets(self):
        # --- row 1: file ops ---
        controls = tk.Frame(self)
        controls.pack(fill="x", padx=10, pady=5)

        file_frame = tk.Frame(controls)
        file_frame.pack(side="left", fill="x")

        tk.Button(file_frame, text="Load CSV", command=self.load_csv,
                  bg="lightblue", font=("Arial", 10, "bold")).pack(side="left", padx=2)
        tk.Button(file_frame, text="Load CPA", command=self.load_cpa,
                  bg="lightsteelblue", font=("Arial", 10, "bold")).pack(side="left", padx=2)
        tk.Button(file_frame, text="Load NeoProj ZIP", command=self.load_neoproj_zip,
                  bg="thistle", font=("Arial", 10, "bold")).pack(side="left", padx=2)
        tk.Button(file_frame, text="Load Matches", command=self.load_matches,
                  bg="lightgreen").pack(side="left", padx=2)
        tk.Button(file_frame, text="Export Matches", command=self.export_matches,
                  bg="lightyellow").pack(side="left", padx=2)
        tk.Button(file_frame, text="Auto Match Screen", command=self.auto_match_current_screen,
                  bg="lightcyan", font=("Arial", 10, "bold")).pack(side="left", padx=10)

        # --- row 2: screen, view, filters, search ---
        controls2 = tk.Frame(self)
        controls2.pack(fill="x", padx=10, pady=2)

        screen_frame = tk.Frame(controls2)
        screen_frame.pack(side="left", padx=5)
        tk.Label(screen_frame, text="Screen:", font=("Arial", 10, "bold")).pack(side="left")
        self.screen_dropdown = ttk.Combobox(screen_frame, textvariable=self.selected_screen,
                                            state="readonly", width=20)
        self.screen_dropdown.pack(side="left", padx=5)

        view_frame = tk.Frame(controls2)
        view_frame.pack(side="left", padx=10)
        tk.Label(view_frame, text="Text Size:", font=("Arial", 9)).pack(side="left")
        tk.Scale(view_frame, from_=6, to=14, orient="horizontal",
                 variable=self.text_size_var, length=80,
                 command=lambda _: self.update_plot()).pack(side="left", padx=2)
        tk.Checkbutton(view_frame, text="Show text", variable=self.show_all_text_var,
                       command=self.update_plot).pack(side="left", padx=5)
        tk.Label(view_frame, text="Radius:", font=("Arial", 9)).pack(side="left", padx=(10, 0))
        tk.Entry(view_frame, textvariable=self.auto_radius_var, width=5).pack(side="left", padx=2)

        # type filters
        filter_frame = tk.LabelFrame(controls2, text="Type Filters", font=("Arial", 9, "bold"))
        filter_frame.pack(side="left", padx=15)
        tk.Checkbutton(filter_frame, text="PLC_Tag", variable=self.filter_plc_tag_var,
                       fg="blue", command=self.update_plot).pack(side="left", padx=3)
        tk.Checkbutton(filter_frame, text="Text", variable=self.filter_text_var,
                       fg="green", command=self.update_plot).pack(side="left", padx=3)
        tk.Checkbutton(filter_frame, text="Unit", variable=self.filter_unit_var,
                       fg="gray", command=self.update_plot).pack(side="left", padx=3)
        tk.Checkbutton(filter_frame, text="Description", variable=self.filter_description_var,
                       fg="orange", command=self.update_plot).pack(side="left", padx=3)

        # search
        search_frame = tk.LabelFrame(controls2, text="Search PLC_Tag", font=("Arial", 9, "bold"))
        search_frame.pack(side="left", padx=15)
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_plc_var, width=20)
        self.search_entry.pack(side="left", padx=3)
        self.search_entry.bind("<Return>", lambda _: self.search_plc_tag())
        tk.Button(search_frame, text="Find", command=self.search_plc_tag, bg="lightyellow").pack(side="left", padx=2)
        tk.Button(search_frame, text="Next", command=self.search_next, bg="lightyellow").pack(side="left", padx=2)
        tk.Button(search_frame, text="Clear", command=self.clear_search, bg="lightgray").pack(side="left", padx=2)
        self.search_status_label = tk.Label(search_frame, text="", font=("Arial", 8), width=8)
        self.search_status_label.pack(side="left", padx=5)

        # action buttons
        action_frame = tk.Frame(controls2)
        action_frame.pack(side="right")
        tk.Button(action_frame, text="Mark as Match", command=self.mark_as_match,
                  bg="lightcoral", font=("Arial", 10, "bold")).pack(side="left", padx=2)
        tk.Button(action_frame, text="Clear Selection", command=self.clear_selection,
                  bg="lightgray").pack(side="left", padx=2)
        tk.Button(action_frame, text="Delete Match", command=self.delete_selected_match,
                  bg="red", fg="white").pack(side="left", padx=2)

        # legend
        legend_frame = tk.LabelFrame(self, text="Legend (Middle-click + drag = Pan)",
                                     font=("Arial", 10, "bold"))
        legend_frame.pack(fill="x", padx=10, pady=2)
        legend_inner = tk.Frame(legend_frame)
        legend_inner.pack(pady=2)
        for label, bg, fg in [("PLC_Tag", "blue", "white"), ("Text", "green", "white"),
                               ("Unit", "black", "white"), ("Description", "orange", "white"),
                               ("Selected", "red", "white"), ("In Match", "purple", "white"),
                               ("Search Result", "yellow", "black")]:
            tk.Label(legend_inner, text=label, bg=bg, fg=fg, width=12,
                     relief="raised", borderwidth=1).pack(side="left", padx=2)

        # main paned
        main_paned = ttk.PanedWindow(self, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=10, pady=5)

        plot_frame = tk.LabelFrame(main_paned, text="Plot (Scroll=Zoom, Middle+Drag=Pan)",
                                   font=("Arial", 10, "bold"))
        main_paned.add(plot_frame, weight=2)
        self.setup_plot(plot_frame)

        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # selection info
        self.live_frame = tk.LabelFrame(right_frame, text="Current Selection",
                                        font=("Arial", 10, "bold"))
        self.live_frame.pack(fill="x", pady=5)
        self.selection_info = tk.Text(self.live_frame, height=6, width=40,
                                      state="disabled", bg="lightyellow")
        self.selection_info.pack(fill="x", padx=5, pady=2)

        # type reassignment
        type_frame = tk.LabelFrame(self.live_frame, text="Reassign Item Type")
        type_frame.pack(fill="x", padx=5, pady=2)
        tk.Label(type_frame, textvariable=self.current_item_var,
                 font=("Arial", 9), wraplength=300).pack(pady=2)
        btn_frame = tk.Frame(type_frame)
        btn_frame.pack(pady=2)
        for tkey, (dname, color) in {"PLC_Tag": ("PLC Tag", "lightblue"),
                                      "Text": ("Text", "lightgreen"),
                                      "Unit": ("Unit", "lightgray"),
                                      "Description": ("Description", "lightyellow")}.items():
            btn = tk.Button(btn_frame, text=f"Set as {dname}", bg=color,
                            command=lambda t=tkey: self.change_item_type(t))
            btn.pack(side="left", padx=2)
            self.type_buttons[tkey] = btn

        sel_frame = tk.Frame(type_frame)
        sel_frame.pack(fill="x", pady=2)
        tk.Label(sel_frame, text="Item to modify:").pack(side="left")
        self.item_dropdown = ttk.Combobox(sel_frame, textvariable=self.selected_item_for_type_change,
                                          state="readonly", width=28)
        self.item_dropdown.pack(side="left", padx=5)
        self.item_dropdown.bind("<<ComboboxSelected>>", self.on_item_selected_for_type_change)
        tk.Button(type_frame, text="Reset All Types", command=self.reset_item_types,
                  bg="lightcoral").pack(pady=2)

        self.no_unit_check = ttk.Checkbutton(self.live_frame, text="This match has no unit",
                                             variable=self.no_unit_var)
        self.no_unit_check.pack(anchor="w", padx=5, pady=2)

        # matches table
        table_frame = tk.LabelFrame(right_frame, text="Matches (double-click to edit)",
                                    font=("Arial", 10, "bold"))
        table_frame.pack(fill="both", expand=True, pady=5)
        self.setup_matches_table(table_frame)

    def setup_plot(self, parent):
        self.figure, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvasTkAgg(self.figure, parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def setup_matches_table(self, parent):
        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        table_columns = self.match_columns + ["match_index"]
        self.match_table = ttk.Treeview(tree_frame, columns=table_columns,
                                        show="headings", selectmode="extended")
        for col in self.match_columns:
            self.match_table.heading(col, text=col.replace("_", " ").title())
            w = 150 if col in ("plc_path", "target_id", "equipment_description") else 70
            self.match_table.column(col, width=w, stretch=False)
        self.match_table.column("match_index", width=0, stretch=False)
        self.match_table.heading("match_index", text="")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.match_table.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.match_table.xview)
        self.match_table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.match_table.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

    def bind_events(self):
        self.screen_dropdown.bind("<<ComboboxSelected>>", self.on_screen_changed)
        if self.canvas:
            self.canvas.mpl_connect("button_press_event", self.on_plot_click)
            self.canvas.mpl_connect("scroll_event", self.on_plot_scroll)
            self.canvas.mpl_connect("button_press_event", self.on_pan_press)
            self.canvas.mpl_connect("button_release_event", self.on_pan_release)
            self.canvas.mpl_connect("motion_notify_event", self.on_pan_motion)
        self.match_table.bind("<Button-3>", self.show_context_menu)
        self.match_table.bind("<Double-1>", self.start_cell_edit)
        self.bind("<Control-s>", lambda _: self.export_matches())
        self.bind("<Delete>", lambda _: self.delete_selected_match())

    # ================================================================== #
    #  Pan (middle mouse)
    # ================================================================== #
    def on_pan_press(self, event):
        if event.button == 2 and event.inaxes == self.ax:
            self._pan_start = (event.xdata, event.ydata)
            self._pan_xlim = self.ax.get_xlim()
            self._pan_ylim = self.ax.get_ylim()

    def on_pan_release(self, event):
        if event.button == 2:
            self._pan_start = None

    def on_pan_motion(self, event):
        if self._pan_start is None or event.inaxes != self.ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        dx = self._pan_start[0] - event.xdata
        dy = self._pan_start[1] - event.ydata
        self.ax.set_xlim(self._pan_xlim[0] + dx, self._pan_xlim[1] + dx)
        self.ax.set_ylim(self._pan_ylim[0] + dy, self._pan_ylim[1] + dy)
        self.canvas.draw_idle()

    # ================================================================== #
    #  Selection / plot
    # ================================================================== #
    def on_screen_changed(self, _event=None):
        self.clear_selection()
        self.clear_search()
        self.update_plot()

    def update_selection_display(self):
        self.selection_info.config(state="normal")
        self.selection_info.delete(1.0, tk.END)

        if self.selection_order and self.filtered_df is not None:
            dd_items = []
            for i, idx in enumerate(self.selection_order, 1):
                if idx in self.filtered_df.index:
                    row = self.filtered_df.loc[idx]
                    eff = self.get_effective_type(idx)
                    orig = row["type"]
                    mc = self.get_match_count_for_index(idx)
                    dv = self.format_tag_name(str(row["value"])) if orig == "PLC_Tag" else str(row["value"])
                    ti = f" → {eff}" if eff != orig else ""
                    mi = f" [{mc}]" if mc > 0 else ""
                    dd_items.append(f"#{i}: {orig}{ti}{mi} - {dv[:30]}")
            self.item_dropdown["values"] = dd_items
            if not self.selected_item_for_type_change.get() and dd_items:
                self.selected_item_for_type_change.set(dd_items[0])
        else:
            self.item_dropdown["values"] = []
            self.selected_item_for_type_change.set("")

        if not self.selection_order or self.filtered_df is None:
            self.selection_info.insert(tk.END, "No items selected.\n\nClick on plot points to select.")
            self.current_item_var.set("Select an item to change its type")
        else:
            self.selection_info.insert(tk.END, f"Selected {len(self.selection_order)} items:\n\n")
            for i, idx in enumerate(self.selection_order, 1):
                if idx in self.filtered_df.index:
                    row = self.filtered_df.loc[idx]
                    eff = self.get_effective_type(idx)
                    dv = self.format_tag_name(str(row["value"])) if row["type"] == "PLC_Tag" else str(row["value"])
                    self.selection_info.insert(tk.END, f"{i}. {eff}: '{dv}'\n")
        self.selection_info.config(state="disabled")
        self.on_item_selected_for_type_change()

    def update_plot(self):
        if self.df is None or not self.selected_screen.get():
            return
        try:
            screen = self.selected_screen.get()
            self.filtered_df = self.df[self.df["Screen"] == screen].copy()
            if self.filtered_df.empty:
                self.ax.clear()
                self.ax.set_title(f"No data for screen: {screen}")
                self.canvas.draw()
                return

            self.ax.clear()
            visible_types = self._get_visible_types()
            unmatched_idx = set()
            matched_idx = set()
            for idx in self.filtered_df.index:
                (matched_idx if self.get_match_count_for_index(idx) > 0 else unmatched_idx).add(idx)

            for pt, color in self.type_colors.items():
                if pt not in visible_types:
                    continue
                td = self.filtered_df[self.filtered_df["type"] == pt]
                if td.empty:
                    continue
                um = td[td.index.isin(unmatched_idx)]
                if not um.empty:
                    self.ax.scatter(um["x"], um["y"], c=color, label=pt, s=40, alpha=0.6, marker="o")
                    if self.show_all_text_var.get():
                        for _, row in um.iterrows():
                            self._add_text_annotation(row, color, pt)
                mt = td[td.index.isin(matched_idx)]
                if not mt.empty:
                    self.ax.scatter(mt["x"], mt["y"], c=color, s=70, alpha=0.9,
                                   edgecolors="purple", linewidth=3, marker="o")
                    if self.show_all_text_var.get():
                        for _, row in mt.iterrows():
                            self._add_text_annotation(row, color, pt)

            # search highlights
            if self.search_results:
                siv = [i for i in self.search_results if i in self.filtered_df.index]
                if siv:
                    sd = self.filtered_df.loc[siv]
                    self.ax.scatter(sd["x"], sd["y"], c="yellow", s=200, alpha=0.6, marker="*",
                                   edgecolors="black", linewidth=2, zorder=5)

            # selected items
            if self.selection_order:
                vs = [i for i in self.selection_order if i in self.filtered_df.index]
                if vs:
                    sd = self.filtered_df.loc[vs]
                    self.ax.scatter(sd["x"], sd["y"], c="none", s=150, marker="o",
                                   facecolors="none", edgecolors="red", linewidth=5)
                    for i, idx in enumerate(vs, 1):
                        row = self.filtered_df.loc[idx]
                        self.ax.annotate(f"#{i}", (row["x"], row["y"]),
                                         xytext=(-15, -15), textcoords="offset points",
                                         fontsize=10, color="white", fontweight="bold",
                                         bbox=dict(boxstyle="circle,pad=0.2", facecolor="red"),
                                         ha="center", va="center")

            self.ax.set_xlabel("X")
            self.ax.set_ylabel("Y")
            tc = self.filtered_df["type"].value_counts().to_dict()
            ts = ", ".join(f"{k}: {v}" for k, v in sorted(tc.items()))
            self.ax.set_title(f"Screen: {screen} | {ts}")
            self.ax.legend(loc="upper left", fontsize=8)
            self.ax.grid(True, alpha=0.3)
            self.ax.invert_yaxis()
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as exc:
            messagebox.showerror("Plot Error", str(exc))

    def _add_text_annotation(self, row, color, item_type):
        raw = str(row["value"])
        if item_type == "PLC_Tag":
            text = self.format_tag_name(raw)
        else:
            text = raw[:25] + ("..." if len(raw) > 25 else "")
        self.ax.annotate(text, (row["x"], row["y"]),
                         xytext=(5, 5), textcoords="offset points",
                         fontsize=self.text_size_var.get(), color=color, alpha=0.9,
                         bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                                   alpha=0.7, edgecolor=color))

    def on_plot_click(self, event):
        if event.button == 2:
            return
        if event.inaxes != self.ax or self.filtered_df is None:
            return
        if event.xdata is None or event.ydata is None:
            return
        visible = self._get_visible_types()
        vdf = self.filtered_df[self.filtered_df["type"].isin(visible)]
        if vdf.empty:
            return
        dists = np.sqrt((vdf["x"] - event.xdata) ** 2 + (vdf["y"] - event.ydata) ** 2)
        nearest = dists.idxmin()
        if dists.min() > 15:
            return
        if nearest in self.selection_order:
            self.selection_order.remove(nearest)
            self.assigned_roles.pop(nearest, None)
        else:
            self.selection_order.append(nearest)
        self.update_plot()
        self.update_selection_display()

    def on_plot_scroll(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        try:
            base = 1.15
            xl = self.ax.get_xlim()
            yl = self.ax.get_ylim()
            sf = 1 / base if event.button == "up" else (base if event.button == "down" else None)
            if sf is None:
                return
            nw = (xl[1] - xl[0]) * sf
            nh = (yl[1] - yl[0]) * sf
            rx = (event.xdata - xl[0]) / (xl[1] - xl[0] + 1e-9)
            ry = (event.ydata - yl[0]) / (yl[1] - yl[0] + 1e-9)
            self.ax.set_xlim([event.xdata - nw * rx, event.xdata + nw * (1 - rx)])
            self.ax.set_ylim([event.ydata - nh * ry, event.ydata + nh * (1 - ry)])
            self.canvas.draw_idle()
        except Exception:
            pass

    # ================================================================== #
    #  Type reassignment
    # ================================================================== #
    def on_item_selected_for_type_change(self, _event=None):
        sel = self.selected_item_for_type_change.get()
        if not sel:
            self.current_item_var.set("Select an item to change its type")
            return
        try:
            num = int(sel.split(":")[0].replace("#", ""))
            if 1 <= num <= len(self.selection_order):
                idx = self.selection_order[num - 1]
                if self.filtered_df is not None and idx in self.filtered_df.index:
                    row = self.filtered_df.loc[idx]
                    ct = self.assigned_roles.get(idx, row["type"])
                    dv = self.format_tag_name(str(row["value"])) if row["type"] == "PLC_Tag" else str(row["value"])
                    self.current_item_var.set(f"Item #{num}: '{dv}' (Current: {ct})")
        except Exception:
            self.current_item_var.set("Select an item to change its type")

    def change_item_type(self, new_type):
        sel = self.selected_item_for_type_change.get()
        if not sel:
            messagebox.showwarning("No Selection", "Select an item first.")
            return
        try:
            num = int(sel.split(":")[0].replace("#", ""))
            if 1 <= num <= len(self.selection_order):
                idx = self.selection_order[num - 1]
                if self.filtered_df is not None and idx in self.filtered_df.index:
                    if idx not in self.original_types:
                        self.original_types[idx] = self.filtered_df.loc[idx, "type"]
                    self.assigned_roles[idx] = new_type
                    self.update_selection_display()
                    self.update_plot()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def reset_item_types(self):
        if not self.selection_order:
            return
        self.assigned_roles.clear()
        self.update_selection_display()
        self.update_plot()

    def clear_selection(self):
        self.selection_order.clear()
        self.assigned_roles.clear()
        self.original_types.clear()
        self.no_unit_var.set(False)
        self.selected_item_for_type_change.set("")
        self.update_plot()
        self.update_selection_display()

    # ================================================================== #
    #  Matches
    # ================================================================== #
    def mark_as_match(self):
        if not self.selection_order:
            messagebox.showwarning("No Selection", "Select items to create a match.")
            return
        if len(self.selection_order) < 2:
            messagebox.showwarning("Need More", "Select at least 2 items.")
            return
        if self.filtered_df is None:
            return
        try:
            screen = self.selected_screen.get()
            md = {c: "" for c in self.match_columns}
            md["screen"] = screen

            for idx in self.selection_order:
                if idx not in self.filtered_df.index:
                    continue
                row = self.filtered_df.loc[idx]
                eff = self.get_effective_type(idx)
                if eff == "PLC_Tag" and not md["plc_path"]:
                    md["plc_path"] = self.format_tag_name(str(row["value"]))
                    md["plc_x"] = float(row["x"])
                    md["plc_y"] = float(row["y"])
                elif eff == "Text" and not md["target_id"]:
                    md["target_id"] = str(row["value"])
                    md["target_id_x"] = float(row["x"])
                    md["target_id_y"] = float(row["y"])
                elif eff == "Unit" and not md["target_units"]:
                    md["target_units"] = str(row["value"])
                    md["target_units_x"] = float(row["x"])
                    md["target_units_y"] = float(row["y"])
                elif eff == "Description" and not md["equipment_description"]:
                    md["equipment_description"] = str(row["value"])
                    md["equipment_description_x"] = float(row["x"])
                    md["equipment_description_y"] = float(row["y"])

            if not md["plc_path"]:
                messagebox.showwarning("Missing PLC Tag", "A match must include at least one PLC_Tag.")
                return

            if self.no_unit_var.get():
                md["target_units"] = "NO_UNIT"
                md["target_units_x"] = ""
                md["target_units_y"] = ""

            mi = len(self.matched_rows)
            self.matched_rows.append(md)
            vals = tuple(str(md.get(c, "")) for c in self.match_columns)
            self.match_table.insert("", "end", values=vals + (str(mi),))
            self.clear_selection()
            messagebox.showinfo("Match Created", "Match created successfully!")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def delete_selected_match(self):
        sel = self.match_table.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a match to delete.")
            return
        for item in sel:
            self.match_table.delete(item)
        self.rebuild_matches_from_table()
        self.update_plot()

    def rebuild_matches_from_table(self):
        self.matched_rows.clear()
        self.match_to_indices.clear()
        self.index_to_matches.clear()
        for i, item in enumerate(self.match_table.get_children()):
            values = self.match_table.item(item)["values"]
            md = {}
            for j, col in enumerate(self.match_columns):
                md[col] = str(values[j]) if j < len(values) and values[j] else ""
            self.matched_rows.append(md)
            nv = list(values[: len(self.match_columns)]) + [str(i)]
            self.match_table.item(item, values=nv)

    def export_matches(self):
        if not self.matched_rows:
            messagebox.showwarning("No Matches", "No matches to export.")
            return
        path = filedialog.asksaveasfilename(title="Export matches", defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            pd.DataFrame(self.matched_rows, columns=self.match_columns).to_csv(path, index=False)
            messagebox.showinfo("Exported", f"Exported {len(self.matched_rows)} matches to {path}")
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    def load_matches(self):
        path = filedialog.askopenfilename(title="Load matches",
                                          filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            mdf = pd.read_csv(path)
            mdf = mdf.rename(columns={c: c.strip().lower() for c in mdf.columns})
            for item in self.match_table.get_children():
                self.match_table.delete(item)
            self.matched_rows.clear()
            for _, row in mdf.iterrows():
                md = {c: str(row.get(c.lower(), "")) if pd.notna(row.get(c.lower(), "")) else "" for c in self.match_columns}
                mi = len(self.matched_rows)
                self.matched_rows.append(md)
                self.match_table.insert("", "end", values=tuple(md.get(c, "") for c in self.match_columns) + (str(mi),))
            self.rebuild_matches_from_table()
            self.update_plot()
            messagebox.showinfo("Loaded", f"Loaded {len(self.matched_rows)} matches.")
        except Exception as exc:
            messagebox.showerror("Load Error", str(exc))

    def auto_match_current_screen(self):
        if self.df is None or not self.selected_screen.get():
            messagebox.showwarning("No Data", "Load data and select a screen first.")
            return
        screen = self.selected_screen.get()
        sdf = self.df[self.df["Screen"] == screen]
        plcs = sdf[sdf["type"] == "PLC_Tag"]
        texts = sdf[sdf["type"] == "Text"]
        if plcs.empty:
            messagebox.showinfo("Auto Match", "No PLC_Tags on this screen.")
            return
        radius = float(self.auto_radius_var.get() or 140.0)
        created = 0
        for _, plc in plcs.iterrows():
            md = {c: "" for c in self.match_columns}
            md["screen"] = screen
            md["plc_path"] = self.format_tag_name(str(plc["value"]))
            md["plc_x"] = float(plc["x"])
            md["plc_y"] = float(plc["y"])
            if not texts.empty:
                d = np.sqrt((texts["x"] - plc["x"]) ** 2 + (texts["y"] - plc["y"]) ** 2)
                ci = d.idxmin()
                if d.min() <= radius:
                    c = texts.loc[ci]
                    md["target_id"] = str(c["value"])
                    md["target_id_x"] = float(c["x"])
                    md["target_id_y"] = float(c["y"])
            if md["target_id"]:
                mi = len(self.matched_rows)
                self.matched_rows.append(md)
                self.match_table.insert("", "end",
                                        values=tuple(str(md.get(c, "")) for c in self.match_columns) + (str(mi),))
                created += 1
        self.rebuild_matches_from_table()
        self.update_plot()
        messagebox.showinfo("Auto Match", f"Created {created} auto-matches.")

    # ================================================================== #
    #  Table editing
    # ================================================================== #
    def start_cell_edit(self, event):
        if self._edit_entry is not None:
            return
        if self.match_table.identify("region", event.x, event.y) != "cell":
            return
        item_id = self.match_table.identify_row(event.y)
        col_id = self.match_table.identify_column(event.x)
        if not item_id or not col_id:
            return
        ci = int(col_id.replace("#", "")) - 1
        if ci < 0 or ci >= len(self.match_columns):
            return
        col = self.match_columns[ci]
        bbox = self.match_table.bbox(item_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        val = self.match_table.set(item_id, col)
        self._edit_item_id = item_id
        self._edit_col = col
        entry = tk.Entry(self.match_table)
        entry.insert(0, val)
        entry.select_range(0, tk.END)
        entry.focus_set()
        entry.place(x=x, y=y, width=w, height=h)
        entry.bind("<Return>", self.commit_cell_edit)
        entry.bind("<Escape>", self.cancel_cell_edit)
        entry.bind("<FocusOut>", self.commit_cell_edit)
        self._edit_entry = entry

    def commit_cell_edit(self, _event=None):
        if self._edit_entry is None:
            return
        nv = self._edit_entry.get()
        self.match_table.set(self._edit_item_id, self._edit_col, nv)
        self._edit_entry.destroy()
        self._edit_entry = None
        self.rebuild_matches_from_table()

    def cancel_cell_edit(self, _event=None):
        if self._edit_entry is None:
            return
        self._edit_entry.destroy()
        self._edit_entry = None

    def show_context_menu(self, event):
        item = self.match_table.identify_row(event.y)
        if item:
            self.match_table.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete Match", command=self.delete_selected_match)
        menu.add_separator()
        menu.add_command(label="Export All", command=self.export_matches)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


# ============================================================================
# Entry point
# ============================================================================
def main():
    try:
        app = TagMatcherApp()
        app.mainloop()
    except Exception as exc:
        print(f"Fatal error: {exc}")
        try:
            messagebox.showerror("Fatal Error", str(exc))
        except Exception:
            pass


if __name__ == "__main__":
    main()
