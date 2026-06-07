#!/usr/bin/env python3
"""
tabs/tab_slr.py - Systematic Literature Review (SLR) Tab Builder
"""

import customtkinter as ctk

from py.config import (
    FONT_FAMILY, BG_PANEL, BG_CARD, BORDER_CLR, TEXT_MID,
)


def build_slr_tab(app, parent):
    """
    Builds the Systematic Literature Review tab (under development).
    """
    box = ctk.CTkFrame(parent, fg_color=BG_PANEL, corner_radius=12,
                       border_width=1, border_color=BORDER_CLR)
    box.pack(fill="both", expand=True, padx=40, pady=40)

    inner = ctk.CTkFrame(box, width=550, height=220, fg_color=BG_CARD,
                         corner_radius=8, border_width=1, border_color=BORDER_CLR)
    inner.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        inner, text="🚧 PIPELINE COMPONENT NOTICE 🚧",
        font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
        text_color="#E63946").pack(pady=(40, 10))

    ctk.CTkLabel(
        inner, text="DEVELOPMENT UNDER PROGRESS",
        font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
        text_color=BORDER_CLR).pack(pady=5)

    ctk.CTkLabel(
        inner,
        text="The Systematic Literature Review Parsing Engine is under modification.",
        font=ctk.CTkFont(family=FONT_FAMILY, size=12),
        text_color=TEXT_MID).pack(pady=5)
