#!/usr/bin/env python3
"""
BiblioBlitz v3.0 — Academic Open-Access Paper Downloader
Searches CrossRef (Q1 journals only), checks Unpaywall, downloads free PDFs.
Pure Python backend — no R or Python scientific stack required by end users.
Cross-platform (Windows / macOS / Linux).
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import sys
import re
import time
import json
import csv
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# ── App-wide constants ─────────────────────────────────────────
APP_NAME = "BiblioBlitz"
APP_VER = "v3.0"
APP_TAGLINE = "Q1 Open-Access Academic Paper Downloader"

# ── Logo: embedded as a base64 PNG so it always works ─────────
LOGO_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAACXBIWXMAAAsTAAAL"
    "EwEAmpwYAAAF8WlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJl"
    "Z2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1w"
    "bWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1Q"
    "IENvcmUgNS42LWMxNDUgNzkuMTYzNDk5LCAyMDE4LzA4LzEzLTE2OjQwOjIyICAg"
    "ICAgICAiPiA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5"
    "OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPiA8L3JkZjpSREY+IDwveDp4bXBtZXRh"
    "PiA8P3hwYWNrZXQgZW5kPSJyIj8+"
)

# ── Q1 Journal Whitelist ───────────────────────────────────────
# Curated list of Q1 publishers/journals for hydrology, climate,
# earth sciences, environmental science, geosciences, ecology,
# and related fields. Container-title matching (case-insensitive).
Q1_JOURNALS = [
    # ── Nature family ────────────────────────────────────────────
    "nature", "nature climate change", "nature geoscience",
    "nature water", "nature sustainability", "nature communications",
    "nature reviews earth & environment", "nature ecology & evolution",
    "scientific reports",
    # ── Science / AAAS ───────────────────────────────────────────
    "science", "science advances",
    # ── Elsevier – hydrology / earth ─────────────────────────────
    "journal of hydrology", "journal of hydrology: regional studies",
    "advances in water resources", "water research",
    "water resources research",           # also AGU
    "journal of contaminant hydrology",
    "hydrological processes",
    "catena", "geoderma", "soil and tillage research",
    "science of the total environment",
    "environmental science & technology",
    "global and planetary change",
    "earth-science reviews",
    "geomorphology", "remote sensing of environment",
    "agricultural and forest meteorology",
    "agricultural water management",
    "journal of cleaner production",
    "ecological modelling", "ecological indicators",
    "global change biology",
    "environmental research letters",    # IOP – included as Q1
    # ── AGU (Wiley/AGU) ──────────────────────────────────────────
    "geophysical research letters",
    "journal of geophysical research",
    "journal of geophysical research: atmospheres",
    "journal of geophysical research: earth surface",
    "journal of geophysical research: biogeosciences",
    "water resources research",
    "earth and space science",
    "global biogeochemical cycles",
    "geochemistry geophysics geosystems",
    # ── EGU (Copernicus) ─────────────────────────────────────────
    "hydrology and earth system sciences",
    "hydrology and earth system sciences discussions",
    "natural hazards and earth system sciences",
    "the cryosphere",
    "atmospheric chemistry and physics",
    "biogeosciences",
    "earth system dynamics",
    "geoscientific model development",
    "solid earth",
    "climate of the past",
    # ── AMS ──────────────────────────────────────────────────────
    "journal of climate",
    "journal of hydrometeorology",
    "monthly weather review",
    "bulletin of the american meteorological society",
    "journal of the atmospheric sciences",
    "weather and forecasting",
    # ── Springer / other Q1 ──────────────────────────────────────
    "climatic change",
    "climate dynamics",
    "theoretical and applied climatology",
    "international journal of climatology",
    "stochastic environmental research and risk assessment",
    "environmental earth sciences",
    "hydrogeology journal",
    "groundwater",
    "journal of flood risk management",
    "natural hazards",
    "landslides",
    "earth surface processes and landforms",
    "ecohydrology",
    # ── MDPI – Q1 listed ─────────────────────────────────────────
    "remote sensing",
    "water",
    "sustainability",
    "atmosphere",
    "land",
    # ── Wiley misc Q1 ────────────────────────────────────────────
    "hydrological sciences journal",
    "river research and applications",
    "earth surface processes",
    "vadose zone journal",
    # ── General high-impact ──────────────────────────────────────
    "plos one",
    "global environmental change",
    "one earth",
    "iscience",
]

# Lower-cased set for O(1) lookup
Q1_SET = {j.lower() for j in Q1_JOURNALS}


def is_q1_journal(container_title: str) -> bool:
    """Return True if container_title matches the Q1 whitelist."""
    if not container_title:
        return False
    ct = container_title.strip().lower()
    # Exact match
    if ct in Q1_SET:
        return True
    # Partial / substring match for long variants
    for q in Q1_SET:
        if q in ct or ct in q:
            return True
    return False


# ══════════════════════════════════════════════════════════════
#  PURE-PYTHON BACKEND  (replaces R + PowerShell)
# ══════════════════════════════════════════════════════════════

def _http_get_json(url: str, params: dict = None, timeout: int = 20):
    """Fetch URL (with optional query params) and return parsed JSON or None."""
    if params:
        qs = urllib.parse.urlencode({k: str(v) for k, v in params.items()})
        url = url + "?" + qs
    req = urllib.request.Request(
        url, headers={"User-Agent": "BiblioBlitz/3.0 (academic-tool)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)
    except Exception:
        return None


def _download_file(url: str, dest_path: str, email: str) -> bool:
    """Download binary from url to dest_path. Returns True on success."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"BiblioBlitz/3.0 ({email})",
            "Accept": "application/pdf,*/*",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, \
                open(dest_path, "wb") as fh:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                fh.write(chunk)
        return True
    except Exception:
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False


