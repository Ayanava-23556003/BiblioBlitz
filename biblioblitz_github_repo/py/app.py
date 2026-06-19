#!/usr/bin/env python3
"""
app.py - BiblioBlitzApp Main Window and Controller (v4.2)
"""

import sys
import ctypes
import threading
import os

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    FigureCanvasTkAgg = None

from py.config import (
    APP_NAME, APP_TAGLINE, FONT_FAMILY, FONT_LABEL_SZ,
    BG_HEADER, BG_CARD, BG_ENTRY,
    BORDER_CLR, ACCENT_BLUE, ACCENT_TEAL, ACCENT_PURP,
    TEXT_BRIGHT, TEXT_MID, TEXT_DIM,
    COUNTRIES,
)
from py.utils import bind_mouse_wheel, _get_val
from py.dialogs import (
    GenericSelectorDialog, GroupedJournalSelectorDialog,
    YesNoDialog, ConfirmCloseDialog, ResultsTableDialog
)
from py.tabs.tab_acquisition import build_acquisition_tab
from py.tabs.tab_statistics import build_statistics_tab
from py.engine.journals import fetch_journals_for_keywords
from py.engine.downloader import run_download
from py.engine.trends import compile_csv_trends


def resource_path(filename):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


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

        self.title(APP_NAME)
        self.geometry("1280x880")
        self.minsize(1100, 780)

        self._zoom_factor = 1.0
        self._running = False
        self._stop_event = threading.Event()

        # These are populated fresh at each download via the popup chain
        self._selected_journals = []
        self._fetched_journals = []
        self._selected_countries = []

        self._last_results = []
        self._last_csv_path = None   # path of the last saved metadata CSV

        self._load_icon()
        self._build_ui_shell()

        # Always ask before closing
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

    # ── Icon ──────────────────────────────────────────────────────────────────

    def _load_icon(self):
        try:
            ico_path = resource_path("biblioblitz.ico")
            p_path   = resource_path("biblioblitz.png")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
            if os.path.exists(p_path):
                self._icon_img = tk.PhotoImage(file=p_path)
                self.wm_iconphoto(True, self._icon_img)
        except Exception:
            pass

    # ── Close warning — always shown ──────────────────────────────────────────

    def _on_close_requested(self):
        """
        Always confirm before closing.
        If a download is running, show the abort-warning variant.
        Otherwise show a simple 'sure you want to quit?' prompt.
        """
        dlg = ConfirmCloseDialog(self, download_running=self._running)
        self.wait_window(dlg)
        if not dlg.result:
            return
        if self._running:
            self._stop_event.set()
        self.destroy()

    # ── Shell ─────────────────────────────────────────────────────────────────

    def _build_ui_shell(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_HEADER, height=70, corner_radius=0)
        hdr.pack(fill="x", side="top")

        lbl_f = ctk.CTkFrame(hdr, fg_color="transparent")
        lbl_f.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(lbl_f, text=APP_NAME,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
                     text_color=BORDER_CLR).pack(anchor="w")
        ctk.CTkLabel(lbl_f, text=APP_TAGLINE,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                     text_color=TEXT_MID).pack(anchor="w")

        z_f = ctk.CTkFrame(hdr, fg_color="transparent")
        z_f.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(z_f, text="🔍 Zoom In (+)", width=110, height=32,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                      fg_color=ACCENT_BLUE,
                      command=lambda: self._apply_ui_zoom(0.1)).pack(side="left", padx=4)
        ctk.CTkButton(z_f, text="🔍 Zoom Out (-)", width=110, height=32,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                      fg_color=ACCENT_BLUE,
                      command=lambda: self._apply_ui_zoom(-0.1)).pack(side="left", padx=4)

        self.tabs = ctk.CTkTabview(
            self, fg_color="transparent",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_unselected_color=BG_CARD,
            text_color=TEXT_BRIGHT)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=5)

        tab_acq   = self.tabs.add("Data Acquisition Platform")
        tab_stats = self.tabs.add("Scholarly Trend Statistics")

        build_acquisition_tab(self, tab_acq)
        build_statistics_tab(self, tab_stats)

    def _apply_ui_zoom(self, delta):
        new_zoom = max(0.8, min(1.6, self._zoom_factor + delta))
        if new_zoom != self._zoom_factor:
            self._zoom_factor = new_zoom
            ctk.set_widget_scaling(new_zoom)
            ctk.set_window_scaling(new_zoom)

    # ── Acquisition tab helpers ───────────────────────────────────────────────

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.v_dir.set(d)

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
            self._append_log("[ALERT] Provide search keywords before fetching journals.", "error")
            return
        self._btn_fetch_j.configure(state="disabled", text="⚡ Processing Web Schemas...")

        def _async_run():
            res = fetch_journals_for_keywords(kw, self._append_log)
            self._fetched_journals = res

            def _ui_sync():
                self._btn_fetch_j.configure(
                    state="normal", text="Extract Publication Portals")
                self._lbl_j_status.configure(
                    text=f"✅ {len(res)} source options loaded.", text_color=ACCENT_TEAL)
            self.after(0, _ui_sync)

        threading.Thread(target=_async_run, daemon=True).start()

    # ── Download pipeline with popup chain ───────────────────────────────────

    def _start_download_pipeline(self, mode):
        """
        Entry point for both download buttons.
        Runs the popup chain on the main thread, then kicks off the
        background worker once the user has confirmed all selections.
        """
        kw = _get_val(self._e_keywords)
        if not kw:
            self._append_log("[ALERT] Execution aborted. Write your search terms first.", "error")
            messagebox.showerror("Form Input Error", "Core search terms cannot remain unassigned.")
            return
        email = _get_val(self._e_email)
        if not email or "@" not in email:
            messagebox.showerror("Form Input Error", "Input a valid email identifier.")
            return

        # Run the blocking popup chain on the main thread
        # (safe because we haven't started the download thread yet)
        if not self._run_filter_popup_chain():
            # User cancelled somewhere in the chain
            return

        self._clear_log()
        self._stop_event.clear()
        self._set_ui_state(True)

        params = dict(
            email=email,
            download_dir=self.v_dir.get().strip().replace("\\", "/"),
            keywords=kw,
            max_results=int(self.v_max.get()),
            year_from=int(self.v_year.get()),
            selected_journals=list(self._selected_journals),
            countries=list(self._selected_countries),
            download_mode=mode,
            log_cb=self._append_log,
            stop_event=self._stop_event,
        )
        threading.Thread(target=self._pipeline_executor, kwargs=params, daemon=True).start()

    def _run_filter_popup_chain(self):
        """
        Sequential modal popup chain called before every download.

        Step 1 — Journal filter
          Yes → open journal multi-select window
          No  → use all journals

        Step 2 — Country scope
          Yes → open country multi-select window
          No  → global (no country filter)

        Returns True if the user completed the chain, False if they cancelled.
        """
        # ── Step 1: Journal filter ────────────────────────────────────────────
        jdlg = YesNoDialog(
            self,
            "Journal Filter",
            "Would you like to filter results by specific journals?\n\n"
            "Yes → select journals\n"
            "No  → include all journals"
        )
        self.wait_window(jdlg)
        # jdlg.result is None if user closed the window without choosing
        if jdlg.result is None:
            return False

        if jdlg.result:
            # Open journal multi-select
            if not self._fetched_journals:
                messagebox.showinfo(
                    "No Journals Available",
                    "No journal list has been loaded yet.\n"
                    "Click 'Extract Publication Portals' first, then try again.")
                return False
            sel_j = GroupedJournalSelectorDialog(
                self, "Select Target Journals",
                self._fetched_journals, self._selected_journals)
            self.wait_window(sel_j)
            self._selected_journals = sel_j.get_selected()
            self._append_log(
                f"[FILTER] Journals selected: "
                f"{len(self._selected_journals) if self._selected_journals else 'All'}", "step")
        else:
            self._selected_journals = []
            self._append_log("[FILTER] Journal filter: All journals included.", "step")

        # ── Step 2: Country scope ─────────────────────────────────────────────
        cdlg = YesNoDialog(
            self,
            "Country / Region Scope",
            "Would you like to restrict results to specific countries?\n\n"
            "Yes → select countries\n"
            "No  → global search (all countries)"
        )
        self.wait_window(cdlg)
        if cdlg.result is None:
            return False

        if cdlg.result:
            country_options = [c for c in COUNTRIES if c != "Global (All Countries)"]
            sel_c = GenericSelectorDialog(
                self, "Select Countries",
                country_options, self._selected_countries)
            self.wait_window(sel_c)
            self._selected_countries = sel_c.get_selected()
            self._append_log(
                f"[FILTER] Countries selected: "
                f"{', '.join(self._selected_countries) if self._selected_countries else 'All'}", "step")
        else:
            self._selected_countries = []
            self._append_log("[FILTER] Country scope: Global (all countries).", "step")

        return True

    # ── Pipeline executor (background thread) ─────────────────────────────────

    def _pipeline_executor(self, **kwargs):
        try:
            results = run_download(**kwargs)
            if results:
                self._last_results = results

                # Find the saved CSV path from the download dir
                download_dir = kwargs.get("download_dir", "")
                self._locate_and_load_csv(download_dir)

                self.after(400, self._show_results_table)
        except Exception as e:
            self._append_log(f"[CRITICAL ERR] Processing interrupted: {e}", "error")
        finally:
            self._set_ui_state(False)

    def _locate_and_load_csv(self, download_dir):
        """
        After a download finishes, find the most recently modified .csv
        in the download dir and automatically feed it to the stats engine.
        """
        import glob, time

        if not download_dir or not os.path.isdir(download_dir):
            self.after(0, lambda: self._update_stat_notice(
                "Download complete — upload the saved CSV to generate charts.", "info"))
            return

        csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
        if not csv_files:
            self.after(0, lambda: self._update_stat_notice(
                "No CSV found in the download folder. Upload manually.", "warn"))
            return

        # Pick the most recently modified csv
        latest = max(csv_files, key=os.path.getmtime)
        self._last_csv_path = latest

        from pathlib import Path as _P
        self._append_log(f"[STATS] Auto-loading CSV: {_P(latest).name}", "step")

        # Switch to stats tab and render
        self.after(0, self._auto_load_csv_to_stats)

    def _auto_load_csv_to_stats(self):
        if not self._last_csv_path:
            return
        from pathlib import Path as _P
        self.tabs.set("Scholarly Trend Statistics")
        self._lbl_csv_file.configure(text=f"Loaded: {_P(self._last_csv_path).name}")
        self._update_stat_notice("Rendering charts from downloaded metadata…", "info")
        self._btn_calc_trends.configure(state="disabled", text="⚡ Parsing metadata CSV...")

        def _worker():
            try:
                compile_csv_trends(
                    self._last_csv_path,
                    self._charts_scroll_box,
                    self._update_stat_notice,
                    render_cb=lambda fig: self.after(0, lambda f=fig: self._draw_chart(f)),
                )
            except Exception as e:
                self._update_stat_notice(f"Error rendering charts: {e}", "error")
            finally:
                self.after(0, lambda: self._btn_calc_trends.configure(
                    state="normal", text="📂 Upload CSV & Generate Charts"))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_results_table(self):
        if self._last_results:
            self.after(10, lambda: ResultsTableDialog(self, self._last_results))

    def _stop_pipeline(self):
        self._stop_event.set()
        self._append_log("[KILL CALL] Sending shutdown signals across current process loops.", "warn")

    def _set_ui_state(self, is_running):
        self._running = is_running
        st = "disabled" if is_running else "normal"
        self._btn_pdf.configure(state=st)
        self._btn_csv.configure(state=st)
        self._btn_stop.configure(state="normal" if is_running else "disabled")
        if is_running:
            self._pbar.start()
        else:
            self._pbar.stop()
            self._pbar.set(0)

    # ── Statistics tab helpers ────────────────────────────────────────────────

    def _update_stat_notice(self, msg, tag="info"):
        color = ACCENT_TEAL if tag in ("success", "done") else (
            "#E63946" if tag == "error" else
            "#D68C45" if tag == "warn" else ACCENT_BLUE)
        self.after(0, lambda: self._lbl_stat_notice.configure(
            text=f"Status: {msg}", text_color=color))

    def _trigger_csv_trends(self):
        """Manual CSV upload from the Statistics tab."""
        path = filedialog.askopenfilename(
            title="Select BiblioBlitz Metadata CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        from pathlib import Path as _P
        self._last_csv_path = path
        self._lbl_csv_file.configure(text=f"Loaded: {_P(path).name}")
        self._btn_calc_trends.configure(state="disabled", text="⚡ Parsing metadata CSV...")

        def _worker():
            try:
                compile_csv_trends(
                    path,
                    self._charts_scroll_box,
                    self._update_stat_notice,
                    render_cb=lambda fig: self.after(0, lambda f=fig: self._draw_chart(f)),
                )
            except Exception as e:
                self._update_stat_notice(f"Error compiling graphs: {e}", "error")
            finally:
                self.after(0, lambda: self._btn_calc_trends.configure(
                    state="normal", text="📂 Upload CSV & Generate Charts"))

        threading.Thread(target=_worker, daemon=True).start()

    def _draw_chart(self, fig):
        """Embed a matplotlib Figure inside the scrollable chart area."""
        # Clear old content (placeholder + previous charts)
        for w in self._charts_scroll_box.winfo_children():
            w.destroy()
        if FigureCanvasTkAgg:
            canvas = FigureCanvasTkAgg(fig, master=self._charts_scroll_box)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
