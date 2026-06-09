#!/usr/bin/env python3
"""
engine/trends.py - Live Scholarly Trend Compilation and Chart Rendering
"""

import re
import time
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

from py.config import BG_CARD, BG_ENTRY, TEXT_BRIGHT, BORDER_CLR
from py.utils import _http_get_json

# ── Colour palette ────────────────────────────────────────────────────────────
_C1 = (0.113, 0.207, 0.341)
_C2 = (0.164, 0.615, 0.560)
_C3 = (0.270, 0.482, 0.615)
_C4 = (0.850, 0.550, 0.200)
_C5 = (0.600, 0.200, 0.300)

# ── Full ISO 3166-1 alpha-2 → country name ────────────────────────────────────
_ISO2_NAME = {
    "AF": "Afghanistan", "AX": "Åland Islands", "AL": "Albania", "DZ": "Algeria",
    "AS": "American Samoa", "AD": "Andorra", "AO": "Angola", "AI": "Anguilla",
    "AQ": "Antarctica", "AG": "Antigua and Barbuda", "AR": "Argentina", "AM": "Armenia",
    "AW": "Aruba", "AU": "Australia", "AT": "Austria", "AZ": "Azerbaijan",
    "BS": "Bahamas", "BH": "Bahrain", "BD": "Bangladesh", "BB": "Barbados",
    "BY": "Belarus", "BE": "Belgium", "BZ": "Belize", "BJ": "Benin",
    "BM": "Bermuda", "BT": "Bhutan", "BO": "Bolivia", "BQ": "Bonaire",
    "BA": "Bosnia and Herzegovina", "BW": "Botswana", "BV": "Bouvet Island",
    "BR": "Brazil", "IO": "British Indian Ocean Territory", "BN": "Brunei",
    "BG": "Bulgaria", "BF": "Burkina Faso", "BI": "Burundi", "CV": "Cabo Verde",
    "KH": "Cambodia", "CM": "Cameroon", "CA": "Canada", "KY": "Cayman Islands",
    "CF": "Central African Republic", "TD": "Chad", "CL": "Chile", "CN": "China",
    "CX": "Christmas Island", "CC": "Cocos Islands", "CO": "Colombia", "KM": "Comoros",
    "CG": "Congo", "CD": "DR Congo", "CK": "Cook Islands", "CR": "Costa Rica",
    "CI": "Côte d'Ivoire", "HR": "Croatia", "CU": "Cuba", "CW": "Curaçao",
    "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark", "DJ": "Djibouti",
    "DM": "Dominica", "DO": "Dominican Republic", "EC": "Ecuador", "EG": "Egypt",
    "SV": "El Salvador", "GQ": "Equatorial Guinea", "ER": "Eritrea", "EE": "Estonia",
    "SZ": "Eswatini", "ET": "Ethiopia", "FK": "Falkland Islands", "FO": "Faroe Islands",
    "FJ": "Fiji", "FI": "Finland", "FR": "France", "GF": "French Guiana",
    "PF": "French Polynesia", "TF": "French Southern Territories", "GA": "Gabon",
    "GM": "Gambia", "GE": "Georgia", "DE": "Germany", "GH": "Ghana", "GI": "Gibraltar",
    "GR": "Greece", "GL": "Greenland", "GD": "Grenada", "GP": "Guadeloupe", "GU": "Guam",
    "GT": "Guatemala", "GG": "Guernsey", "GN": "Guinea", "GW": "Guinea-Bissau",
    "GY": "Guyana", "HT": "Haiti", "HM": "Heard Island", "VA": "Holy See",
    "HN": "Honduras", "HK": "Hong Kong", "HU": "Hungary", "IS": "Iceland", "IN": "India",
    "ID": "Indonesia", "IR": "Iran", "IQ": "Iraq", "IE": "Ireland", "IM": "Isle of Man",
    "IL": "Israel", "IT": "Italy", "JM": "Jamaica", "JP": "Japan", "JE": "Jersey",
    "JO": "Jordan", "KZ": "Kazakhstan", "KE": "Kenya", "KI": "Kiribati",
    "KP": "North Korea", "KR": "South Korea", "KW": "Kuwait", "KG": "Kyrgyzstan",
    "LA": "Laos", "LV": "Latvia", "LB": "Lebanon", "LS": "Lesotho", "LR": "Liberia",
    "LY": "Libya", "LI": "Liechtenstein", "LT": "Lithuania", "LU": "Luxembourg",
    "MO": "Macao", "MG": "Madagascar", "MW": "Malawi", "MY": "Malaysia",
    "MV": "Maldives", "ML": "Mali", "MT": "Malta", "MH": "Marshall Islands",
    "MQ": "Martinique", "MR": "Mauritania", "MU": "Mauritius", "YT": "Mayotte",
    "MX": "Mexico", "FM": "Micronesia", "MD": "Moldova", "MC": "Monaco",
    "MN": "Mongolia", "ME": "Montenegro", "MS": "Montserrat", "MA": "Morocco",
    "MZ": "Mozambique", "MM": "Myanmar", "NA": "Namibia", "NR": "Nauru", "NP": "Nepal",
    "NL": "Netherlands", "NC": "New Caledonia", "NZ": "New Zealand", "NI": "Nicaragua",
    "NE": "Niger", "NG": "Nigeria", "NU": "Niue", "NF": "Norfolk Island",
    "MK": "North Macedonia", "MP": "Northern Mariana Islands", "NO": "Norway",
    "OM": "Oman", "PK": "Pakistan", "PW": "Palau", "PS": "Palestine", "PA": "Panama",
    "PG": "Papua New Guinea", "PY": "Paraguay", "PE": "Peru", "PH": "Philippines",
    "PN": "Pitcairn", "PL": "Poland", "PT": "Portugal", "PR": "Puerto Rico",
    "QA": "Qatar", "RE": "Réunion", "RO": "Romania", "RU": "Russia", "RW": "Rwanda",
    "BL": "Saint Barthélemy", "SH": "Saint Helena", "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia", "MF": "Saint Martin", "PM": "Saint Pierre and Miquelon",
    "VC": "Saint Vincent and the Grenadines", "WS": "Samoa", "SM": "San Marino",
    "ST": "Sao Tome and Principe", "SA": "Saudi Arabia", "SN": "Senegal",
    "RS": "Serbia", "SC": "Seychelles", "SL": "Sierra Leone", "SG": "Singapore",
    "SX": "Sint Maarten", "SK": "Slovakia", "SI": "Slovenia", "SB": "Solomon Islands",
    "SO": "Somalia", "ZA": "South Africa", "GS": "South Georgia", "SS": "South Sudan",
    "ES": "Spain", "LK": "Sri Lanka", "SD": "Sudan", "SR": "Suriname",
    "SJ": "Svalbard and Jan Mayen", "SE": "Sweden", "CH": "Switzerland", "SY": "Syria",
    "TW": "Taiwan", "TJ": "Tajikistan", "TZ": "Tanzania", "TH": "Thailand",
    "TL": "Timor-Leste", "TG": "Togo", "TK": "Tokelau", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "TN": "Tunisia", "TR": "Turkey", "TM": "Turkmenistan",
    "TC": "Turks and Caicos Islands", "TV": "Tuvalu", "UG": "Uganda", "UA": "Ukraine",
    "AE": "United Arab Emirates", "GB": "United Kingdom", "US": "United States",
    "UM": "US Minor Outlying Islands", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VU": "Vanuatu", "VE": "Venezuela", "VN": "Vietnam", "VG": "British Virgin Islands",
    "VI": "US Virgin Islands", "WF": "Wallis and Futuna", "EH": "Western Sahara",
    "YE": "Yemen", "ZM": "Zambia", "ZW": "Zimbabwe",
}


