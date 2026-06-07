#!/usr/bin/env python3
"""
utils.py - Helper Functions and Formatting Utilities for v4.1
"""

import sys
import re
import json
import urllib.request
import urllib.parse
from py.config import APP_NAME, APP_VER, TEXT_BRIGHT, TEXT_DIM


def bind_mouse_wheel(widget, scroll_frame):
    canvas = getattr(scroll_frame, "_canvas", None)
    if not canvas:
        return

    def _on_mousewheel(event):
        if sys.platform == 'darwin':
            canvas.yview_scroll(int(-1 * event.delta), "units")
        elif sys.platform == 'win32':
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

    widget.bind("<MouseWheel>", _on_mousewheel)
    widget.bind("<Button-4>", _on_mousewheel)
    widget.bind("<Button-5>", _on_mousewheel)


def _http_get_json(url, params=None, timeout=20):
    if params:
        url = url + "?" + \
            urllib.parse.urlencode({k: str(v) for k, v in params.items()})
    req = urllib.request.Request(
        url, headers={"User-Agent": f"{APP_NAME}/{APP_VER} (academic-tool)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _download_file(url, dest_path, email):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"{APP_NAME}/{APP_VER} ({email})",
        "Accept": "application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r, open(dest_path, "wb") as fh:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
        return True
    except Exception:
        import os
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False


def _safe_filename(title, doi, year=None, authors=None, journal=None):
    def _clean(s, maxlen=50):
        s = re.sub(r"[^\w\s\-]", "_", str(s) if s else "")
        s = re.sub(r"\s+", "_", s).strip("_")
        return s[:maxlen]

    if authors and isinstance(authors, list) and len(authors) > 0:
        first = authors[0]
        last = first.get("family") or first.get(
            "name") or "" if isinstance(first, dict) else str(first)
        last = _clean(last, 30)
        author_part = f"[{last}_et_al]" if len(authors) > 1 else f"[{last}]"
    else:
        author_part = "[Unknown]"

    year_part = str(year) if year else "0000"
    title_part = _clean(title, 60)
    journal_part = _clean(journal or "", 40) if journal else "Journal"
    doi_part = doi.replace("/", "_").replace("\\", "_") if doi else "no-doi"

    fname = f"{author_part}_{year_part}_{title_part}_{journal_part}_{doi_part}.pdf"
    return re.sub(r'[<>:"/\\|?*]', "_", fname)


def _add_placeholder(entry, placeholder):
    entry._ph_text = placeholder

    def _show():
        if not entry.get():
            entry.insert(0, placeholder)
            entry.configure(text_color=TEXT_DIM)

    def _hide(e=None):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.configure(text_color=TEXT_BRIGHT)
    _show()
    entry.bind("<FocusIn>", _hide)
    entry.bind("<FocusOut>", lambda e: _show())


def _get_val(entry):
    v = entry.get().strip()
    return "" if v == getattr(entry, "_ph_text", None) else v
