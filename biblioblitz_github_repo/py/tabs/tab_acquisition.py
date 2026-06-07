#!/usr/bin/env python3
"""
tabs/tab_acquisition.py - Data Acquisition Platform Tab Builder
"""

from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

from py.config import (
    FONT_FAMILY, FONT_LABEL_SZ, FONT_ENTRY_SZ,
    BG_PANEL, BG_CARD, BG_ENTRY, BG_FOOTER, BG_ROOT,
    BORDER_CLR, ACCENT_BLUE, ACCENT_TEAL, ACCENT_PURP,
    TEXT_BRIGHT, TEXT_MID, TEXT_DIM,
    COUNTRIES,
)
from py.utils import bind_mouse_wheel, _add_placeholder, _get_val


def build_acquisition_tab(app, parent):
    """
    Builds the Data Acquisition Platform tab.
    Writes UI references back to `app` so handlers can reach them.
    """
    body = ctk.CTkFrame(parent, fg_color="transparent")
    body.pack(fill="both", expand=True)

    # ── Left panel (controls) ────────────────────────────────────────────────
    left = ctk.CTkScrollableFrame(
        body, width=420, fg_color=BG_PANEL, corner_radius=12,
        border_width=1, border_color=BORDER_CLR, scrollbar_button_color=BORDER_CLR)
    left.pack(side="left", fill="y", padx=(0, 10))
    bind_mouse_wheel(left, left)

    def field_label(text, hint=None):
        ctk.CTkLabel(left, text=text,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
                     text_color=TEXT_BRIGHT).pack(anchor="w", padx=14, pady=(6, 1))
        if hint:
            ctk.CTkLabel(left, text=hint,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ - 2),
                         text_color=TEXT_MID).pack(anchor="w", padx=14, pady=(0, 2))

    # Email
    field_label("📧 User Handshake Email Connection String")
    app._e_email = ctk.CTkEntry(
        left, height=36,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
        fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT)
    app._e_email.pack(fill="x", padx=14, pady=(0, 10))
    _add_placeholder(app._e_email, "academic@university.edu")

    # Download directory
    field_label("📁 Target Download Folder Destination")
    df = ctk.CTkFrame(left, fg_color="transparent")
    df.pack(fill="x", padx=14, pady=(0, 10))
    app.v_dir = ctk.StringVar(value=str(Path.home() / "BiblioBlitz_Data"))
    ctk.CTkEntry(
        df, textvariable=app.v_dir, height=36,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
        fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT
    ).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ctk.CTkButton(
        df, text="Browse...", width=90, height=36,
        fg_color=ACCENT_BLUE, text_color=BG_ROOT,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"),
        command=app._browse_dir
    ).pack(side="right")

    # Keywords
    field_label("🔍 Primary Search Keyword Filter String")
    app._e_keywords = ctk.CTkEntry(
        left, height=36,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
        fg_color=BG_ENTRY, border_color=BORDER_CLR, text_color=TEXT_BRIGHT)
    app._e_keywords.pack(fill="x", padx=14, pady=(0, 8))
    _add_placeholder(app._e_keywords, "e.g. soil erosion, rainfall runoff")

    # Fetch journals button
    app._btn_fetch_j = ctk.CTkButton(
        left, text="🔎 Extract Mapped Publication Portals", height=34,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"),
        fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT,
        command=app._fetch_journals_triggered)
    app._btn_fetch_j.pack(fill="x", padx=14, pady=(0, 4))

    app._lbl_j_status = ctk.CTkLabel(
        left, text="No active journal index logs generated.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
        text_color=TEXT_MID)
    app._lbl_j_status.pack(anchor="w", padx=14, pady=(0, 4))

    app._btn_select_j = ctk.CTkButton(
        left, text="📋 Select Publication Venues Filter", height=34,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"),
        fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT,
        state="disabled", command=app._open_journal_ui)
    app._btn_select_j.pack(fill="x", padx=14, pady=(0, 12))

    # Countries
    field_label("🌍 Filter Geographic Country Demographics")
    app._btn_select_country = ctk.CTkButton(
        left, text="Select Countries (Global Active)", height=34,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"),
        fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT,
        command=app._open_countries_ui)
    app._btn_select_country.pack(fill="x", padx=14, pady=(0, 12))

    # States (locked until country chosen)
    field_label("🏛️ State / Administrative Division Bounds")
    app._btn_select_st = ctk.CTkButton(
        left, text="🔒 Select Country First to Unlock States", height=34,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ, weight="bold"),
        fg_color=BG_CARD, border_width=1, border_color=BORDER_CLR, text_color=TEXT_DIM,
        state="disabled", command=app._open_states_ui)
    app._btn_select_st.pack(fill="x", padx=14, pady=(0, 4))
    ctk.CTkLabel(
        left, text="States load from the bundled global CSV catalogue.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10), text_color=TEXT_MID
    ).pack(anchor="w", padx=14, pady=(0, 12))

    # Max results
    field_label("📦 Maximum Yield Dataset Record Limit")
    import tkinter as tk
    app.v_max = ctk.IntVar(value=1000)
    mf = ctk.CTkFrame(left, fg_color="transparent")
    mf.pack(fill="x", padx=14, pady=(0, 10))
    ctk.CTkEntry(mf, textvariable=app.v_max, width=75, height=34,
                 fg_color=BG_ENTRY, border_color=BORDER_CLR,
                 font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ)
                 ).pack(side="left", padx=(0, 6))
    ctk.CTkSlider(mf, from_=50, to=100000, variable=app.v_max,
                  button_color=ACCENT_BLUE, progress_color=BORDER_CLR
                  ).pack(side="left", fill="x", expand=True)

    # Min year
    field_label("📅 Minimum Publication Year Lower Bound")
    app.v_year = ctk.IntVar(value=2019)
    yf = ctk.CTkFrame(left, fg_color="transparent")
    yf.pack(fill="x", padx=14, pady=(0, 10))
    ctk.CTkEntry(yf, textvariable=app.v_year, width=75, height=34,
                 fg_color=BG_ENTRY, border_color=BORDER_CLR,
                 font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ)
                 ).pack(side="left", padx=(0, 6))
    ctk.CTkSlider(yf, from_=1995, to=2026, variable=app.v_year,
                  button_color=ACCENT_BLUE, progress_color=BORDER_CLR
                  ).pack(side="left", fill="x", expand=True)

    # ── Right panel (log) ────────────────────────────────────────────────────
    right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=12,
                         border_width=1, border_color=BORDER_CLR)
    right.pack(side="left", fill="both", expand=True)

    r_hdr = ctk.CTkFrame(right, fg_color="transparent")
    r_hdr.pack(fill="x", padx=14, pady=10)
    ctk.CTkLabel(
        r_hdr, text="Transaction Pipeline Output Ledger",
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        text_color=TEXT_BRIGHT).pack(side="left")
    ctk.CTkButton(
        r_hdr, text="Flush Screen", width=100, height=26,
        fg_color=BG_PANEL, border_width=1, border_color=BORDER_CLR, text_color=TEXT_BRIGHT,
        font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        command=app._clear_log).pack(side="right")

    app._log = ctk.CTkTextbox(
        right, font=ctk.CTkFont(family="Consolas", size=12),
        fg_color=BG_ENTRY, text_color=TEXT_BRIGHT,
        border_width=1, border_color=BORDER_CLR, corner_radius=8, wrap="none")
    app._log.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    app._log.configure(state="disabled")

    for tag, color in [
        ("step", "#457B9D"), ("info", "#1D3557"), ("success", "#2A9D8F"),
        ("warn", "#D68C45"), ("error", "#E63946"), ("sep", BORDER_CLR), ("done", "#2A9D8F")
    ]:
        app._log.tag_config(tag, foreground=color)

    # ── Footer (progress + action buttons) ──────────────────────────────────
    foot = ctk.CTkFrame(parent, fg_color=BG_FOOTER, height=75,
                        corner_radius=12, border_width=1, border_color=BORDER_CLR)
    foot.pack(fill="x", side="bottom", pady=(8, 0))
    foot.pack_propagate(False)

    app._pbar = ctk.CTkProgressBar(
        foot, height=4, mode="indeterminate",
        progress_color=ACCENT_BLUE, fg_color=BG_CARD)
    app._pbar.pack(fill="x")
    app._pbar.set(0)

    b_row = ctk.CTkFrame(foot, fg_color="transparent")
    b_row.pack(fill="x", padx=14, pady=12)

    app._btn_pdf = ctk.CTkButton(
        b_row, text="📥 Download PDFs Only", height=38,
        fg_color=ACCENT_BLUE, text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        command=lambda: app._start_download_pipeline("pdf"))
    app._btn_pdf.pack(side="left", fill="x", expand=True, padx=(0, 4))

    app._btn_csv = ctk.CTkButton(
        b_row, text="📊 Build CSV Index Mapping Only", height=38,
        fg_color=ACCENT_PURP, text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        command=lambda: app._start_download_pipeline("csv"))
    app._btn_csv.pack(side="left", fill="x", expand=True, padx=(0, 4))

    app._btn_both = ctk.CTkButton(
        b_row, text="✨ Execute Download Both (PDF+CSV)", height=38,
        fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        command=lambda: app._start_download_pipeline("both"))
    app._btn_both.pack(side="left", fill="x", expand=True, padx=(0, 6))

    app._btn_stop = ctk.CTkButton(
        b_row, text="⏹ Kill", height=38, width=80,
        fg_color="#E63946", text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        state="disabled", command=app._stop_pipeline)
    app._btn_stop.pack(side="right")
