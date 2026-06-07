#!/usr/bin/env python3
"""
main.py - BiblioBlitz v4.1 Entrypoint
"""

import customtkinter as ctk
from py.splash import SplashScreen
from py.app import BiblioBlitzApp


if __name__ == "__main__":
    splash_root = ctk.CTk()
    splash_root.withdraw()

    splash = SplashScreen()
    splash.update()

    def _launch():
        splash.destroy()
        splash_root.destroy()
        app = BiblioBlitzApp()
        app.mainloop()

    splash.after(2800, _launch)
    splash_root.mainloop()