def _iso_to_name(code):
    if not code:
        return ""
    code = code.upper().strip()
    # Return full name if known, otherwise return the code itself
    return _ISO2_NAME.get(code, code)


# ── Metadata harvesters ───────────────────────────────────────────────────────

def _harvest_crossref(query_str, year_from, status_cb):
    years, countries, types = [], [], []
    fetched, target = 0, 3000
    status_cb("CrossRef: harvesting publication metadata...", "step")
    while fetched < target:
        rows = min(1000, target - fetched)
        res = _http_get_json("https://api.crossref.org/works", params={
            "query":  query_str,
            "filter": f"from-pub-date:{year_from}",
            "rows":   rows,
            "offset": fetched,
            # Do NOT use select= here — it strips affiliation data
        })
        items = ((res or {}).get("message") or {}).get("items") or []
        if not items:
            break
        for item in items:
            try:
                yr = int(item["published"]["date-parts"][0][0])
            except Exception:
                yr = int(year_from)
            years.append(yr)

            raw_t = (item.get("type") or "").lower()
            if "journal" in raw_t:
                types.append("Journal Article")
            elif "book" in raw_t:
                types.append("Book / Chapter")
            elif "proceedings" in raw_t or "conference" in raw_t:
                types.append("Conference Paper")
            else:
                types.append("Other")

            # Country from author affiliation string (last comma-segment)
            for auth in (item.get("author") or []):
                for aff in (auth.get("affiliation") or []):
                    name = (aff.get("name") or "").strip()
                    if name:
                        c = name.split(",")[-1].strip()
                        if c:
                            countries.append(c)
                            break

        fetched += len(items)
        status_cb(f"CrossRef: {fetched} records...", "info")
        if len(items) < rows:
            break
        time.sleep(0.05)
    return years, countries, types


