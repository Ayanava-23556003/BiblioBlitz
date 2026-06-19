#!/usr/bin/env python3
"""
engine/trends.py  –  CSV-based Scholarly Trend Compilation and Chart Rendering
                     (BiblioBlitz v4.2)

Reads a BiblioBlitz metadata CSV exported from the Acquisition tab.
Deduplicates by DOI (empty DOI rows are all kept).
Builds three charts:
  1. Publications vs Year
  2. Publications by Country (top 20)
  3. Publication Type distribution (pie)
"""

import csv
from collections import Counter
from pathlib import Path

import customtkinter as ctk

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    _MATPLOTLIB_OK = True
except ImportError:
    _MATPLOTLIB_OK = False

from py.config import BG_CARD, BG_ENTRY, TEXT_BRIGHT, BORDER_CLR, COUNTRIES as _KNOWN_COUNTRIES

# Valid country names — used to reject junk strings
_VALID_COUNTRY_SET = set(_KNOWN_COUNTRIES) - {"Global (All Countries)"}

# ── Colour palette ────────────────────────────────────────────────────────────
_C1 = (0.113, 0.207, 0.341)   # dark navy
_C2 = (0.164, 0.615, 0.560)   # teal
_C3 = (0.270, 0.482, 0.615)   # steel blue
_C4 = (0.850, 0.550, 0.200)   # amber
_C5 = (0.600, 0.200, 0.300)   # wine

# ── Expected CSV column names produced by BiblioBlitz downloader ──────────────
# These are tried in order; the first match wins.
_COL_YEAR    = ["Year"]
_COL_COUNTRY = ["Country"]
_COL_TYPE    = ["Publication Type"]
_COL_DOI     = ["DOI"]


def _find_col(header, candidates):
    """Return the first candidate column name found in header (case-insensitive)."""
    h_lower = {c.lower(): c for c in header}
    for c in candidates:
        if c.lower() in h_lower:
            return h_lower[c.lower()]
    return None


def _parse_csv(path, status_cb):
    """
    Read the BiblioBlitz metadata CSV.
    Returns list of dicts with keys: year, country, pub_type, doi.
    Deduplicates by DOI (case-insensitive, stripped).
    Papers with an empty DOI are always kept (can't deduplicate without one).
    """
    records = []
    seen_dois = set()
    raw_count = 0
    dup_count = 0

    path = str(path)
    status_cb(f"Reading CSV: {Path(path).name}", "step")

    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []

        col_year    = _find_col(header, _COL_YEAR)
        col_country = _find_col(header, _COL_COUNTRY)
        col_type    = _find_col(header, _COL_TYPE)
        col_doi     = _find_col(header, _COL_DOI)

        status_cb(
            f"Columns detected — Year: {col_year}, Country: {col_country}, "
            f"Type: {col_type}, DOI: {col_doi}",
            "info"
        )

        for row in reader:
            raw_count += 1

            # ── DOI deduplication ─────────────────────────────────────────
            doi = ""
            if col_doi:
                doi = (row.get(col_doi) or "").strip().lower()
                # Strip full URL prefix if present
                if doi.startswith("https://doi.org/"):
                    doi = doi[len("https://doi.org/"):]

            if doi:
                if doi in seen_dois:
                    dup_count += 1
                    continue
                seen_dois.add(doi)

            # ── Year ──────────────────────────────────────────────────────
            yr = None
            if col_year:
                try:
                    yr_raw = (row.get(col_year) or "").strip()
                    yr = int(float(yr_raw)) if yr_raw else None
                except (ValueError, TypeError):
                    yr = None

            # ── Country ───────────────────────────────────────────────────
            country = ""
            if col_country:
                raw_c = (row.get(col_country) or "").strip()
                # Accept only validated country names
                if raw_c in _VALID_COUNTRY_SET:
                    country = raw_c

            # ── Publication type ──────────────────────────────────────────
            pub_type = "Other"
            if col_type:
                raw_t = (row.get(col_type) or "").strip()
                if raw_t:
                    pub_type = raw_t

            records.append({
                "year":     yr,
                "country":  country,
                "pub_type": pub_type,
                "doi":      doi,
            })

    status_cb(
        f"CSV parsed — {raw_count} raw rows → {len(records)} unique records "
        f"({dup_count} duplicates removed by DOI).",
        "info"
    )
    return records


