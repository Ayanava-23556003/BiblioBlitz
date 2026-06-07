#!/usr/bin/env python3
"""
splash.py - Application Splash Screen
"""

import customtkinter as ctk

from py.config import (
    APP_NAME, APP_VER, APP_TAGLINE,
    FONT_FAMILY, BG_ROOT, BG_CARD,
    ACCENT_BLUE, ACCENT_TEAL, TEXT_MID, TEXT_DIM,
)


def resource_path(filename):
    import os, sys
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, filename)


class SplashScreen(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.configure(fg_color=BG_ROOT)
        self.attributes("-topmost", True)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = 380, 420
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        try:
            from PIL import Image, ImageTk
            img = Image.open(resource_path("biblioblitz.png")).resize((180, 187), Image.LANCZOS)
            self._img = ImageTk.PhotoImage(img)
            ctk.CTkLabel(self, image=self._img, text="").pack(pady=(40, 10))
        except Exception:
            ctk.CTkLabel(self, text="⚡", font=ctk.CTkFont(size=60)).pack(pady=(40, 10))

        ctk.CTkLabel(self, text=APP_NAME,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=28, weight="bold"),
                     text_color=ACCENT_BLUE).pack()

        ctk.CTkLabel(self, text=APP_VER,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                     text_color=TEXT_MID).pack(pady=(4, 0))

        ctk.CTkLabel(self, text=APP_TAGLINE,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                     text_color=TEXT_DIM,
                     wraplength=320).pack(pady=(6, 0))

        ctk.CTkProgressBar(self, fg_color=BG_CARD, progress_color=ACCENT_TEAL,
                           width=260, height=6).pack(pady=(30, 0))
