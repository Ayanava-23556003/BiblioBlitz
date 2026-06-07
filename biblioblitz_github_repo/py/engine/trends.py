#!/usr/bin/env python3
"""
engine/trends.py - Live Scholarly Trend Compilation and Chart Rendering
"""

import re
from collections import Counter

import customtkinter as ctk

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    _MATPLOTLIB_OK = True
except ImportError:
    _MATPLOTLIB_OK = False

from py.config import BG_CARD, BG_ENTRY, TEXT_BRIGHT
from py.utils import _http_get_json


def compile_live_api_trends(keywords, year_from, parent_frame, status_cb, render_cb=None):
    if not _MATPLOTLIB_OK:
        ctk.CTkLabel(parent_frame, text="Matplotlib missing.",
                     text_color="#E63946").pack(pady=20)
        return

    status_cb("Connecting to global repositories... Querying metadata metrics indexes...", "step")
    query_str = " ".join([k.strip() for k in re.split(r"[,;|]+", keywords) if k.strip()])

    years_pool = []
    journals_pool = []
    types_pool = []

    # ── CrossRef ────────────────────────────────────────────────────────────
    res_cr = _http_get_json("https://api.crossref.org/works", params={
        "query": query_str,
        "filter": f"from-pub-date:{year_from},type:journal-article",
        "rows": 150
    })
    if res_cr and res_cr.get("message") and res_cr["message"].get("items"):
        for item in res_cr["message"]["items"]:
            try:
                y = int(item["published"]["date-parts"][0][0])
            except Exception:
                y = int(year_from)
            years_pool.append(y)
            journals_pool.append(
                (item.get("container-title") or ["Global/Other Open Journals"])[0])
            types_pool.append("Journal Article")

    # ── OpenAlex ────────────────────────────────────────────────────────────
    res_oa = _http_get_json("https://api.openalex.org/works", params={
        "search": query_str,
        "filter": f"from_publication_date:{year_from}-01-01,type:article",
        "per_page": 150
    })
    if res_oa and res_oa.get("results"):
        for r in res_oa["results"]:
            years_pool.append(r.get("publication_year") or int(year_from))
            loc = r.get("primary_location") or {}
            src = loc.get("source") or {}
            journals_pool.append(src.get("display_name") or "Global/Other Open Journals")

            raw_type = r.get("type", "").lower()
            if "article" in raw_type or "journal" in raw_type:
                types_pool.append("Journal Article")
            elif "book" in raw_type:
                types_pool.append("Book/Report Chapters")
            else:
                types_pool.append("Institutional Reports/Theses")

    if not years_pool:
        status_cb("[ALERT] Zero remote records found matching current keyword sequences.", "error")
        return

    status_cb("Data compiled successfully. Rendering custom contrast RGB chart matrices...", "success")

    plt.rcParams.update({
        'font.size': 11, 'axes.labelsize': 12,
        'axes.titlesize': 13, 'xtick.labelsize': 10, 'ytick.labelsize': 10
    })
    fig = plt.figure(figsize=(11, 9), facecolor=BG_CARD)

    # Chart 1: publication volume over time
    ax1 = plt.subplot2grid((2, 2), (0, 0), colspan=2)
    yc = Counter(years_pool)
    s_yrs = sorted(yc.keys())
    s_cnts = [yc[y] for y in s_yrs]
    ax1.plot(s_yrs, s_cnts, marker='o', color=(0.113, 0.207, 0.341), linewidth=3.0)
    ax1.set_title("Scholarly Output Velocity Vector (Volume Over Time)",
                  fontsize=13, weight='bold', color=TEXT_BRIGHT)
    ax1.set_ylabel("Quantity", fontsize=11)
    ax1.set_facecolor(BG_ENTRY)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Chart 2: top 3 journals bar
    ax2 = plt.subplot2grid((2, 2), (1, 0))
    top_j = [item[0] for item in Counter(journals_pool).most_common(3)]
    clr_set = [(0.113, 0.207, 0.341), (0.164, 0.615, 0.560), (0.270, 0.482, 0.615)]
    wrapped_labels = ["\n".join(re.findall(r'.{1,22}(?:\s+|$)', j_name)) for j_name in top_j]

    bar_width = 0.2
    for idx, j_name in enumerate(top_j):
        j_years = [years_pool[i] for i, x in enumerate(journals_pool) if x == j_name]
        j_yc = Counter(j_years)
        j_cnts = [j_yc.get(yr, 0) for yr in s_yrs]
        offsets = [yr + (idx * bar_width) for yr in s_yrs]
        ax2.bar(offsets, j_cnts, width=bar_width, color=clr_set[idx], label=wrapped_labels[idx])

    ax2.set_title("Top 3 Core Publication Venues Density Split",
                  fontsize=12, weight='bold', color=TEXT_BRIGHT)
    ax2.set_facecolor(BG_ENTRY)
    ax2.legend(fontsize=9, loc="upper left")
    ax2.grid(True, linestyle="--", alpha=0.4)

    # Chart 3: document type pie
    ax3 = plt.subplot2grid((2, 2), (1, 1))
    tc = Counter(types_pool)
    labels = list(tc.keys())
    sizes = list(tc.values())
    pie_clrs = [(0.113, 0.207, 0.341), (0.270, 0.482, 0.615), (0.850, 0.820, 0.750)]
    ax3.pie(sizes, labels=labels, colors=pie_clrs, autopct='%1.1f%%',
            startangle=140, textprops={'fontsize': 10, 'color': TEXT_BRIGHT})
    ax3.set_title("Dataset Composition Split Percentage",
                  fontsize=12, weight='bold', color=TEXT_BRIGHT)

    fig.tight_layout()

    if render_cb:
        render_cb(fig)
    else:
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    status_cb("Trend charts compilation cycle completed.", "done")
