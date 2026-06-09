#!/usr/bin/env python3
"""
app.py - BiblioBlitzApp Main Window and Controller
"""

import sys
import ctypes
import threading

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
    YesNoDialog, ResultsTableDialog
)
from py.tabs.tab_acquisition import build_acquisition_tab
from py.tabs.tab_statistics import build_statistics_tab
from py.engine.journals import fetch_journals_for_keywords
from py.engine.downloader import run_download
from py.engine.trends import compile_live_api_trends


def resource_path(filename):
    import os
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(
        os.path.abspath(__file__)))
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

        self._selected_journals = []
        self._fetched_journals = []
        self._selected_countries = []

        # Stored after pipeline completes
        self._last_results = []
        self._last_country_data = []

        self._load_icon()
        self._build_ui_shell()

    # ── Icon ──────────────────────────────────────────────────────────────────

    def _load_icon(self):
        import os
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

    # ── Shell ─────────────────────────────────────────────────────────────────

    def _build_ui_shell(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_HEADER,
                           height=70, corner_radius=0)
        hdr.pack(fill="x", side="top")

        lbl_f = ctk.CTkFrame(hdr, fg_color="transparent")
        lbl_f.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(lbl_f, text=APP_NAME,
                     font=ctk.CTkFont(family=FONT_FAMILY,
                                      size=24, weight="bold"),
                     text_color=BORDER_CLR).pack(anchor="w")
        ctk.CTkLabel(lbl_f, text=APP_TAGLINE,
                     font=ctk.CTkFont(family=FONT_FAMILY,
                                      size=11, weight="bold"),
                     text_color=TEXT_MID).pack(anchor="w")

        z_f = ctk.CTkFrame(hdr, fg_color="transparent")
        z_f.pack(side="right", padx=16, pady=12)
        ctk.CTkButton(z_f, text="🔍 Zoom In (+)", width=110, height=32,
                      font=ctk.CTkFont(family=FONT_FAMILY,
                                       size=11, weight="bold"),
                      fg_color=ACCENT_BLUE,
                      command=lambda: self._apply_ui_zoom(0.1)).pack(side="left", padx=4)
        ctk.CTkButton(z_f, text="🔍 Zoom Out (-)", width=110, height=32,
                      font=ctk.CTkFont(family=FONT_FAMILY,
                                       size=11, weight="bold"),
                      fg_color=ACCENT_BLUE,
                      command=lambda: self._apply_ui_zoom(-0.1)).pack(side="left", padx=4)

        self.tabs = ctk.CTkTabview(
            self, fg_color="transparent",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_unselected_color=BG_CARD,
            text_color=TEXT_BRIGHT)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=5)

        tab_acq = self.tabs.add("Data Acquisition Platform")
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

    def _prompt_global_or_country(self):
        dlg = YesNoDialog(self, "Country Scope",
                          "Search globally (all countries)?")
        self.wait_window(dlg)
        if dlg.result:
            self._selected_countries = []
            self._btn_select_country.configure(
                text="Select Countries (Global Active)")
        else:
            country_options = [c for c in COUNTRIES if c !=
                               "Global (All Countries)"]
            sel_dlg = GenericSelectorDialog(
                self, "Select Countries For Title Search",
                country_options, self._selected_countries)
            self.wait_window(sel_dlg)
            self._selected_countries = sel_dlg.get_selected()
            self._btn_select_country.configure(
                text=(f"Countries Active ({len(self._selected_countries)})"
                      if self._selected_countries
                      else "Select Countries (Global Active)"))

    def _prompt_journal_filter(self):
        if not self._fetched_journals:
            messagebox.showinfo(
                "No Journals Loaded",
                "Click 'Extract Publication Portals' first to load journals.")
            return
        dlg = YesNoDialog(self, "Journal Filter",
                          "Filter results by specific journals?")
        self.wait_window(dlg)
        if dlg.result:
            self._open_journal_ui()
        else:
            self._selected_journals = []
            self._btn_select_j.configure(
                text="Filter by Journals (None — All Journals)")

    def _open_journal_ui(self):
        if not self._fetched_journals:
            return
        dlg = GroupedJournalSelectorDialog(
            self, "Filter Mapped Target Journals Matrix",
            self._fetched_journals, self._selected_journals)
        self.wait_window(dlg)
        self._selected_journals = dlg.get_selected()
        self._btn_select_j.configure(
            text=f"Journals Active ({len(self._selected_journals)} selected)"
            if self._selected_journals else "Filter by Journals (None — All Journals)")

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
                "[ALERT] Provide search keywords before fetching journals.", "error")
            return
        self._btn_fetch_j.configure(
            state="disabled", text="⚡ Processing Web Schemas...")

        def _async_run():
            res = fetch_journals_for_keywords(kw, self._append_log)
            self._fetched_journals = res

            def _ui_sync():
                self._btn_fetch_j.configure(
                    state="normal", text="Extract Publication Portals")
                self._lbl_j_status.configure(
                    text=f"✅ {len(res)} source options loaded.", text_color=ACCENT_TEAL)
                self._btn_select_j.configure(state="normal")
            self.after(0, _ui_sync)

        threading.Thread(target=_async_run, daemon=True).start()

    def _start_download_pipeline(self, mode):
        kw = _get_val(self._e_keywords)
        if not kw:
            self._append_log(
                "[ALERT] Execution aborted. Write your search terms first.", "error")
            messagebox.showerror("Form Input Error",
                                 "Core search terms cannot remain unassigned.")
            return
        email = _get_val(self._e_email)
        if not email or "@" not in email:
            messagebox.showerror("Form Input Error",
                                 "Input a valid email identifier.")
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
        threading.Thread(target=self._pipeline_executor,
                         kwargs=params, daemon=True).start()

    def _pipeline_executor(self, **kwargs):
        try:
            results = run_download(**kwargs)
            if results:
                self._last_results = results
                self._last_country_data = [
                    r.get("Country", "") for r in results if r.get("Country")
                ]
                self.after(0, self._auto_trigger_stats)
                self.after(400, self._show_results_table)
        except Exception as e:
            self._append_log(
                f"[CRITICAL ERR] Processing interrupted: {e}", "error")
        finally:
            self._set_ui_state(False)

    def _auto_trigger_stats(self):
        """
        After download completes:
        1. Copy acquisition keywords + year into the stats tab fields.
        2. Switch to the stats tab.
        3. Fire the trend generator.
        """
        kw = _get_val(self._e_keywords)
        if not kw:
            return

        # Push keywords and year into stats tab inputs
        try:
            self._e_stat_kw.delete(0, "end")
            self._e_stat_kw.insert(0, kw)
        except Exception:
            pass
        try:
            self._e_stat_yr.delete(0, "end")
            self._e_stat_yr.insert(0, str(self.v_year.get()))
        except Exception:
            pass

        self.tabs.set("Scholarly Trend Statistics")
        self._trigger_live_trends_async()

    def _show_results_table(self):
        if self._last_results:
            ResultsTableDialog(self, self._last_results)

    def _stop_pipeline(self):
        self._stop_event.set()
        self._append_log(
            "[KILL CALL] Sending shutdown signals across current process loops.", "warn")

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
            "#E63946" if tag == "error" else ACCENT_BLUE)
        self.after(0, lambda: self._lbl_stat_notice.configure(
            text=f"Status: {msg}", text_color=color))

    def _trigger_live_trends_async(self):
        """
        Resolve keywords: prefer stats tab entry if filled,
        otherwise fall back to the acquisition tab keywords.
        Year: prefer stats tab entry, else acquisition year.
        """
        kw = _get_val(self._e_stat_kw)
        if not kw:
            # Fall back to acquisition keywords
            kw = _get_val(self._e_keywords)

        if not kw:
            messagebox.showerror(
                "No Keywords",
                "Enter keywords in the Acquisition tab first, or type them in the stats bar.")
            return

        try:
            yr_raw = self._e_stat_yr.get().strip()
            yr = int(yr_raw) if yr_raw else int(self.v_year.get())
        except Exception:
            yr = 2018

        # Sync the stats entry box so the user can see what's running
        try:
            self._e_stat_kw.delete(0, "end")
            self._e_stat_kw.insert(0, kw)
        except Exception:
            pass

        self._btn_calc_trends.configure(
            state="disabled", text="⚡ Harvesting metadata worldwide...")

        country_snapshot = list(self._last_country_data)

        def _draw_chart(fig):
            for w in self._charts_scroll_box.winfo_children():
                w.destroy()
            if FigureCanvasTkAgg:
                canvas = FigureCanvasTkAgg(fig, master=self._charts_scroll_box)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        def _async_worker():
            try:
                compile_live_api_trends(
                    kw, yr,
                    self._charts_scroll_box,
                    self._update_stat_notice,
                    render_cb=lambda fig: self.after(
                        0, lambda: _draw_chart(fig)),
                    country_data=country_snapshot if country_snapshot else None
                )
            except Exception as e:
                self._update_stat_notice(
                    f"Error compiling graphs: {e}", "error")
            finally:
                self.after(0, lambda: self._btn_calc_trends.configure(
                    state="normal", text="Generate Worldwide Trend Graphs"))

        threading.Thread(target=_async_worker, daemon=True).start()
