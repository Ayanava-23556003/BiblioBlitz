#!/usr/bin/env python3
"""
tabs/tab_statistics.py - Scholarly Trend Statistics Tab Builder

Charts auto-generate after any download completes using the acquisition
keywords. Can also be triggered manually — keywords are always pulled
from the acquisition tab first, with the option to override here.
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

    The keyword field is pre-filled from the Acquisition tab automatically.
    Charts generated:
      1. Publications vs Year
      2. Publications vs Country (top 15)
      3. Publication Type pie
    """

    # ── Top control bar ───────────────────────────────────────────────────────
    top_bar = ctk.CTkFrame(
        parent, fg_color=BG_PANEL, corner_radius=12,
        border_width=1, border_color=BORDER_CLR)
    top_bar.pack(fill="x", padx=14, pady=(10, 6))

    # Hint line
    ctk.CTkLabel(
        top_bar,
        text="Keywords are sourced automatically from the Acquisition tab after download. "
             "You can also type a keyword and click Generate manually.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10),
        text_color=TEXT_MID,
        wraplength=900, justify="left"
    ).pack(anchor="w", padx=14, pady=(8, 2))

    f_row = ctk.CTkFrame(top_bar, fg_color="transparent")
    f_row.pack(fill="x", padx=14, pady=(4, 10))

    # Keyword entry (editable — user can override)
    ctk.CTkLabel(
        f_row, text="Keywords:",
        font=ctk.CTkFont(family=FONT_FAMILY,
                         size=FONT_LABEL_SZ, weight="bold"),
        text_color=TEXT_BRIGHT
    ).pack(side="left", padx=(0, 6))

    app._e_stat_kw = ctk.CTkEntry(
        f_row, width=340, height=36,
        fg_color=BG_ENTRY, border_color=BORDER_CLR,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ),
        placeholder_text="Auto-filled from Acquisition tab, or type here")
    app._e_stat_kw.pack(side="left", padx=(0, 16))

    # Year From
    ctk.CTkLabel(
        f_row, text="Year From:",
        font=ctk.CTkFont(family=FONT_FAMILY,
                         size=FONT_LABEL_SZ, weight="bold"),
        text_color=TEXT_BRIGHT
    ).pack(side="left", padx=(0, 6))

    app._e_stat_yr = ctk.CTkEntry(
        f_row, width=80, height=36,
        fg_color=BG_ENTRY, border_color=BORDER_CLR,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ))
    app._e_stat_yr.pack(side="left", padx=(0, 16))
    app._e_stat_yr.insert(0, "2018")

    # Generate button
    app._btn_calc_trends = ctk.CTkButton(
        f_row,
        text="Generate Worldwide Trend Graphs",
        height=36, fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY,
                         size=FONT_LABEL_SZ, weight="bold"),
        command=app._trigger_live_trends_async)
    app._btn_calc_trends.pack(side="left", fill="x", expand=True)

    # Status line
    app._lbl_stat_notice = ctk.CTkLabel(
        top_bar,
        text="Status: Idle — charts will auto-generate after download completes.",
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
        text="Charts will appear here after download completes\n"
             "or when you click Generate above.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=14),
        text_color=TEXT_DIM)
    app._stat_placeholder.pack(expand=True, pady=80)