def _safe_filename(title: str, doi: str) -> str:
    t = re.sub(r"[^\w\s-]", "_", title)
    t = re.sub(r"[\s]+", "_", t).strip("_")
    t = t[:70]
    d = doi.replace("/", "_").replace("\\", "_")
    return f"{t} [{d}].pdf"


def run_download(
    email: str,
    download_dir: str,
    keywords: str,
    max_results: int,
    year_from: int,
    log_cb,          # callable(msg, tag="info")
    stop_event,      # threading.Event
):
    """
    Main download worker.
    Steps: CrossRef search → Q1 filter → keyword filter →
           Unpaywall OA check → download PDFs → CSV log.
    """
    os.makedirs(download_dir, exist_ok=True)

    kw_parts = [k.strip() for k in re.split(r"[,;|]+", keywords) if k.strip()]
    kw_pattern = "|".join(re.escape(k.lower()) for k in kw_parts)
    query_str = " ".join(kw_parts)

    log_cb(f"[INFO] Keywords     : {query_str}", "info")
    log_cb(f"[INFO] Year from    : {year_from}  |  Max: {max_results}", "info")
    log_cb(f"[INFO] Save folder  : {download_dir}", "info")
    log_cb("─" * 55, "sep")

    # ── STEP 1 — CrossRef ─────────────────────────────────────
    log_cb("[STEP 1/4] Searching CrossRef API…", "step")
    all_items = []
    offset = 0
    batch_sz = 100

    while len(all_items) < max_results:
        if stop_event.is_set():
            log_cb("[INFO] Stopped by user.", "warn")
            return
        to_fetch = min(batch_sz, max_results - len(all_items))
        res = _http_get_json(
            "https://api.crossref.org/works",
            params={
                "query":  query_str,
                "filter": f"from-pub-date:{year_from},type:journal-article",
                "rows":   to_fetch,
                "offset": offset,
                "mailto": email,
                "select": "DOI,title,published,container-title",
            }
        )
        if not res or not res.get("message") or not res["message"].get("items"):
            break
        batch = res["message"]["items"]
        if not batch:
            break
        all_items.extend(batch)
        log_cb(f"[INFO] Fetched {len(all_items)} papers so far…", "info")
        offset += len(batch)
        time.sleep(0.4)

    log_cb(f"[INFO] CrossRef total fetched: {len(all_items)}", "info")

    if not all_items:
        log_cb("[ERROR] No results from CrossRef. Check keywords / internet.", "error")
        return

    # ── STEP 2 — Filter: Q1 journals + keyword in title ──────
    log_cb("[STEP 2/4] Filtering: Q1 journals & keyword in title…", "step")
    papers = []
    for item in all_items:
        title = (item.get("title") or [""])[0] if item.get("title") else ""
        doi = item.get("DOI", "")
        year = None
        try:
            year = item["published"]["date-parts"][0][0]
        except Exception:
            pass
        ct_list = item.get("container-title") or []
        ct = ct_list[0] if ct_list else ""

        if not title or not doi:
            continue
        if not is_q1_journal(ct):
            continue
        if kw_pattern and not re.search(kw_pattern, title.lower()):
            continue
        papers.append({"doi": doi, "title": title,
                      "year": year, "journal": ct})

    log_cb(f"[INFO] Q1 + keyword filtered papers: {len(papers)}", "info")

    if not papers:
        log_cb("[WARN] No papers passed the Q1 + keyword filter.", "warn")
        log_cb(
            "[HINT] Try broader keywords, or check if your topic has Q1 coverage.", "warn")
        return

    # ── STEP 3 — Unpaywall OA check ───────────────────────────
    log_cb("[STEP 3/4] Checking Unpaywall for open-access PDFs…", "step")
    for i, p in enumerate(papers, 1):
        if stop_event.is_set():
            log_cb("[INFO] Stopped by user.", "warn")
            return
        enc_doi = urllib.parse.quote(p["doi"], safe="")
        data = _http_get_json(
            f"https://api.unpaywall.org/v2/{enc_doi}",
            params={"email": email}
        )
        pdf_url = ""
        if data:
            loc = data.get("best_oa_location") or {}
            pdf_url = loc.get("url_for_pdf") or loc.get("url") or ""
        p["pdf_url"] = pdf_url
        if i % 10 == 0 or i == len(papers):
            log_cb(f"[INFO] Unpaywall checked: {i} / {len(papers)}", "info")
        time.sleep(0.25)

    papers_oa = [p for p in papers if p.get("pdf_url")]
    log_cb(f"[INFO] Papers with open-access PDF: {len(papers_oa)}", "info")

    if not papers_oa:
        log_cb("[WARN] No open-access PDFs found for the filtered papers.", "warn")
        return

    # ── STEP 4 — Download PDFs ────────────────────────────────
    log_cb("[STEP 4/4] Downloading PDFs…", "step")
    n_ok = n_skip = n_err = 0
    log_rows = []

    for i, p in enumerate(papers_oa, 1):
        if stop_event.is_set():
            log_cb("[INFO] Stopped by user.", "warn")
            break
        fname = _safe_filename(p["title"], p["doi"])
        fpath = os.path.join(download_dir, fname)
        short = p["title"][:60]

        if os.path.exists(fpath):
            status = "already_exists"
            n_skip += 1
            log_cb(f"[SKIP]  [{i}/{len(papers_oa)}] {short}", "warn")
        else:
            ok = _download_file(p["pdf_url"], fpath, email)
            if ok:
                status = "success"
                n_ok += 1
                log_cb(f"[OK]    [{i}/{len(papers_oa)}] {short}", "success")
            else:
                status = "error"
                n_err += 1
                log_cb(f"[FAIL]  [{i}/{len(papers_oa)}] {short}", "error")
        log_rows.append({
            "title":   p["title"],
            "doi":     p["doi"],
            "year":    p.get("year", ""),
            "journal": p.get("journal", ""),
            "status":  status,
            "file":    fname,
        })
        time.sleep(0.5)

    # ── Save CSV log ──────────────────────────────────────────
    log_path = os.path.join(download_dir, "download_log.csv")
    try:
        with open(log_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=log_rows[0].keys())
            writer.writeheader()
            writer.writerows(log_rows)
        log_cb(f"[LOG]   Report saved: {log_path}", "info")
    except Exception as e:
        log_cb(f"[WARN]  Could not save CSV log: {e}", "warn")

    log_cb("─" * 55, "sep")
    log_cb(
        f"[DONE]  Downloaded: {n_ok}  |  Skipped: {n_skip}  |  "
        f"Errors: {n_err}  |  Total OA: {len(papers_oa)}",
        "done"
    )


