#!/usr/bin/env python3
"""
main.py - Entrypoint and Graphical Interface Controller Suite for v4.1
"""

import os
import sys
import threading
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    FigureCanvasTkAgg = None

from config import *
from utils import bind_mouse_wheel, _add_placeholder, _get_val
from core_engine import fetch_journals_for_keywords, run_download, compile_live_api_trends, fetch_live_world_states


def resource_path(filename):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(
        os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


class GenericSelectorDialog(ctk.CTkToplevel):
    def __init__(self, parent, title_text, items_list, current_selections):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("520x600")
        self.configure(fg_color=BG_PANEL)
        self.grab_set()

        try:
            ico_path = resource_path("biblioblitz.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            if hasattr(parent, '_icon_img'):
                self.wm_iconphoto(True, parent._icon_img)
        except Exception:
            pass

        self._all_items = items_list
        self._vars = {c: tk.BooleanVar(value=True)
                      for c in current_selections if c in items_list}
        self._filtered = list(items_list)
        self._build()

    def _var_for(self, item):
        if item not in self._vars:
            self._vars[item] = tk.BooleanVar(value=False)
        return self._vars[item]

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(top, text="🔍 Filter:", font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ,
                     weight="bold"), text_color=TEXT_BRIGHT).pack(side="left", padx=(0, 8))

        self._s_var = tk.StringVar()
        self._s_var.trace_add("write", self._on_filter)
        ctk.CTkEntry(top, textvariable=self._s_var, height=34, fg_color=BG_ENTRY,
                     border_color=BORDER_CLR, text_color=TEXT_BRIGHT).pack(side="left", fill="x", expand=True)

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_CARD, corner_radius=8, scrollbar_button_color=BORDER_CLR)
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        bind_mouse_wheel(self._scroll, self._scroll)

        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=14, pady=12)
        ctk.CTkButton(bf, text="✔ Lock Parameters", fg_color=ACCENT_BLUE, text_color=BG_ENTRY, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), command=self._confirm).pack(fill="x")
        self._render()

    def _render(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        q = self._s_var.get().lower() if hasattr(self, "_s_var") else ""
        if q == self._last_q:
            return
        self._last_q = q

        for item in sorted(self._all_items, key=str.lower):
            if q and q not in item.lower():
                continue
            var = self._vars[item]
            cb = ctk.CTkCheckBox(self._scroll, text=item, variable=self._var_for(item), font=ctk.CTkFont(
                family=FONT_FAMILY, size=FONT_ENTRY_SZ), text_color=TEXT_BRIGHT, fg_color=ACCENT_TEAL, border_color=BORDER_CLR)
            cb.pack(anchor="w", padx=8, pady=3)
            bind_mouse_wheel(cb, self._scroll)

    def _on_filter(self, *_):
        if hasattr(self, "_filter_job"):
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(180, self._apply_filter)

    def _apply_filter(self):
        q = self._s_var.get().lower()
        self._filtered = [c for c in self._all_items if q in c.lower()]
        self._render()

    def _confirm(self):
        self._selected = [c for c, v in self._vars.items() if v.get()]
        self.destroy()

    def get_selected(self):
        return getattr(self, "_selected", [])


class GroupedJournalSelectorDialog(GenericSelectorDialog):
    def __init__(self, parent, title_text, journal_items, current_selections):
        self._journal_items = journal_items
        self._filter_job = None
        self._last_q = None
        labels = [
            f"{j.get('publisher') or 'Other journals'} :: {j['journal']}"
            for j in journal_items
        ]
        super().__init__(parent, title_text, labels, current_selections)

    def _on_filter(self, *_):
        if self._filter_job:
            self.after_cancel(self._filter_job)
        self._filter_job = self.after(200, self._render)

    def _render(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        q = self._s_var.get().lower() if hasattr(self, "_s_var") else ""
        if q == self._last_q:
            return
        self._last_q = q

        grouped = {}
        for item in self._all_items:
            if q and q not in item.lower():
                continue
            publisher, journal = item.split("::", 1)
            grouped.setdefault(publisher.strip(), []).append(
                (journal.strip(), item))

        render_limit = 500
        rendered = 0
        total_matches = sum(len(items) for items in grouped.values())
        notice = "Type a journal or publication house name to filter." if not q else f"Showing up to {render_limit} of {total_matches} matches."
        ctk.CTkLabel(self._scroll, text=notice, font=ctk.CTkFont(
            family=FONT_FAMILY, size=10), text_color=TEXT_MID).pack(anchor="w", padx=8, pady=(4, 8))

        for publisher in sorted(grouped, key=str.lower):
            if rendered >= render_limit:
                break
            ctk.CTkLabel(self._scroll, text=publisher, font=ctk.CTkFont(
                family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
                text_color=ACCENT_BLUE).pack(anchor="w", padx=8, pady=(10, 2))
            for journal, item in sorted(grouped[publisher], key=lambda x: x[0].lower()):
                if rendered >= render_limit:
                    break
                cb = ctk.CTkCheckBox(self._scroll, text=journal, variable=self._var_for(item), font=ctk.CTkFont(
                    family=FONT_FAMILY, size=FONT_ENTRY_SZ), text_color=TEXT_BRIGHT, fg_color=ACCENT_TEAL, border_color=BORDER_CLR)
                cb.pack(anchor="w", padx=24, pady=3)
                bind_mouse_wheel(cb, self._scroll)
                rendered += 1


class BiblioBlitzApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "AyanavaPoddar.BiblioBlitz.WorkspaceSuite")
            except Exception:
                pass
        self.title(f"{APP_NAME}")
        self.geometry("1280x880")
        self.minsize(1100, 780)

        self._zoom_factor = 1.0
        self._running = False
        self._stop_event = threading.Event()

        self._selected_journals = []
        self._fetched_journals = []
        self._selected_countries = []
        self._selected_states = []
        self._active_states_pool = []

        try:
            ico_path = resource_path("biblioblitz.ico")
            p_path = resource_path("biblioblitz.png")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            if os.path.exists(p_path):
                self._icon_img = tk.PhotoImage(file=p_path)
                self.wm_iconphoto(True, self._icon_img)
        except Exception:
            pass

        self._build_ui_shell()

    def _build_ui_shell(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_HEADER,
                           height=70, corner_radius=0)
        hdr.pack(fill="x", side="top")

        lbl_f = ctk.CTkFrame(hdr, fg_color="transparent")
        lbl_f.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(lbl_f, text=APP_NAME, font=ctk.CTkFont(
            family=FONT_FAMILY, size=24, weight="bold"), text_color=BORDER_CLR).pack(anchor="w")
        ctk.CTkLabel(lbl_f, text=APP_TAGLINE, font=ctk.CTkFont(
            family=FONT_FAMILY, size=11, weight="bold"), text_color=TEXT_MID).pack(anchor="w")

        z_f = ctk.CTkFrame(hdr, fg_color="transparent")
        z_f.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(z_f, text="🔍 Zoom In (+)", width=110, height=32, font=ctk.CTkFont(family=FONT_FAMILY, size=11,
                      weight="bold"), fg_color=ACCENT_BLUE, command=lambda: self._apply_ui_zoom(0.1)).pack(side="left", padx=4)
        ctk.CTkButton(z_f, text="🔍 Zoom Out (-)", width=110, height=32, font=ctk.CTkFont(family=FONT_FAMILY, size=11,
                      weight="bold"), fg_color=ACCENT_BLUE, command=lambda: self._apply_ui_zoom(-0.1)).pack(side="left", padx=4)

        self.tabs = ctk.CTkTabview(self, fg_color="transparent", segmented_button_selected_color=ACCENT_BLUE,
                                   segmented_button_unselected_color=BG_CARD, text_color=TEXT_BRIGHT)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=5)

        self.tab_acq = self.tabs.add("Data Acquisition Platform")
        self.tab_stats = self.tabs.add("Scholarly Trend Statistics")
        self.tab_prog = self.tabs.add("Systematic Literature Review (SLR)")

        self._build_acquisition_tab(self.tab_acq)
        self._build_statistics_tab(self.tab_stats)
        self._build_progress_tab(self.tab_prog)

    def _apply_ui_zoom(self, delta):
        new_zoom = max(0.8, min(1.6, self._zoom_factor + delta))
        if new_zoom != self._zoom_factor:
            self._zoom_factor = new_zoom
            ctk.set_widget_scaling(new_zoom)
            ctk.set_window_scaling(new_zoom)

    def _field_label(self, parent, text, hint=None):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ,
                     weight="bold"), text_color=TEXT_BRIGHT).pack(anchor="w", padx=14, pady=(6, 1))
        if hint:
            ctk.CTkLabel(parent, text=hint, font=ctk.CTkFont(
                family=FONT_FAMILY, size=FONT_ENTRY_SZ-2), text_color=TEXT_MID).pack(anchor="w", padx=14, pady=(0, 2))

    def _build_acquisition_tab(self, parent):
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True)

        left = ctk.CTkScrollableFrame(body, width=420, fg_color=BG_PANEL, corner_radius=12,
                                      border_width=1, border_color=BORDER_CLR, scrollbar_button_color=BORDER_CLR)
        left.pack(side="left", fill="y", padx=(0, 10))
        bind_mouse_wheel(left, left)

        self._field_label(left, "📧 User Handshake Email Connection String")
        self._e_email = ctk.CTkEntry(left, height=36, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ), fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT)
        self._e_email.pack(fill="x", padx=14, pady=(0, 10))
        _add_placeholder(self._e_email, "academic@university.edu")

        self._field_label(left, "📁 Target Download Folder Destination")
        df = ctk.CTkFrame(left, fg_color="transparent")
        df.pack(fill="x", padx=14, pady=(0, 10))
        self.v_dir = ctk.StringVar(value=str(Path.home() / "BiblioBlitz_Data"))
        ctk.CTkEntry(df, textvariable=self.v_dir, height=36, font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
                     fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(df, text="Browse...", width=90, height=36, fg_color=ACCENT_BLUE, text_color=BG_ROOT, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"), command=self._browse_dir).pack(side="right")

        self._field_label(left, "🔍 Primary Search Keyword Filter String")
        self._e_keywords = ctk.CTkEntry(left, height=36, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ), fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT)
        self._e_keywords.pack(fill="x", padx=14, pady=(0, 8))
        _add_placeholder(self._e_keywords,
                         "e.g. soil erosion, rainfall runoff")

        self._btn_fetch_j = ctk.CTkButton(left, text="🔎 Extract Mapped Publication Portals", height=34, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"), fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT, command=self._fetch_journals_triggered)
        self._btn_fetch_j.pack(fill="x", padx=14, pady=(0, 4))

        self._lbl_j_status = ctk.CTkLabel(left, text="No active journal index logs generated.", font=ctk.CTkFont(
            family=FONT_FAMILY, size=10, weight="bold"), text_color=TEXT_MID)
        self._lbl_j_status.pack(anchor="w", padx=14, pady=(0, 4))

        self._btn_select_j = ctk.CTkButton(left, text="📋 Select Publication Venues Filter", height=34, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"), fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT, state="disabled", command=self._open_journal_ui)
        self._btn_select_j.pack(fill="x", padx=14, pady=(0, 12))

        self._field_label(left, "🌍 Filter Geographic Country Demographics")
        self._btn_select_country = ctk.CTkButton(left, text="Select Countries (Global Active)", height=34, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"), fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT, command=self._open_countries_ui)
        self._btn_select_country.pack(fill="x", padx=14, pady=(0, 12))

        # FIXED: STARTS AS DISABLED. TURNS ON AUTOMATICALLY AFTER A COUNTRY IS SELECTED
        self._field_label(left, "🏛️ State / Administrative Division Bounds")
        self._btn_select_st = ctk.CTkButton(left, text="🔒 Select Country First to Unlock States", height=34, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"), fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_DIM, state="disabled", command=self._open_states_ui)
        self._btn_select_st.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkLabel(left, text="States load from the bundled global CSV catalogue.", font=ctk.CTkFont(
            family=FONT_FAMILY, size=10), text_color=TEXT_MID).pack(anchor="w", padx=14, pady=(0, 12))

        self._field_label(left, "📦 Maximum Yield Dataset Record Limit")
        self.v_max = ctk.IntVar(value=1000)
        mf = ctk.CTkFrame(left, fg_color="transparent")
        mf.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkEntry(mf, textvariable=self.v_max, width=75, height=34, fg_color=BG_ENTRY, border_color=BORDER_CLR,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ)).pack(side="left", padx=(0, 6))
        ctk.CTkSlider(mf, from_=50, to=100000, variable=self.v_max, button_color=ACCENT_BLUE,
                      progress_color=BORDER_CLR).pack(side="left", fill="x", expand=True)

        self._field_label(left, "📅 Minimum Publication Year Lower Bound")
        self.v_year = ctk.IntVar(value=2019)
        yf = ctk.CTkFrame(left, fg_color="transparent")
        yf.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkEntry(yf, textvariable=self.v_year, width=75, height=34, fg_color=BG_ENTRY, border_color=BORDER_CLR,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ)).pack(side="left", padx=(0, 6))
        ctk.CTkSlider(yf, from_=1995, to=2026, variable=self.v_year, button_color=ACCENT_BLUE,
                      progress_color=BORDER_CLR).pack(side="left", fill="x", expand=True)

        right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=12,
                             border_width=1, border_color=BORDER_CLR)
        right.pack(side="left", fill="both", expand=True)

        r_hdr = ctk.CTkFrame(right, fg_color="transparent")
        r_hdr.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(r_hdr, text="Transaction Pipeline Output Ledger", font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), text_color=TEXT_BRIGHT).pack(side="left")
        ctk.CTkButton(r_hdr, text="Flush Screen", width=100, height=26, fg_color=BG_PANEL, border_width=1, border_color=BORDER_CLR,
                      text_color=TEXT_BRIGHT, font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), command=self._clear_log).pack(side="right")

        self._log = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG_ENTRY,
                                   text_color=TEXT_BRIGHT, border_width=1, border_color=BORDER_CLR, corner_radius=8, wrap="none")
        self._log.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._log.configure(state="disabled")

        for tag, color in [("step", "#457B9D"), ("info", "#1D3557"), ("success", "#2A9D8F"), ("warn", "#D68C45"), ("error", "#E63946"), ("sep", BORDER_CLR), ("done", "#2A9D8F")]:
            self._log.tag_config(tag, foreground=color)

        foot = ctk.CTkFrame(parent, fg_color=BG_FOOTER, height=75,
                            corner_radius=12, border_width=1, border_color=BORDER_CLR)
        foot.pack(fill="x", side="bottom", pady=(8, 0))
        foot.pack_propagate(False)

        self._pbar = ctk.CTkProgressBar(
            foot, height=4, mode="indeterminate", progress_color=ACCENT_BLUE, fg_color=BG_CARD)
        self._pbar.pack(fill="x")
        self._pbar.set(0)

        b_row = ctk.CTkFrame(foot, fg_color="transparent")
        b_row.pack(fill="x", padx=14, pady=12)

        self._btn_pdf = ctk.CTkButton(b_row, text="📥 Download PDFs Only", height=38, fg_color=ACCENT_BLUE, text_color=BG_ENTRY, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), command=lambda: self._start_download_pipeline("pdf"))
        self._btn_pdf.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._btn_csv = ctk.CTkButton(b_row, text="📊 Build CSV Index Mapping Only", height=38, fg_color=ACCENT_PURP, text_color=BG_ENTRY, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), command=lambda: self._start_download_pipeline("csv"))
        self._btn_csv.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._btn_both = ctk.CTkButton(b_row, text="✨ Execute Download Both (PDF+CSV)", height=38, fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
                                       font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), command=lambda: self._start_download_pipeline("both"))
        self._btn_both.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._btn_stop = ctk.CTkButton(b_row, text="⏹ Kill", height=38, width=80, fg_color="#E63946", text_color=BG_ENTRY, font=ctk.CTkFont(
            family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), state="disabled", command=self._stop_pipeline)
        self._btn_stop.pack(side="right")

    def _build_statistics_tab(self, parent):
        top_bar = ctk.CTkFrame(
            parent, fg_color=BG_PANEL, corner_radius=12, border_width=1, border_color=BORDER_CLR)
        top_bar.pack(fill="x", padx=14, pady=10)

        f_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        f_row.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(f_row, text="🔍 Keyword Filter:", font=ctk.CTkFont(family=FONT_FAMILY,
                     size=FONT_LABEL_SZ, weight="bold"), text_color=TEXT_BRIGHT).pack(side="left", padx=(0, 4))
        self._e_stat_kw = ctk.CTkEntry(f_row, width=280, height=36, fg_color=BG_ENTRY,
                                       border_color=BORDER_CLR, font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ))
        self._e_stat_kw.pack(side="left", padx=(0, 16))
        _add_placeholder(self._e_stat_kw, "Insert analysis phrase parameter")

        ctk.CTkLabel(f_row, text="📅 Year From:", font=ctk.CTkFont(family=FONT_FAMILY,
                     size=FONT_LABEL_SZ, weight="bold"), text_color=TEXT_BRIGHT).pack(side="left", padx=(0, 4))
        self._e_stat_yr = ctk.CTkEntry(f_row, width=90, height=36, fg_color=BG_ENTRY,
                                       border_color=BORDER_CLR, font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ))
        self._e_stat_yr.pack(side="left", padx=(0, 16))
        self._e_stat_yr.insert(0, "2018")

        self._btn_calc_trends = ctk.CTkButton(f_row, text="📈 Construct Dynamic Worldwide Live Trend Graphs", height=36, fg_color=ACCENT_TEAL,
                                              text_color=BG_ENTRY, font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"), command=self._trigger_live_trends_async)
        self._btn_calc_trends.pack(side="left", fill="x", expand=True)

        self._lbl_stat_notice = ctk.CTkLabel(top_bar, text="Status Core: Idle. Waiting for configuration vectors input strings.", font=ctk.CTkFont(
            family=FONT_FAMILY, size=11, weight="bold"), text_color=ACCENT_BLUE)
        self._lbl_stat_notice.pack(anchor="w", padx=14, pady=(0, 8))

        self._charts_scroll_box = ctk.CTkScrollableFrame(
            parent, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER_CLR, scrollbar_button_color=BORDER_CLR)
        self._charts_scroll_box.pack(
            fill="both", expand=True, padx=14, pady=(0, 12))
        bind_mouse_wheel(self._charts_scroll_box, self._charts_scroll_box)

    def _build_progress_tab(self, parent):
        box = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12,
                           border_width=1, border_color=BORDER_CLR)
        box.pack(fill="both", expand=True, padx=40, pady=40)

        inner = ctk.CTkFrame(box, width=550, height=220, fg_color=BG_CARD,
                             corner_radius=8, border_width=1, border_color=BORDER_CLR)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text="🚧 PIPELINE COMPONENT NOTICE 🚧", font=ctk.CTkFont(
            family=FONT_FAMILY, size=16, weight="bold"), text_color="#E63946").pack(pady=(40, 10))
        ctk.CTkLabel(inner, text="DEVELOPMENT UNDER PROGRESS", font=ctk.CTkFont(
            family=FONT_FAMILY, size=20, weight="bold"), text_color=BORDER_CLR).pack(pady=5)
        ctk.CTkLabel(inner, text="The Systematic Literature Review Parsing Engine is under modification.",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_MID).pack(pady=5)

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.v_dir.set(d)

    def _open_countries_ui(self):
        country_options = ["World"] + \
            [c for c in COUNTRIES if c != "Global (All Countries)"]
        dlg = GenericSelectorDialog(
            self, "Select Countries For Title Search", country_options, self._selected_countries)
        self.wait_window(dlg)
        self._selected_countries = dlg.get_selected()
        self._selected_states = []
        self._active_states_pool = []
        self._btn_select_country.configure(
            text=f"Selected Countries ({len(self._selected_countries)} Active)" if self._selected_countries else "Select Countries (Global Active)")
        self._on_country_selection_changed()

    # FIXED: CASCADING REGIONAL LOGIC TRIGGERS ON-DEMAND LIVE FETCH
    def _on_country_selection_changed(self):
        self._selected_states = []
        if not self._selected_countries:
            self._btn_select_st.configure(
                text="🔒 Select Country First to Unlock States", state="disabled", text_color=TEXT_DIM)
            return

        self._btn_select_st.configure(
            text="⚡ Retrieving World Regional Matrix...", state="disabled", text_color=ACCENT_PURP)

        def _async_lookup():
            states_pulled = []
            for country in self._selected_countries:
                for state in fetch_live_world_states(country):
                    states_pulled.append(f"{country} :: {state}")
            self._active_states_pool = sorted(set(states_pulled))

            def _ui_unlock():
                if self._active_states_pool:
                    self._btn_select_st.configure(
                        text=f"🏛️ Choose States ({len(self._active_states_pool)} Loaded)", state="normal", text_color=TEXT_BRIGHT)
                else:
                    self._btn_select_st.configure(
                        text="🏛️ Filter Subregions (Open Default)", state="normal", text_color=TEXT_BRIGHT)
            self.after(0, _ui_unlock)

        # Cleaned target binding to resolve the syntax crash
        threading.Thread(target=_async_lookup, daemon=True).start()

    def _open_journal_ui(self):
        if not self._fetched_journals:
            return
        dlg = GroupedJournalSelectorDialog(
            self, "Filter Mapped Target Journals Matrix", self._fetched_journals, self._selected_journals)
        self.wait_window(dlg)
        self._selected_journals = dlg.get_selected()
        self._btn_select_j.configure(
            text=f"📋 Target Venues Filter Set ({len(self._selected_journals)} Active)")

    def _open_states_ui(self):
        if not self._active_states_pool:
            return
        dlg = GenericSelectorDialog(
            self, "Filter Selected Country States", self._active_states_pool, self._selected_states)
        self.wait_window(dlg)
        self._selected_states = dlg.get_selected()
        self._btn_select_st.configure(
            text=f"🏛️ Selected States ({len(self._selected_states)} Active)")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _append_log(self, text, tag="info"):
        def _write():
            self._log.configure(state="normal")
            self._log.insert("end", text + "\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _write)

    def _fetch_journals_triggered(self):
        kw = _get_val(self._e_keywords)
        if not kw:
            self._append_log(
                "[ALERT] Ingestion fault. Provide search keywords phrase inputs first.", "error")
            return
        self._btn_fetch_j.configure(
            state="disabled", text="⚡ Processing Web Schemas...")

        def _async_run():
            res = fetch_journals_for_keywords(kw, self._append_log)
            self._fetched_journals = res

            def _ui_sync():
                self._btn_fetch_j.configure(
                    state="normal", text="🔎 Extract Mapped Publication Portals")
                self._lbl_j_status.configure(
                    text=f"✅ Formatted {len(res)} structural source options.", text_color=ACCENT_TEAL)
                self._btn_select_j.configure(state="normal")
            self.after(0, _ui_sync)
        threading.Thread(target=_async_run, daemon=True).start()

    def _start_download_pipeline(self, mode):
        kw = _get_val(self._e_keywords)
        if not kw:
            self._append_log(
                "[ALERT] Execution aborted. Write your search terms in the entry field box.", "error")
            messagebox.showerror(
                "Form Input Error", "Core search terms mapping cannot remain unassigned.")
            return
        if not _get_val(self._e_email) or "@" not in _get_val(self._e_email):
            messagebox.showerror(
                "Form Input Error", "Input a valid email parameters handshake identifier.")
            return

        self._clear_log()
        self._stop_event.clear()
        self._set_ui_state(True)

        params = dict(
            email=_get_val(self._e_email),
            download_dir=self.v_dir.get().strip().replace("\\", "/"),
            keywords=kw,
            max_results=int(self.v_max.get()),
            year_from=int(self.v_year.get()),
            selected_journals=list(self._selected_journals),
            countries=list(self._selected_countries),
            download_mode=mode,
            log_cb=self._append_log,
            stop_event=self._stop_event,
            states=list(self._selected_states),
            basins=[]
        )
        threading.Thread(target=self._pipeline_executor,
                         kwargs=params, daemon=True).start()

    def _pipeline_executor(self, **kwargs):
        try:
            run_download(**kwargs)
        except Exception as e:
            self._append_log(
                f"[CRITICAL ERR] Processing interrupted: {e}", "error")
        finally:
            self._set_ui_state(False)

    def _stop_pipeline(self):
        self._stop_event.set()
        self._append_log(
            "[KILL CALL] Sending shutdown signals across current process loops.", "warn")

    def _set_ui_state(self, is_running):
        self._running = is_running
        st = "disabled" if is_running else "normal"
        self._btn_pdf.configure(state=st)
        self._btn_csv.configure(state=st)
        self._btn_both.configure(state=st)
        self._btn_stop.configure(state="normal" if is_running else "disabled")
        if is_running:
            self._pbar.start()
        else:
            self._pbar.stop()
            self._pbar.set(0)

    def _update_stat_notice(self, msg, tag="info"):
        color = ACCENT_TEAL if tag == "success" else (
            "#E63946" if tag == "error" else ACCENT_BLUE)
        self.after(0, lambda: self._lbl_stat_notice.configure(
            text=f"Status: {msg}", text_color=color))

    def _trigger_live_trends_async(self):
        kw = _get_val(self._e_stat_kw)
        try:
            yr = int(self._e_stat_yr.get().strip())
        except:
            yr = 2018

        if not kw:
            messagebox.showerror(
                "Form Input Error", "Provide trend keywords values before executing live crawls.")
            return

        self._btn_calc_trends.configure(
            state="disabled", text="⚡ Processing Remote Matrix...")

        def _draw_chart(fig):
            for w in self._charts_scroll_box.winfo_children():
                w.destroy()
            canvas = FigureCanvasTkAgg(fig, master=self._charts_scroll_box)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        def _async_worker():
            try:
                def _render_on_main(fig):
                    self.after(0, lambda: _draw_chart(fig))

                compile_live_api_trends(
                    kw, yr, self._charts_scroll_box, self._update_stat_notice, _render_on_main)
            except Exception as e:
                self._update_stat_notice(
                    f"Error compiling graphs: {e}", "error")
            finally:
                self.after(0, lambda: self._btn_calc_trends.configure(
                    state="normal", text="📈 Construct Dynamic Worldwide Live Trend Graphs"))

        threading.Thread(target=_async_worker, daemon=True).start()


if __name__ == "__main__":
    app = BiblioBlitzApp()
    app.mainloop()
