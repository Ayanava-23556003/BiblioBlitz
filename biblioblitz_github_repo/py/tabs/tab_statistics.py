#!/usr/bin/env python3
"""
tabs/tab_statistics.py - Scholarly Trend Statistics Tab Builder

Charts are generated from a user-uploaded BiblioBlitz metadata CSV.
Deduplication is performed by DOI before charting.
"""

import customtkinter as ctk

from py.config import (
    FONT_FAMILY, FONT_LABEL_SZ, FONT_ENTRY_SZ,
    BG_PANEL, BG_CARD, BG_ENTRY,
    BORDER_CLR, ACCENT_BLUE, ACCENT_TEAL, TEXT_DIM,
    TEXT_BRIGHT, TEXT_MID,
)
from py.utils import bind_mouse_wheel


def build_statistics_tab(app, parent):
    """
    Builds the Scholarly Trend Statistics tab.

    Workflow:
      1. User downloads metadata CSV from the Acquisition tab.
      2. User clicks "Upload CSV & Generate Charts" here.
      3. The CSV is parsed, deduplicated by DOI, and three charts are rendered:
           - Publications vs Year
           - Publications by Country (top 20)
           - Publication Type distribution (pie)
    """

    # ── Top control bar ───────────────────────────────────────────────────────
    top_bar = ctk.CTkFrame(
        parent, fg_color=BG_PANEL, corner_radius=12,
        border_width=1, border_color=BORDER_CLR)
    top_bar.pack(fill="x", padx=14, pady=(10, 6))

    # Hint line
    ctk.CTkLabel(
        top_bar,
        text="Upload the BiblioBlitz metadata CSV you downloaded from the Acquisition tab. "
             "Charts are built directly from your data — no live API calls needed.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        text_color=TEXT_MID,
        wraplength=900, justify="left"
    ).pack(anchor="w", padx=14, pady=(8, 4))

    f_row = ctk.CTkFrame(top_bar, fg_color="transparent")
    f_row.pack(fill="x", padx=14, pady=(4, 10))

    # Upload & Generate button (primary action)
    app._btn_calc_trends = ctk.CTkButton(
        f_row,
        text="📂 Upload CSV & Generate Charts",
        height=38, fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY,
                         size=FONT_LABEL_SZ, weight="bold"),
        command=app._trigger_csv_trends)
    app._btn_calc_trends.pack(side="left", fill="x", expand=True, padx=(0, 8))

    # Tiny info label showing which file is loaded
    app._lbl_csv_file = ctk.CTkLabel(
        f_row,
        text="No file loaded",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        text_color=TEXT_DIM,
        anchor="w"
    )
    app._lbl_csv_file.pack(side="left", fill="x", expand=True)

    # Status line
    app._lbl_stat_notice = ctk.CTkLabel(
        top_bar,
        text="Status: Idle — upload a CSV to generate trend charts.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        text_color=ACCENT_BLUE)
    app._lbl_stat_notice.pack(anchor="w", padx=14, pady=(0, 8))

    # ── Scrollable chart area ─────────────────────────────────────────────────
    app._charts_scroll_box = ctk.CTkScrollableFrame(
        parent, fg_color=BG_CARD, corner_radius=12,
        border_width=1, border_color=BORDER_CLR,
        scrollbar_button_color=BORDER_CLR)
    app._charts_scroll_box.pack(
        fill="both", expand=True, padx=14, pady=(0, 12))
    bind_mouse_wheel(app._charts_scroll_box, app._charts_scroll_box)

    # Placeholder text shown before first run
    app._stat_placeholder = ctk.CTkLabel(
        app._charts_scroll_box,
        text="📊  Charts will appear here after you upload a metadata CSV.\n\n"
             "Download metadata first from the Acquisition tab, then\n"
             "click  📂 Upload CSV & Generate Charts  above.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        text_color=TEXT_DIM,
        justify="center")
    app._stat_placeholder.pack(expand=True, pady=80)
