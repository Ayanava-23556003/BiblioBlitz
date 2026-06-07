#!/usr/bin/env python3
"""
tabs/tab_statistics.py - Scholarly Trend Statistics Tab Builder
"""

import customtkinter as ctk

from py.config import (
    FONT_FAMILY, FONT_LABEL_SZ, FONT_ENTRY_SZ,
    BG_PANEL, BG_CARD, BG_ENTRY,
    BORDER_CLR, ACCENT_BLUE, ACCENT_TEAL,
    TEXT_BRIGHT,
)
from py.utils import bind_mouse_wheel, _add_placeholder


def build_statistics_tab(app, parent):
    """
    Builds the Scholarly Trend Statistics tab.
    Writes UI references back to `app`.
    """
    top_bar = ctk.CTkFrame(
        parent, fg_color=BG_PANEL, corner_radius=12,
        border_width=1, border_color=BORDER_CLR)
    top_bar.pack(fill="x", padx=14, pady=10)

    f_row = ctk.CTkFrame(top_bar, fg_color="transparent")
    f_row.pack(fill="x", padx=14, pady=10)

    ctk.CTkLabel(
        f_row, text="🔍 Keyword Filter:",
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        text_color=TEXT_BRIGHT).pack(side="left", padx=(0, 4))

    app._e_stat_kw = ctk.CTkEntry(
        f_row, width=280, height=36,
        fg_color=BG_ENTRY, border_color=BORDER_CLR,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ))
    app._e_stat_kw.pack(side="left", padx=(0, 16))
    _add_placeholder(app._e_stat_kw, "Insert analysis phrase parameter")

    ctk.CTkLabel(
        f_row, text="📅 Year From:",
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        text_color=TEXT_BRIGHT).pack(side="left", padx=(0, 4))

    app._e_stat_yr = ctk.CTkEntry(
        f_row, width=90, height=36,
        fg_color=BG_ENTRY, border_color=BORDER_CLR,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_ENTRY_SZ))
    app._e_stat_yr.pack(side="left", padx=(0, 16))
    app._e_stat_yr.insert(0, "2018")

    app._btn_calc_trends = ctk.CTkButton(
        f_row, text="📈 Construct Dynamic Worldwide Live Trend Graphs",
        height=36, fg_color=ACCENT_TEAL, text_color=BG_ENTRY,
        font=ctk.CTkFont(family=FONT_FAMILY, size=FONT_LABEL_SZ, weight="bold"),
        command=app._trigger_live_trends_async)
    app._btn_calc_trends.pack(side="left", fill="x", expand=True)

    app._lbl_stat_notice = ctk.CTkLabel(
        top_bar,
        text="Status Core: Idle. Waiting for configuration vectors input strings.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
        text_color=ACCENT_BLUE)
    app._lbl_stat_notice.pack(anchor="w", padx=14, pady=(0, 8))

    app._charts_scroll_box = ctk.CTkScrollableFrame(
        parent, fg_color=BG_CARD, corner_radius=12,
        border_width=1, border_color=BORDER_CLR, scrollbar_button_color=BORDER_CLR)
    app._charts_scroll_box.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    bind_mouse_wheel(app._charts_scroll_box, app._charts_scroll_box)