def compile_csv_trends(csv_path, parent_frame, status_cb, render_cb=None):
    """
    Entry point called by app._trigger_csv_trends().

    Parses *csv_path*, deduplicates, and renders three charts.
    Calls status_cb(message, tag) for status updates.
    Calls render_cb(fig) to display the matplotlib Figure,
    or embeds it directly into parent_frame if render_cb is None.
    """
    if not _MATPLOTLIB_OK:
        ctk.CTkLabel(parent_frame, text="Matplotlib not installed.",
                     text_color="#E63946").pack(pady=20)
        return

    records = _parse_csv(csv_path, status_cb)

    if not records:
        status_cb("[ALERT] No records found in the CSV.", "error")
        return

    # Separate data series
    all_years    = [r["year"]    for r in records if r["year"] is not None]
    all_countries = [r["country"] for r in records if r["country"]]
    all_types    = [r["pub_type"] for r in records]

    # Count distinct values for summary
    unique_countries = len(set(all_countries))
    unique_pub_types = len(set(all_types))
    total = len(records)

    status_cb(
        f"Rendering — {total} publications | "
        f"{len(all_countries)} with country data ({unique_countries} unique countries) | "
        f"{unique_pub_types} publication type(s).",
        "success"
    )

    # ── Configure matplotlib style ────────────────────────────────────────────
    plt.rcParams.update({
        "font.size":        11,
        "axes.labelsize":   12,
        "axes.titlesize":   13,
        "xtick.labelsize":  10,
        "ytick.labelsize":  10,
        "axes.titlecolor":  TEXT_BRIGHT,
        "axes.labelcolor":  TEXT_BRIGHT,
        "xtick.color":      TEXT_BRIGHT,
        "ytick.color":      TEXT_BRIGHT,
    })

    has_country = bool(all_countries)
    nrows = 3 if has_country else 2
    fig = plt.figure(figsize=(12, 4.8 * nrows), facecolor=BG_CARD)

    # ── Chart 1: Publications vs Year ─────────────────────────────────────────
    ax1 = plt.subplot2grid((nrows, 1), (0, 0))
    if all_years:
        yc = Counter(all_years)
        s_yrs  = sorted(yc.keys())
        s_cnts = [yc[y] for y in s_yrs]

        ax1.plot(s_yrs, s_cnts, marker="o", color=_C1, linewidth=2.5, markersize=5)
        ax1.fill_between(s_yrs, s_cnts, alpha=0.12, color=_C1)

        # Annotate peak year
        peak_yr  = s_yrs[s_cnts.index(max(s_cnts))]
        peak_val = max(s_cnts)
        ax1.annotate(
            f"Peak: {peak_yr} ({peak_val})",
            xy=(peak_yr, peak_val),
            xytext=(peak_yr, peak_val + max(s_cnts) * 0.07),
            fontsize=9, color=_C1,
            arrowprops=dict(arrowstyle="->", color=_C1, lw=1.2)
        )
    else:
        ax1.text(0.5, 0.5, "No year data available",
                 ha="center", va="center", color=TEXT_BRIGHT, fontsize=12,
                 transform=ax1.transAxes)

    ax1.set_title(f"Publications vs Year  (n={total}, deduplicated by DOI)",
                  fontsize=13, weight="bold", color=TEXT_BRIGHT)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Number of Publications")
    ax1.set_facecolor(BG_ENTRY)
    ax1.grid(True, linestyle="--", alpha=0.45)
    for sp in ax1.spines.values():
        sp.set_edgecolor(BORDER_CLR)

    # ── Chart 2: Publications by Country ──────────────────────────────────────
    if has_country:
        ax2 = plt.subplot2grid((nrows, 1), (1, 0))
        cc = Counter(all_countries)
        top_n  = min(20, len(cc))
        top_c  = cc.most_common(top_n)
        c_names = [x[0] for x in top_c][::-1]
        c_vals  = [x[1] for x in top_c][::-1]
        bar_clrs = [_C2 if i % 2 == 0 else _C3 for i in range(len(c_names))]

        bars = ax2.barh(c_names, c_vals, color=bar_clrs, height=0.65)
        for bar, val in zip(bars, c_vals):
            ax2.text(
                bar.get_width() + max(c_vals) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, color=TEXT_BRIGHT)

        ax2.set_title(
            f"Publications by Country  "
            f"(top {top_n} of {unique_countries} countries, "
            f"{len(all_countries)} records with country data)",
            fontsize=13, weight="bold", color=TEXT_BRIGHT)
        ax2.set_xlabel("Number of Publications")
        ax2.set_facecolor(BG_ENTRY)
        ax2.grid(True, linestyle="--", alpha=0.4, axis="x")
        for sp in ax2.spines.values():
            sp.set_edgecolor(BORDER_CLR)

    # ── Chart 3: Publication Type Pie ─────────────────────────────────────────
    pie_row = 2 if has_country else 1
    ax3 = plt.subplot2grid((nrows, 1), (pie_row, 0))
    tc = Counter(all_types)
    if tc:
        labels   = list(tc.keys())
        sizes    = list(tc.values())
        pie_clrs = [_C1, _C2, _C3, _C4, _C5][: len(labels)]
        wedges, texts, autotexts = ax3.pie(
            sizes, labels=labels, colors=pie_clrs,
            autopct="%1.1f%%", startangle=140,
            textprops={"fontsize": 10, "color": TEXT_BRIGHT},
            wedgeprops={"linewidth": 0.8, "edgecolor": BG_CARD},
            pctdistance=0.82)
        for at in autotexts:
            at.set_fontsize(9)
            at.set_color(TEXT_BRIGHT)
        ax3.set_title(
            f"Publication Type Distribution  (n={sum(sizes)})",
            fontsize=13, weight="bold", color=TEXT_BRIGHT)
    else:
        ax3.text(0.5, 0.5, "No publication type data available",
                 ha="center", va="center", color=TEXT_BRIGHT, fontsize=12)
        ax3.set_facecolor(BG_ENTRY)

    fig.tight_layout(pad=2.5)

    if render_cb:
        render_cb(fig)
    else:
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    status_cb(
        f"Done — {total} records | {unique_countries} countries | "
        f"{unique_pub_types} publication type(s).",
        "done"
    )