def _harvest_openalex(query_str, year_from, status_cb):
    """
    OpenAlex is the best source for country data via institution.country_code.
    We do NOT use the select= parameter so all authorship/institution fields
    are returned. We paginate up to 5000 records.
    """
    years, countries, types = [], [], []
    fetched, page, target = 0, 1, 5000
    status_cb("OpenAlex: harvesting publication metadata...", "step")
    while fetched < target:
        per = min(200, target - fetched)
        res = _http_get_json("https://api.openalex.org/works", params={
            "search":   query_str,
            "filter":   f"from_publication_date:{year_from}-01-01",
            "per_page": per,
            "page":     page,
        })
        results = (res or {}).get("results") or []
        if not results:
            break
        for r in results:
            yr = r.get("publication_year") or int(year_from)
            years.append(yr)

            raw_t = (r.get("type") or "").lower()
            if "article" in raw_t or "journal" in raw_t:
                types.append("Journal Article")
            elif "book" in raw_t:
                types.append("Book / Chapter")
            elif "proceedings" in raw_t or "conference" in raw_t:
                types.append("Conference Paper")
            elif "thesis" in raw_t or "dissertation" in raw_t:
                types.append("Thesis / Dissertation")
            elif "preprint" in raw_t or "review" in raw_t:
                types.append("Preprint / Review")
            else:
                types.append("Other")

            # Pull EVERY institution's country_code per author
            for auth in (r.get("authorships") or []):
                for inst in (auth.get("institutions") or []):
                    cc = (inst.get("country_code") or "").strip()
                    if cc:
                        name = _iso_to_name(cc)
                        if name:
                            countries.append(name)

        fetched += len(results)
        page += 1
        status_cb(
            f"OpenAlex: {fetched} records, {len(countries)} country entries...", "info")
        if len(results) < per:
            break
        time.sleep(0.05)
    return years, countries, types


def _harvest_semantic_scholar(query_str, year_from, status_cb):
    years, countries, types = [], [], []
    status_cb("Semantic Scholar: harvesting publication metadata...", "step")
    offset, limit, target = 0, 100, 1000
    while offset < target:
        res = _http_get_json(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query":  query_str,
                "fields": "year,publicationTypes",
                "limit":  limit,
                "offset": offset,
                "year":   f"{year_from}-",
            })
        items = (res or {}).get("data") or []
        if not items:
            break
        for item in items:
            yr = item.get("year") or int(year_from)
            try:
                yr = int(yr)
            except Exception:
                yr = int(year_from)
            if yr < int(year_from):
                continue
            years.append(yr)
            raw_types = [t.lower()
                         for t in (item.get("publicationTypes") or [])]
            if any("journal" in t for t in raw_types):
                types.append("Journal Article")
            elif any("book" in t for t in raw_types):
                types.append("Book / Chapter")
            elif any("conference" in t for t in raw_types):
                types.append("Conference Paper")
            elif any("review" in t for t in raw_types):
                types.append("Preprint / Review")
            else:
                types.append("Other")
        offset += len(items)
        status_cb(f"Semantic Scholar: {offset} records...", "info")
        if len(items) < limit:
            break
        time.sleep(0.1)
    return years, countries, types


def _harvest_core(query_str, year_from, status_cb):
    years, countries, types = [], [], []
    status_cb("CORE: harvesting publication metadata...", "step")
    res = _http_get_json("https://api.core.ac.uk/v3/search/works",
                         params={"q": query_str, "limit": 500})
    for item in (res or {}).get("results") or []:
        yr = item.get("yearPublished") or item.get(
            "publishedYear") or int(year_from)
        try:
            yr = int(yr)
        except Exception:
            yr = int(year_from)
        if yr < int(year_from):
            continue
        years.append(yr)
        types.append("Journal Article")
    if res:
        status_cb(f"CORE: {len(years)} records...", "info")
    return years, countries, types


# ── Chart renderer ────────────────────────────────────────────────────────────