def run_pdf_integrity_check(folder: str, log_cb, stop_event):
    """
    Pure-Python PDF integrity check.
    Reads the first 4 bytes of every .pdf file.
    Moves corrupt files to Corrupted_PDFs/.
    """
    bad_folder = os.path.join(folder, "Corrupted_PDFs")
    os.makedirs(bad_folder, exist_ok=True)

    pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    log_cb(f"[INFO]  Found {len(pdfs)} PDF file(s) to check.", "info")

    ok_count = bad_count = 0
    results = []

    for fname in pdfs:
        if stop_event.is_set():
            break
        fpath = os.path.join(folder, fname)
        status = "OK"
        try:
            with open(fpath, "rb") as fh:
                header = fh.read(8)
            if len(header) < 4:
                status = "TooSmall"
            elif header[:4] != b"%PDF":
                status = "InvalidHeader"
        except Exception as e:
            status = f"CannotOpen:{e}"

        size_mb = round(os.path.getsize(fpath) / (1024 * 1024),
                        3) if os.path.exists(fpath) else 0

        if status == "OK":
            ok_count += 1
            log_cb(f"[OK]    {fname}", "success")
        else:
            dest = os.path.join(bad_folder, fname)
            c = 1
            while os.path.exists(dest):
                base, ext = os.path.splitext(fname)
                dest = os.path.join(bad_folder, f"{base}_dup{c}{ext}")
                c += 1
            try:
                os.replace(fpath, dest)
                log_cb(f"[MOVED] {fname}  →  {status}", "warn")
            except Exception as e:
                log_cb(f"[ERROR] Could not move {fname}: {e}", "error")
                status = f"MoveError:{status}"
            bad_count += 1

        results.append(
            {"FileName": fname, "Status": status, "SizeMB": size_mb})

    # Save report
    report_path = os.path.join(folder, "pdf_integrity_report.csv")
    try:
        with open(report_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["FileName", "Status", "SizeMB"])
            writer.writeheader()
            writer.writerows(results)
        log_cb(f"[REPORT] {report_path}", "info")
    except Exception as e:
        log_cb(f"[WARN]  Could not save report: {e}", "warn")

    log_cb(
        f"[DONE]  Total: {len(results)}  |  OK: {ok_count}  |  Problematic: {bad_count}",
        "done"
    )
    if bad_count > 0:
        log_cb(f"[INFO]  Corrupt files moved to: {bad_folder}", "info")


