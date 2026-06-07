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
from py.dialogs import GenericSelectorDialog, GroupedJournalSelectorDialog
from py.tabs.tab_acquisition import build_acquisition_tab
from py.tabs.tab_statistics import build_statistics_tab
from py.tabs.tab_slr import build_slr_tab
from py.engine.geo import fetch_live_world_states
from py.engine.journals import fetch_journals_for_keywords
from py.engine.downloader import run_download
from py.engine.trends import compile_live_api_trends


def resource_path(filename):
    import os
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

        self._selected_journals = []
        self._fetched_journals = []
        self._selected_countries = []
        self._selected_states = []
        self._active_states_pool = []

        self._load_icon()
        self._build_ui_shell()

    # ── Icon ─────────────────────────────────────────────────────────────────

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
        tab_slr   = self.tabs.add("Systematic Literature Review (SLR)")

        build_acquisition_tab(self, tab_acq)
        build_statistics_tab(self, tab_stats)
        build_slr_tab(self, tab_slr)

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

    def _open_countries_ui(self):
        country_options = ["World"] + [c for c in COUNTRIES if c != "Global (All Countries)"]
        dlg = GenericSelectorDialog(
            self, "Select Countries For Title Search",
            country_options, self._selected_countries)
        self.wait_window(dlg)
        self._selected_countries = dlg.get_selected()
        self._selected_states = []
        self._active_states_pool = []
        self._btn_select_country.configure(
            text=(f"Selected Countries ({len(self._selected_countries)} Active)"
                  if self._selected_countries else "Select Countries (Global Active)"))
        self._on_country_selection_changed()

    def _on_country_selection_changed(self):
        self._selected_states = []
        if not self._selected_countries:
            self._btn_select_st.configure(
                text="🔒 Select Country First to Unlock States",
                state="disabled", text_color=TEXT_DIM)
            return

        self._btn_select_st.configure(
            text="⚡ Retrieving World Regional Matrix...",
            state="disabled", text_color=ACCENT_PURP)

        def _async_lookup():
            states_pulled = []
            for country in self._selected_countries:
                for state in fetch_live_world_states(country):
                    states_pulled.append(f"{country} :: {state}")
            self._active_states_pool = sorted(set(states_pulled))

            def _ui_unlock():
                if self._active_states_pool:
                    self._btn_select_st.configure(
                        text=f"🏛️ Choose States ({len(self._active_states_pool)} Loaded)",
                        state="normal", text_color=TEXT_BRIGHT)
                else:
                    self._btn_select_st.configure(
                        text="🏛️ Filter Subregions (Open Default)",
                        state="normal", text_color=TEXT_BRIGHT)
            self.after(0, _ui_unlock)

        threading.Thread(target=_async_lookup, daemon=True).start()

    def _open_journal_ui(self):
        if not self._fetched_journals:
            return
        dlg = GroupedJournalSelectorDialog(
            self, "Filter Mapped Target Journals Matrix",
            self._fetched_journals, self._selected_journals)
        self.wait_window(dlg)
        self._selected_journals = dlg.get_selected()
        self._btn_select_j.configure(
            text=f"📋 Target Venues Filter Set ({len(self._selected_journals)} Active)")

    def _open_states_ui(self):
        if not self._active_states_pool:
            return
        dlg = GenericSelectorDialog(
            self, "Filter Selected Country States",
            self._active_states_pool, self._selected_states)
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
        self._btn_fetch_j.configure(state="disabled", text="⚡ Processing Web Schemas...")

        def _async_run():
            res = fetch_journals_for_keywords(kw, self._append_log)
            self._fetched_journals = res

            def _ui_sync():
                self._btn_fetch_j.configure(
                    state="normal", text="🔎 Extract Mapped Publication Portals")
                self._lbl_j_status.configure(
                    text=f"✅ Formatted {len(res)} structural source options.",
                    text_color=ACCENT_TEAL)
                self._btn_select_j.configure(state="normal")
            self.after(0, _ui_sync)

        threading.Thread(target=_async_run, daemon=True).start()

    def _start_download_pipeline(self, mode):
        kw = _get_val(self._e_keywords)
        if not kw:
            self._append_log(
                "[ALERT] Execution aborted. Write your search terms in the entry field box.", "error")
            messagebox.showerror("Form Input Error",
                                 "Core search terms mapping cannot remain unassigned.")
            return
        if not _get_val(self._e_email) or "@" not in _get_val(self._e_email):
            messagebox.showerror("Form Input Error",
                                 "Input a valid email parameters handshake identifier.")
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
        threading.Thread(target=self._pipeline_executor, kwargs=params, daemon=True).start()

    def _pipeline_executor(self, **kwargs):
        try:
            run_download(**kwargs)
        except Exception as e:
            self._append_log(f"[CRITICAL ERR] Processing interrupted: {e}", "error")
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

    # ── Statistics tab helpers ────────────────────────────────────────────────

    def _update_stat_notice(self, msg, tag="info"):
        color = ACCENT_TEAL if tag == "success" else ("#E63946" if tag == "error" else ACCENT_BLUE)
        self.after(0, lambda: self._lbl_stat_notice.configure(
            text=f"Status: {msg}", text_color=color))

    def _trigger_live_trends_async(self):
        kw = _get_val(self._e_stat_kw)
        try:
            yr = int(self._e_stat_yr.get().strip())
        except Exception:
            yr = 2018

        if not kw:
            messagebox.showerror(
                "Form Input Error",
                "Provide trend keywords values before executing live crawls.")
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
                    kw, yr, self._charts_scroll_box,
                    self._update_stat_notice, _render_on_main)
            except Exception as e:
                self._update_stat_notice(f"Error compiling graphs: {e}", "error")
            finally:
                self.after(0, lambda: self._btn_calc_trends.configure(
                    state="normal",
                    text="📈 Construct Dynamic Worldwide Live Trend Graphs"))

        threading.Thread(target=_async_worker, daemon=True).start()