def compile_live_api_trends(
    keywords, year_from, parent_frame, status_cb,
    render_cb=None, country_data=None
):
    if not _MATPLOTLIB_OK:
        ctk.CTkLabel(parent_frame, text="Matplotlib not installed.",
                     text_color="#E63946").pack(pady=20)
        return

    query_str = " ".join(
        k.strip() for k in re.split(r"[,;|&]+", keywords) if k.strip()
    )
    yr_int = int(year_from)

    # Each harvester returns parallel lists (years[i], countries[i], types[i])
    # We filter ALL three together so country/type counts match the year window.
    raw_years, raw_countries, raw_types = [], list(country_data or []), []

    for harvester in [_harvest_crossref, _harvest_openalex,
                      _harvest_semantic_scholar, _harvest_core]:
        try:
            yrs, ctrs, typs = harvester(query_str, yr_int, status_cb)
            raw_years.extend(yrs)
            raw_countries.extend(ctrs)
            raw_types.extend(typs)
        except Exception as e:
            status_cb(f"[WARN] {harvester.__name__} failed: {e}", "warn")

    # Filter all three in lockstep so counts stay consistent
    filtered = [
        (y, c, t)
        for y, c, t in zip(raw_years, raw_countries, raw_types)
        if yr_int <= int(y) <= 2026
    ]
    # Pad/trim country_data (pre-existing) — it isn't year-tagged, keep as-is
    extra_countries = [c for c in (country_data or []) if c and len(c) > 1]

    all_years = [r[0] for r in filtered]
    all_countries = extra_countries + [r[1]
                                       for r in filtered if r[1] and len(r[1]) > 1]
    all_types = [r[2] for r in filtered]

    if not all_years:
        status_cb(
            "[ALERT] No records found for these keywords / year range.", "error")
        return

    unique_countries = len(set(all_countries))
    total = len(all_years)
    status_cb(
        f"Rendering — {total} records | "
        f"{len(all_countries)} country entries ({unique_countries} unique) | "
        f"{len(all_types)} typed.", "success"
    )

    # ── Figure ────────────────────────────────────────────────────────────────
    plt.rcParams.update({
        "font.size": 11, "axes.labelsize": 12, "axes.titlesize": 13,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
        "axes.titlecolor": TEXT_BRIGHT, "axes.labelcolor": TEXT_BRIGHT,
        "xtick.color": TEXT_BRIGHT, "ytick.color": TEXT_BRIGHT,
    })

    has_country = bool(all_countries)
    nrows = 3 if has_country else 2
    fig = plt.figure(figsize=(12, 4.8 * nrows), facecolor=BG_CARD)

    yc = Counter(all_years)
    s_yrs = sorted(yc.keys())
    s_cnts = [yc[y] for y in s_yrs]

    # ── Chart 1: Publications vs Year ─────────────────────────────────────────
    ax1 = plt.subplot2grid((nrows, 1), (0, 0))
    ax1.plot(s_yrs, s_cnts, marker="o", color=_C1, linewidth=2.5, markersize=5)
    ax1.fill_between(s_yrs, s_cnts, alpha=0.12, color=_C1)
    ax1.set_title(f"Publications vs Year  (n={total})",
                  fontsize=13, weight="bold", color=TEXT_BRIGHT)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Number of Publications")
    ax1.set_facecolor(BG_ENTRY)
    ax1.grid(True, linestyle="--", alpha=0.45)
    if s_cnts:
        peak_yr = s_yrs[s_cnts.index(max(s_cnts))]
        peak_val = max(s_cnts)
        ax1.annotate(
            f"Peak: {peak_yr} ({peak_val})",
            xy=(peak_yr, peak_val),
            xytext=(peak_yr, peak_val + max(s_cnts) * 0.07),
            fontsize=9, color=_C1,
            arrowprops=dict(arrowstyle="->", color=_C1, lw=1.2)
        )
    for sp in ax1.spines.values():
        sp.set_edgecolor(BORDER_CLR)

    # ── Chart 2: Publications vs Country ──────────────────────────────────────
    if has_country:
        ax2 = plt.subplot2grid((nrows, 1), (1, 0))
        cc = Counter(all_countries)
        top_n = min(20, len(cc))   # show up to top 20
        top_c = cc.most_common(top_n)
        c_names = [x[0] for x in top_c][::-1]
        c_vals = [x[1] for x in top_c][::-1]
        bar_clrs = [_C2 if i % 2 == 0 else _C3 for i in range(len(c_names))]
        bars = ax2.barh(c_names, c_vals, color=bar_clrs, height=0.65)
        ax2.set_title(
            f"Publications by Country  "
            f"(top {top_n} of {unique_countries} countries, "
            f"{len(all_countries)} total entries)",
            fontsize=13, weight="bold", color=TEXT_BRIGHT)
        ax2.set_xlabel("Number of Publication Entries")
        ax2.set_facecolor(BG_ENTRY)
        ax2.grid(True, linestyle="--", alpha=0.4, axis="x")
        for bar, val in zip(bars, c_vals):
            ax2.text(
                bar.get_width() + max(c_vals) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, color=TEXT_BRIGHT)
        for sp in ax2.spines.values():
            sp.set_edgecolor(BORDER_CLR)

    # ── Chart 3: Publication Type Pie ─────────────────────────────────────────
    pie_row = 2 if has_country else 1
    ax3 = plt.subplot2grid((nrows, 1), (pie_row, 0))
    tc = Counter(all_types)
    if tc:
        labels = list(tc.keys())
        sizes = list(tc.values())
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
        ax3.text(0.5, 0.5, "No type data available",
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
        f"{len(set(all_types))} publication types.", "done"
    )