# ══════════════════════════════════════════════════════════════
#  PLACEHOLDER ENTRY  (auto-clears on focus / type)
# ══════════════════════════════════════════════════════════════

def _add_placeholder(entry: ctk.CTkEntry, placeholder: str,
                     ph_color="#4B5563", active_color="#CBD5E1"):
    """Attach placeholder behaviour to a CTkEntry."""
    entry._ph_text = placeholder
    entry._ph_color = ph_color
    entry._act_color = active_color

    def _show_ph():
        entry.configure(text_color=ph_color)
        if not entry.get():
            entry.insert(0, placeholder)

    def _hide_ph(event=None):
        if entry.get() == placeholder:
            entry.delete(0, "end")
        entry.configure(text_color=active_color)

    def _check_leave(event=None):
        if not entry.get():
            _show_ph()

    _show_ph()
    entry.bind("<FocusIn>",  _hide_ph)
    entry.bind("<FocusOut>", _check_leave)
    # Also clear on first keypress if placeholder still showing

    def _key(event=None):
        if entry.cget("text_color") == ph_color:
            _hide_ph()
    entry.bind("<Key>", _key)


def _get_entry_value(entry: ctk.CTkEntry) -> str:
    """Return entry value, treating placeholder text as empty."""
    val = entry.get().strip()
    ph = getattr(entry, "_ph_text", None)
    return "" if val == ph else val


# ══════════════════════════════════════════════════════════════
#  GUI APPLICATION
# ══════════════════════════════════════════════════════════════

class BiblioBlitzApp(ctk.CTk):

    # ── Init ─────────────────────────────────────────────────

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME}  ·  {APP_TAGLINE}")
        self.geometry("1060x780")
        self.minsize(860, 650)

        self._process = None
        self._running = False
        self._stop_event = threading.Event()
        self._log_lines = 0

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Closing ────────────────────────────────────────────────────
    def _on_close(self):
        if self._running:
            answer = messagebox.askyesno(
                "Download in Progress",
                "A download is currently running.\nStop it and exit BiblioBlitz?"
            )
            if not answer:
                return
            self._stop_event.set()
        else:
            answer = messagebox.askyesno(
                "Exit BiblioBlitz",
                "Are you sure you want to close BiblioBlitz?"
            )
            if not answer:
                return
        self.destroy()
    # ── UI ────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=("#0B1628", "#0B1628"),
                           corner_radius=0, height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Logo — try to render embedded PNG; fall back to glyph
        logo_loaded = False
        if _PIL_OK:
            try:
                base = getattr(sys, '_MEIPASS', os.path.dirname(
                    os.path.abspath(__file__)))
                logo_path = os.path.join(
                    base, 'Gemini_Generated_Image_nsppmcnsppmcnspp.png')
                if not os.path.isfile(logo_path):
                    logo_path = r"C:\Users\ayanp\Downloads\Gemini_Generated_Image_nsppmcnsppmcnspp.png"
                if os.path.isfile(logo_path):
                    img = Image.open(logo_path)
                    img.thumbnail((44, 44), Image.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img,
                                           size=(img.width, img.height))
                    ctk.CTkLabel(hdr, image=ctk_img, text="").pack(
                        side="left", padx=(14, 8), pady=0)
                    logo_loaded = True
            except Exception:
                pass

        if not logo_loaded:
            ctk.CTkLabel(
                hdr, text="✦",
                font=ctk.CTkFont(size=26),
                text_color="#3B82F6"
            ).pack(side="left", padx=(18, 6), pady=0)

        ctk.CTkLabel(
            hdr, text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI Semibold",
                             size=20, weight="bold"),
            text_color="#3B82F6"
        ).pack(side="left", padx=(0, 10), pady=0)

        ctk.CTkLabel(
            hdr, text=APP_TAGLINE,
            font=ctk.CTkFont(size=12),
            text_color="#64748B"
        ).pack(side="left", padx=(0, 20))

        # Version badge (right side)
        ctk.CTkLabel(
            hdr, text=APP_VER,
            font=ctk.CTkFont(size=11),
            text_color="#374151"
        ).pack(side="right", padx=(0, 6))

        ctk.CTkLabel(
            hdr, text="⬤  Pure Python  •  No R/Python setup needed",
            font=ctk.CTkFont(size=11),
            text_color="#34D399"
        ).pack(side="right", padx=(20, 8))

        # ── Body ─────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 0))

        left_panel = ctk.CTkFrame(
            body, width=345, fg_color=("#111827", "#111827"), corner_radius=10
        )
        left_panel.pack(side="left", fill="y", padx=(0, 8))
        left_panel.pack_propagate(False)
        self._build_config_panel(left_panel)

        right_panel = ctk.CTkFrame(
            body, fg_color=("#0D1117", "#0D1117"), corner_radius=10
        )
        right_panel.pack(side="left", fill="both", expand=True)
        self._build_log_panel(right_panel)

        self._build_footer()

    def _build_config_panel(self, parent):
        ctk.CTkLabel(
            parent, text="CONFIGURATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#374151"
        ).pack(anchor="w", padx=16, pady=(14, 0))

        ctk.CTkLabel(
            parent, text="Search & Download Settings",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F1F5F9"
        ).pack(anchor="w", padx=16, pady=(2, 8))

        # Q1 notice
        ctk.CTkLabel(
            parent,
            text="🏆  Q1 journals only (Nature, Science, EGU, AGU, Elsevier…)",
            font=ctk.CTkFont(size=9),
            text_color="#A78BFA",
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 6))

        ctk.CTkFrame(parent, height=1, fg_color="#1E293B").pack(
            fill="x", padx=16, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent", scrollbar_button_color="#1E293B"
        )
        scroll.pack(fill="both", expand=True, padx=4, pady=0)

        # ── Email ────────────────────────────────────────────
        self._field_label(scroll, "📧  Email Address",
                          hint="Used for Unpaywall & CrossRef API (not stored)")
        self._e_email = ctk.CTkEntry(
            scroll, height=35, font=ctk.CTkFont(size=11),
            fg_color="#0D1117", border_color="#1E3A5F", border_width=1
        )
        self._e_email.pack(fill="x", padx=12, pady=(0, 14))
        _add_placeholder(self._e_email, "e.g. yourname@university.edu")

        # ── Download Dir ─────────────────────────────────────
        self._field_label(scroll, "📁  Download Directory")
        df = ctk.CTkFrame(scroll, fg_color="transparent")
        df.pack(fill="x", padx=12, pady=(0, 14))
        self.v_dir = ctk.StringVar(value=str(Path.home() / "Papers"))
        ctk.CTkEntry(
            df, textvariable=self.v_dir, height=35,
            font=ctk.CTkFont(size=11),
            fg_color="#0D1117", border_color="#1E3A5F", border_width=1
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            df, text="⋯", width=38, height=35,
            fg_color="#1E293B", hover_color="#334155",
            font=ctk.CTkFont(size=14),
            command=self._browse_dir
        ).pack(side="right")

        # ── Keywords ─────────────────────────────────────────
        self._field_label(scroll, "🔍  Keywords",
                          hint="Comma-separated • used for search & title filter")
        self._e_keywords = ctk.CTkEntry(
            scroll, height=35, font=ctk.CTkFont(size=11),
            fg_color="#0D1117", border_color="#1E3A5F", border_width=1
        )
        self._e_keywords.pack(fill="x", padx=12, pady=(0, 14))
        _add_placeholder(self._e_keywords,
                         "e.g. soil erosion, sediment yield, runoff")

        # ── Max Papers ───────────────────────────────────────
        self._field_label(scroll, "📦  Max Papers to Fetch")
        self.v_max = ctk.IntVar(value=1000)
        mf = ctk.CTkFrame(scroll, fg_color="transparent")
        mf.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkEntry(
            mf, textvariable=self.v_max, width=90, height=35,
            font=ctk.CTkFont(size=11),
            fg_color="#0D1117", border_color="#1E3A5F", border_width=1
        ).pack(side="left", padx=(0, 8))
        sl_max = ctk.CTkSlider(
            mf, from_=100, to=100000, number_of_steps=999,
            variable=self.v_max,
            button_color="#3B82F6", button_hover_color="#2563EB",
            progress_color="#1E3A5F"
        )
        sl_max.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(scroll, text="100  —  1,00,000 papers",
                     font=ctk.CTkFont(size=9), text_color="#4B5563"
                     ).pack(anchor="e", padx=12, pady=(0, 10))

        # ── Starting Year ────────────────────────────────────
        self._field_label(scroll, "📅  Starting Year")
        self.v_year = ctk.IntVar(value=2015)
        yf = ctk.CTkFrame(scroll, fg_color="transparent")
        yf.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkEntry(
            yf, textvariable=self.v_year, width=90, height=35,
            font=ctk.CTkFont(size=11),
            fg_color="#0D1117", border_color="#1E3A5F", border_width=1
        ).pack(side="left", padx=(0, 8))
        sl_year = ctk.CTkSlider(
            yf, from_=1990, to=2025, number_of_steps=35,
            variable=self.v_year,
            button_color="#3B82F6", button_hover_color="#2563EB",
            progress_color="#1E3A5F"
        )
        sl_year.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(scroll, text="1990  —  2025",
                     font=ctk.CTkFont(size=9), text_color="#4B5563"
                     ).pack(anchor="e", padx=12, pady=(0, 10))

        # ── PDF Integrity Check ──────────────────────────────
        ctk.CTkFrame(scroll, height=1, fg_color="#1E293B").pack(
            fill="x", padx=12, pady=(6, 12)
        )
        ctk.CTkLabel(
            scroll, text="🔬  PDF Integrity Check",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#93C5FD"
        ).pack(anchor="w", padx=12)
        ctk.CTkLabel(
            scroll,
            text="Scans the download folder for corrupted\nor invalid PDFs and quarantines them.",
            font=ctk.CTkFont(size=10),
            text_color="#6B7280", justify="left"
        ).pack(anchor="w", padx=12, pady=(3, 10))
        ctk.CTkButton(
            scroll,
            text="🔬   Run PDF Integrity Check",
            height=36,
            fg_color="#0F2040", hover_color="#1E3A5F",
            border_width=1, border_color="#1E3A5F",
            font=ctk.CTkFont(size=12),
            command=self._run_pdf_check
        ).pack(fill="x", padx=12, pady=(0, 14))

    def _field_label(self, parent, text, hint=None):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#CBD5E1"
        ).pack(anchor="w", padx=12, pady=(6, 1))
        if hint:
            ctk.CTkLabel(
                parent, text=hint,
                font=ctk.CTkFont(size=9),
                text_color="#4B5563"
            ).pack(anchor="w", padx=12, pady=(0, 3))

    def _build_log_panel(self, parent):
        lhdr = ctk.CTkFrame(parent, fg_color="transparent")
        lhdr.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(
            lhdr, text="Activity Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F1F5F9"
        ).pack(side="left")

        ctk.CTkButton(
            lhdr, text="Clear", width=60, height=26,
            fg_color="#1E293B", hover_color="#334155",
            font=ctk.CTkFont(size=10),
            command=self._clear_log
        ).pack(side="right")

        stats = ctk.CTkFrame(parent, fg_color="#0B1628",
                             corner_radius=8, height=58)
        stats.pack(fill="x", padx=14, pady=(0, 8))
        stats.pack_propagate(False)

        self._s_fetched = self._make_stat(stats, "Fetched",     "#3B82F6")
        self._s_q1 = self._make_stat(stats, "Q1 Filtered", "#A78BFA")
        self._s_oa = self._make_stat(stats, "Open Access", "#8B5CF6")
        self._s_done = self._make_stat(stats, "Downloaded",  "#10B981")
        self._s_errors = self._make_stat(stats, "Errors",      "#EF4444")
        self._s_skipped = self._make_stat(stats, "Skipped",     "#F59E0B")

        self._log = ctk.CTkTextbox(
            parent,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#060D18",
            text_color="#CBD5E1",
            corner_radius=8,
            wrap="none",
            scrollbar_button_color="#1E293B"
        )
        self._log.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._log.configure(state="disabled")

        self._log.tag_config("step",    foreground="#A78BFA")
        self._log.tag_config("info",    foreground="#60A5FA")
        self._log.tag_config("success", foreground="#34D399")
        self._log.tag_config("warn",    foreground="#FCD34D")
        self._log.tag_config("error",   foreground="#F87171")
        self._log.tag_config("install", foreground="#FB923C")
        self._log.tag_config("sep",     foreground="#1E293B")
        self._log.tag_config("done",    foreground="#6EE7B7")

    def _make_stat(self, parent, label, color):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", expand=True)
        val = ctk.CTkLabel(f, text="—",
                           font=ctk.CTkFont(size=17, weight="bold"),
                           text_color=color)
        val.pack(pady=(6, 0))
        ctk.CTkLabel(f, text=label,
                     font=ctk.CTkFont(size=9),
                     text_color="#374151").pack()
        return val

    def _build_footer(self):
        foot = ctk.CTkFrame(self, fg_color="#060D18",
                            corner_radius=0, height=70)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        self._pbar = ctk.CTkProgressBar(
            foot, height=3, mode="indeterminate",
            progress_color="#3B82F6", fg_color="#0B1628"
        )
        self._pbar.pack(fill="x")
        self._pbar.set(0)

        btn_row = ctk.CTkFrame(foot, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(6, 0))

        self._btn_start = ctk.CTkButton(
            btn_row,
            text="▶   Start Download",
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563EB", hover_color="#1D4ED8",
            command=self._start_download
        )
        self._btn_start.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._btn_stop = ctk.CTkButton(
            btn_row,
            text="⏹  Stop",
            height=38, width=90,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#450A0A", hover_color="#7F1D1D",
            state="disabled",
            command=self._stop
        )
        self._btn_stop.pack(side="right")

        self._lbl_status = ctk.CTkLabel(
            foot, text="Ready  •  No R or Python required",
            font=ctk.CTkFont(size=10),
            text_color="#374151"
        )
        self._lbl_status.pack(pady=(2, 0))

    # ── Helpers ──────────────────────────────────────────────

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select Download Folder")
        if d:
            self.v_dir.set(d)

    def _set_running(self, state: bool):
        self._running = state
        s_start = "disabled" if state else "normal"
        s_stop = "normal" if state else "disabled"
        self.after(0, lambda: self._btn_start.configure(state=s_start))
        self.after(0, lambda: self._btn_stop.configure(state=s_stop))
        if state:
            self.after(0, self._pbar.start)
        else:
            self.after(0, self._pbar.stop)
            self.after(0, lambda: self._pbar.set(0))

    def _status(self, txt):
        self.after(0, lambda: self._lbl_status.configure(text=txt))

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")
        self._log_lines = 0

    def _append_log(self, text, tag="info"):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", text + "\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
            self._log_lines += 1
            self._update_stats(text)
        self.after(0, _do)

    def _update_stats(self, line):
        m = re.search(r"Fetched (\d+) papers", line)
        if m:
            self.after(0, lambda v=m.group(
                1): self._s_fetched.configure(text=v))
        m = re.search(r"Q1 \+ keyword filtered papers: (\d+)", line)
        if m:
            self.after(0, lambda v=m.group(1): self._s_q1.configure(text=v))
        m = re.search(r"open-access PDF[s]?: (\d+)", line)
        if m:
            self.after(0, lambda v=m.group(1): self._s_oa.configure(text=v))
        m = re.search(r"Downloaded: (\d+)", line)
        if m:
            self.after(0, lambda v=m.group(1): self._s_done.configure(text=v))
        m = re.search(r"Errors: (\d+)", line)
        if m:
            self.after(0, lambda v=m.group(
                1): self._s_errors.configure(text=v))
        m = re.search(r"Skipped: (\d+)", line)
        if m:
            self.after(0, lambda v=m.group(
                1): self._s_skipped.configure(text=v))

    # ── Validation ───────────────────────────────────────────

    def _validate_inputs(self):
        email = _get_entry_value(self._e_email)
        keywords = _get_entry_value(self._e_keywords)
        dl_dir = self.v_dir.get().strip()

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            messagebox.showerror(
                "Input Error",
                "Please enter a valid email address.\nExample: you@university.edu"
            )
            return False
        if not keywords:
            messagebox.showerror(
                "Input Error", "Please enter at least one keyword.")
            return False
        if not dl_dir:
            messagebox.showerror(
                "Input Error", "Please set a Download Directory.")
            return False
        try:
            max_r = int(self.v_max.get())
            year = int(self.v_year.get())
            if max_r < 1 or max_r > 100000:
                raise ValueError
            if year < 1990 or year > 2025:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror(
                "Input Error",
                "Max papers must be 1 – 1,00,000\nStarting year must be 1990 – 2025"
            )
            return False
        return True

    # ── Start Download ────────────────────────────────────────

    def _start_download(self):
        if not self._validate_inputs():
            return

        for lbl in [self._s_fetched, self._s_q1, self._s_oa,
                    self._s_done, self._s_errors, self._s_skipped]:
            lbl.configure(text="—")

        self._clear_log()
        self._stop_event.clear()
        self._set_running(True)
        self._status("Running…")

        params = dict(
            email=_get_entry_value(self._e_email),
            download_dir=self.v_dir.get().strip().replace("\\", "/"),
            keywords=_get_entry_value(self._e_keywords),
            max_results=int(self.v_max.get()),
            year_from=int(self.v_year.get()),
        )
        self._append_log("─" * 55, "sep")
        self._append_log(f"[INFO] Email        : {params['email']}", "info")
        self._append_log(f"[INFO] Keywords     : {params['keywords']}", "info")
        self._append_log(
            f"[INFO] Save folder  : {params['download_dir']}", "info")
        self._append_log(
            f"[INFO] Year from    : {params['year_from']}  |  "
            f"Max: {params['max_results']:,}", "info"
        )
        self._append_log("─" * 55, "sep")

        threading.Thread(
            target=self._worker,
            kwargs={**params, "log_cb": self._append_log,
                    "stop_event": self._stop_event},
            daemon=True
        ).start()

    def _worker(self, **kwargs):
        try:
            run_download(**kwargs)
            self._status("Completed ✓")
        except Exception as exc:
            self._append_log(f"[ERROR] Unexpected error: {exc}", "error")
            self._status("Error occurred")
        finally:
            self._set_running(False)

    # ── Stop ─────────────────────────────────────────────────

    def _stop(self):
        self._stop_event.set()
        self._append_log(
            "[INFO] Stop requested — finishing current file…", "warn")
        self._status("Stopping…")
        self._set_running(False)

    # ── PDF Integrity Check ───────────────────────────────────

    def _run_pdf_check(self):
        folder = self.v_dir.get().strip()
        if not folder:
            messagebox.showerror(
                "Error", "Please set the Download Directory first.")
            return
        if not os.path.isdir(folder):
            if messagebox.askyesno(
                "Folder Not Found",
                f"Folder does not exist:\n{folder}\n\nCreate it?"
            ):
                os.makedirs(folder, exist_ok=True)
            else:
                return

        self._append_log("─" * 55, "sep")
        self._append_log("[STEP] Starting PDF integrity check…", "step")
        self._stop_event.clear()
        self._set_running(True)
        self._status("Running PDF checker…")

        threading.Thread(
            target=self._worker_pdf,
            args=(folder,),
            daemon=True
        ).start()

    def _worker_pdf(self, folder):
        try:
            run_pdf_integrity_check(folder, self._append_log, self._stop_event)
            self._status("PDF check complete ✓")
        except Exception as exc:
            self._append_log(f"[ERROR] PDF check error: {exc}", "error")
            self._status("PDF check error")
        finally:
            self._set_running(False)


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = BiblioBlitzApp()
    app.mainloop()
