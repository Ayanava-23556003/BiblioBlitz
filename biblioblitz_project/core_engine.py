#!/usr/bin/env python3
"""
core_engine.py - API Async Core Download & Live Trend Analyzer Module
"""

import os
import re
import time
import csv
import customtkinter as ctk
from collections import Counter

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    _MATPLOTLIB_OK = True
except ImportError:
    _MATPLOTLIB_OK = False

from config import BG_CARD, BG_ENTRY, TEXT_BRIGHT, COUNTRY_ISO2
from utils import _http_get_json, _download_file, _safe_filename


OTHER_JOURNALS = "Other journals"
_STATES_CACHE = None
_STATES_CSV_PATHS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "states.csv"),
    r"C:\Users\ayanp\Downloads\states.csv",
]


def _clean_publisher(value):
    value = (value or "").strip()
    if not value or value.lower() in {"unknown", "none", "null", "n/a"}:
        return OTHER_JOURNALS
    return value


def _state_name(label):
    return label.split("::", 1)[1].strip() if "::" in label else label.strip()


def _journal_name(label):
    return label.split("::", 1)[1].strip() if "::" in label else label.strip()


def _geo_terms(countries=None, states=None):
    terms = []
    for country in countries or []:
        if country and country not in terms:
            terms.append(country)
    for state in states or []:
        state_name = _state_name(state)
        if state_name and state_name not in terms:
            terms.append(state_name)
    return terms


def _title_matches_geo(title, terms):
    if not terms:
        return True
    title_l = (title or "").lower()
    return any(term.lower() in title_l for term in terms)


def _query_variants(keywords, geo_terms):
    base = " ".join(k.strip()
                    for k in re.split(r"[,;|]+", keywords) if k.strip())
    if not geo_terms:
        return [base]
    return [f"{base} {term}" for term in geo_terms]


def _resolve_unpaywall_pdf(doi, email):
    if not doi:
        return ""
    res = _http_get_json(
        f"https://api.unpaywall.org/v2/{doi}", params={"email": email})
    if not res:
        return ""
    best = res.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        return best["url_for_pdf"]
    for loc in res.get("oa_locations") or []:
        if loc.get("url_for_pdf"):
            return loc["url_for_pdf"]
    return ""


def _resolve_semantic_scholar_pdf(doi):
    if not doi:
        return ""
    res = _http_get_json(
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}",
        params={"fields": "openAccessPdf"}, timeout=12)
    return ((res or {}).get("openAccessPdf") or {}).get("url") or ""


def _add_record(pool, **kwargs):
    title = (kwargs.get("title") or "").strip()
    if not title:
        return
    pool.append({
        "doi": (kwargs.get("doi") or "").strip(),
        "title": title,
        "year": kwargs.get("year"),
        "journal": kwargs.get("journal") or "Global Venue",
        "publisher": _clean_publisher(kwargs.get("publisher")),
        "pdf_url": kwargs.get("pdf_url") or "",
        "authors": kwargs.get("authors") or [],
        "abstract": kwargs.get("abstract") or "",
        "_source": kwargs.get("source") or "Open API"
    })


def _load_states_from_csv():
    global _STATES_CACHE
    if _STATES_CACHE is not None:
        return _STATES_CACHE

    country_states = {}
    for csv_path in _STATES_CSV_PATHS:
        if not os.path.exists(csv_path):
            continue
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    state = (row.get("name") or "").strip()
                    country = (row.get("country_name") or "").strip()
                    if state and country:
                        country_states.setdefault(country, set()).add(state)
            if country_states:
                break
        except Exception:
            continue

    _STATES_CACHE = {
        country: sorted(states, key=str.lower)
        for country, states in country_states.items()
    }
    return _STATES_CACHE


def fetch_live_world_states(country_name):
    """
    Loads administrative divisions from states.csv, with a web fallback only when
    the local CSV does not contain the selected country.
    """
    csv_states = _load_states_from_csv().get(country_name)
    if csv_states:
        return csv_states

    iso_code = COUNTRY_ISO2.get(country_name)
    if not iso_code:
        return []

    # Utilizing fallback web endpoint parsing matrix targeting top-level division arrays
    url = f"https://secure.geonames.org/childrenJSON"
    res = _http_get_json(
        url, params={"geonameId": "0", "username": "demo", "country": iso_code})

    # Secondary resilient public mirror fallback layer if main endpoint times out
    if not res or not res.get("geonames"):
        url = f"https://api.allorigins.win/raw"
        target = f"https://restcountries.com/v3.1/alpha/{iso_code}"
        res_raw = _http_get_json(url, params={"url": target})
        try:
            if res_raw and "subregion" in res_raw:
                return [res_raw["subregion"]]
        except:
            pass

    if res and res.get("geonames"):
        return sorted([item["name"] for item in res["geonames"] if item.get("name")])

    # Standalone emergency semantic fallback defaults to maintain stable runtime frames
    defaults = {
        "India": ["Uttarakhand", "Delhi", "West Bengal", "Maharashtra", "Karnataka", "Uttar Pradesh", "Tamil Nadu"],
        "United States": ["California", "Texas", "New York", "Florida", "Illinois", "Pennsylvania", "Ohio", "Washington"],
        "Canada": ["Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba"],
        "United Kingdom": ["England", "Scotland", "Wales", "Northern Ireland"],
        "Australia": ["New South Wales", "Queensland", "Victoria", "Western Australia", "South Australia"]
    }
    return defaults.get(country_name, ["Region Area Alpha", "Region Area Beta", "Region Area Gamma"])


def fetch_journals_for_keywords(keywords, log_cb=None):
    kw = " ".join(k.strip()
                  for k in re.split(r"[,;|]+", keywords) if k.strip())
    journal_dict = {}
    offset, fetched, target = 0, 0, 10000

    while fetched < target:
        res = _http_get_json(
            "https://api.crossref.org/works",
            params={"query": kw, "filter": "type:journal-article",
                    "rows": 1000, "offset": offset, "select": "container-title,publisher"})
        if not res or not res.get("message") or not res["message"].get("items"):
            break
        items = res["message"]["items"]
        if not items:
            break
        for item in items:
            ct = (item.get("container-title") or [""])[0]
            pub = _clean_publisher(item.get("publisher"))
            if ct and isinstance(ct, str) and ct.strip():
                ct_clean = ct.strip()
                if ct_clean not in journal_dict:
                    journal_dict[ct_clean] = pub
        fetched += len(items)
        offset += len(items)
        time.sleep(0.1)
        if log_cb:
            log_cb(f"CrossRef mapped {len(journal_dict)} unique venues...", "info")
        if len(items) < 1000:
            break

    for page in range(1, 21):
        res_oa = _http_get_json("https://api.openalex.org/works", params={
            "search": kw, "filter": "type:article", "per_page": 200, "page": page
        })
        results = (res_oa or {}).get("results") or []
        if not results:
            break
        for r in results:
            loc = r.get("primary_location") or {}
            src = loc.get("source") or {}
            journal = (src.get("display_name") or "").strip()
            publisher = _clean_publisher(src.get("host_organization_name"))
            if journal and journal not in journal_dict:
                journal_dict[journal] = publisher
        if log_cb:
            log_cb(f"OpenAlex expanded the venue map to {len(journal_dict)} journals...", "info")
        if len(results) < 200:
            break
        time.sleep(0.05)

    res_pm = _http_get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={
        "db": "pubmed", "term": kw, "retmode": "json", "retmax": 2000
    })
    ids = (((res_pm or {}).get("esearchresult") or {}).get("idlist") or [])
    if ids:
        for pos in range(0, len(ids), 200):
            res_sum = _http_get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params={
                "db": "pubmed", "id": ",".join(ids[pos:pos + 200]), "retmode": "json"
            })
            result = (res_sum or {}).get("result") or {}
            for uid in result.get("uids") or []:
                entry = result.get(uid) or {}
                journal = (entry.get("fulljournalname") or entry.get("source") or "").strip()
                if journal and journal not in journal_dict:
                    journal_dict[journal] = OTHER_JOURNALS
        if log_cb:
            log_cb(f"PubMed expanded the venue map to {len(journal_dict)} journals...", "info")

    res_core = _http_get_json("https://api.core.ac.uk/v3/search/works", params={
        "q": kw, "limit": 1000
    })
    for item in (res_core or {}).get("results") or []:
        journal = ((item.get("journals") or [{}])[0].get("title") if item.get("journals") else "") or ""
        publisher = _clean_publisher(item.get("publisher"))
        if journal and journal not in journal_dict:
            journal_dict[journal.strip()] = publisher
    if res_core and log_cb:
        log_cb(f"CORE expanded the venue map to {len(journal_dict)} journals...", "info")

    sorted_journals = [{"journal": j, "publisher": p}
                       for j, p in journal_dict.items()]
    sorted_journals.sort(key=lambda x: (
        x["publisher"].lower(), x["journal"].lower()))
    return sorted_journals


def run_post_download_integrity_purge(download_dir, log_cb):
    if not os.path.exists(download_dir):
        return
    existing_pdfs = [f for f in os.listdir(
        download_dir) if f.lower().endswith(".pdf")]
    if not existing_pdfs:
        return

    log_cb("─" * 65, "sep")
    log_cb("[POST-DOWNLOAD INTEGRITY SWEEP] Scanning file integrity chains...", "step")
    ok_c = del_c = 0

    for fname in existing_pdfs:
        fpath = os.path.join(download_dir, fname)
        is_corrupt = False
        try:
            with open(fpath, "rb") as fh:
                hdr = fh.read(4)
            if hdr != b"%PDF":
                is_corrupt = True
            elif os.path.getsize(fpath) < 100:
                is_corrupt = True
        except Exception:
            is_corrupt = True

        if is_corrupt:
            try:
                os.remove(fpath)
                del_c += 1
            except Exception:
                pass
        else:
            ok_c += 1

    log_cb(
        f"[INTEGRITY COMPLETE] Verified {ok_c} intact documents. Permanently deleted {del_c} unopenable files.", "success")
    log_cb("─" * 65, "sep")


def compile_live_api_trends(keywords, year_from, parent_frame, status_cb, render_cb=None):
    if not _MATPLOTLIB_OK:
        ctk.CTkLabel(parent_frame, text="Matplotlib missing.",
                     text_color="#E63946").pack(pady=20)
        return

    status_cb(
        "Connecting to global repositories... Querying metadata metrics indexes...", "step")
    query_str = " ".join([k.strip()
                         for k in re.split(r"[,;|]+", keywords) if k.strip()])

    years_pool = []
    journals_pool = []
    types_pool = []

    res_cr = _http_get_json("https://api.crossref.org/works", params={
        "query": query_str, "filter": f"from-pub-date:{year_from},type:journal-article", "rows": 150
    })
    if res_cr and res_cr.get("message") and res_cr["message"].get("items"):
        for item in res_cr["message"]["items"]:
            try:
                y = int(item["published"]["date-parts"][0][0])
            except:
                y = int(year_from)
            years_pool.append(y)
            journals_pool.append(
                (item.get("container-title") or ["Global/Other Open Journals"])[0])
            types_pool.append("Journal Article")

    res_oa = _http_get_json("https://api.openalex.org/works", params={
        "search": query_str, "filter": f"from_publication_date:{year_from}-01-01,type:article", "per_page": 150
    })
    if res_oa and res_oa.get("results"):
        for r in res_oa["results"]:
            years_pool.append(r.get("publication_year") or int(year_from))
            loc = r.get("primary_location") or {}
            src = loc.get("source") or {}
            journals_pool.append(src.get("display_name")
                                 or "Global/Other Open Journals")

            raw_type = r.get("type", "").lower()
            if "article" in raw_type or "journal" in raw_type:
                types_pool.append("Journal Article")
            elif "book" in raw_type:
                types_pool.append("Book/Report Chapters")
            else:
                types_pool.append("Institutional Reports/Theses")

    if not years_pool:
        status_cb(
            "[ALERT] Zero remote records found matching current keyword sequences.", "error")
        return

    status_cb(
        "Data compiled successfully. Rendering custom contrast RGB chart matrices...", "success")

    plt.rcParams.update({'font.size': 11, 'axes.labelsize': 12,
                        'axes.titlesize': 13, 'xtick.labelsize': 10, 'ytick.labelsize': 10})
    fig = plt.figure(figsize=(11, 9), facecolor=BG_CARD)

    ax1 = plt.subplot2grid((2, 2), (0, 0), colspan=2)
    yc = Counter(years_pool)
    s_yrs = sorted(yc.keys())
    s_cnts = [yc[y] for y in s_yrs]
    ax1.plot(s_yrs, s_cnts, marker='o', color=(
        0.113, 0.207, 0.341), linewidth=3.0)
    ax1.set_title("Scholarly Output Velocity Vector (Volume Over Time)",
                  fontsize=13, weight='bold', color=TEXT_BRIGHT)
    ax1.set_ylabel("Quantity", fontsize=11)
    ax1.set_facecolor(BG_ENTRY)
    ax1.grid(True, linestyle="--", alpha=0.5)

    ax2 = plt.subplot2grid((2, 2), (1, 0))
    top_j = [item[0] for item in Counter(journals_pool).most_common(3)]
    clr_set = [(0.113, 0.207, 0.341), (0.164, 0.615, 0.560),
               (0.270, 0.482, 0.615)]
    wrapped_labels = ["\n".join(re.findall(
        r'.{1,22}(?:\s+|$)', j_name)) for j_name in top_j]

    bar_width = 0.2
    for idx, j_name in enumerate(top_j):
        j_years = [years_pool[i]
                   for i, x in enumerate(journals_pool) if x == j_name]
        j_yc = Counter(j_years)
        j_cnts = [j_yc.get(yr, 0) for yr in s_yrs]
        offsets = [yr + (idx * bar_width) for yr in s_yrs]
        ax2.bar(offsets, j_cnts, width=bar_width,
                color=clr_set[idx], label=wrapped_labels[idx])

    ax2.set_title("Top 3 Core Publication Venues Density Split",
                  fontsize=12, weight='bold', color=TEXT_BRIGHT)
    ax2.set_facecolor(BG_ENTRY)
    ax2.legend(fontsize=9, loc="upper left")
    ax2.grid(True, linestyle="--", alpha=0.4)

    ax3 = plt.subplot2grid((2, 2), (1, 1))
    tc = Counter(types_pool)
    labels = list(tc.keys())
    sizes = list(tc.values())
    pie_clrs = [(0.113, 0.207, 0.341), (0.270, 0.482, 0.615),
                (0.850, 0.820, 0.750)]

    ax3.pie(sizes, labels=labels, colors=pie_clrs, autopct='%1.1f%%',
            startangle=140, textprops={'fontsize': 10, 'color': TEXT_BRIGHT})
    ax3.set_title("Dataset Composition Split Percentage",
                  fontsize=12, weight='bold', color=TEXT_BRIGHT)

    fig.tight_layout()
    if render_cb:
        render_cb(fig)
    else:
        # fallback: caller didn't supply render_cb, draw inline (main-thread only)
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
    status_cb("Trend charts compilation cycle completed.", "done")


def run_download(
    email, download_dir, keywords, max_results, year_from,
    selected_journals, countries, download_mode, log_cb, stop_event,
    states=None, basins=None
):
    os.makedirs(download_dir, exist_ok=True)
    geo_terms = _geo_terms(countries, states)
    query_list = _query_variants(keywords, geo_terms)
    selected_journal_names = {_journal_name(j).lower()
                              for j in selected_journals or []}

    log_cb(f"[INFO] Keywords   : {keywords}", "info")
    if countries:
        log_cb(f"[INFO] Country Title Search Active: {', '.join(countries)}", "info")
    if states:
        log_cb(
            f"[INFO] State Title Search Active: {', '.join(_state_name(s) for s in states)}", "info")
    if selected_journal_names:
        log_cb(f"[INFO] Journal Filter Active: {len(selected_journal_names)} selected venues", "info")
    log_cb(f"[INFO] Target Path: {download_dir}", "info")
    log_cb("─" * 65, "sep")

    all_items = []
    source_quota = max(1, min(int(max_results), 100000))

    for query_str in query_list:
        if stop_event.is_set():
            break

        log_cb(f"[API] CrossRef query: {query_str}", "step")
        crossref_fetched = 0
        while crossref_fetched < source_quota and not stop_event.is_set():
            rows = min(1000, source_quota - crossref_fetched)
            res = _http_get_json("https://api.crossref.org/works", params={
                "query.title": query_str, "filter": f"from-pub-date:{year_from},type:journal-article",
                "rows": rows, "offset": crossref_fetched, "mailto": email
            })
            items = ((res or {}).get("message") or {}).get("items") or []
            if not items:
                break
            for item in items:
                title = (item.get("title") or [""])[0]
                if not _title_matches_geo(title, geo_terms):
                    continue
                try:
                    yr = item["published"]["date-parts"][0][0]
                except Exception:
                    yr = year_from
                pdf_url = ""
                for link in item.get("link") or []:
                    if "pdf" in (link.get("content-type") or "").lower():
                        pdf_url = link.get("URL") or ""
                        break
                _add_record(
                    all_items,
                    doi=item.get("DOI", ""),
                    title=title,
                    year=yr,
                    journal=(item.get("container-title") or ["Global Venue"])[0],
                    publisher=item.get("publisher"),
                    pdf_url=pdf_url,
                    authors=item.get("author") or [],
                    abstract=item.get("abstract") or "",
                    source="CrossRef"
                )
            crossref_fetched += len(items)
            if len(items) < rows:
                break
            log_cb(f"[API] CrossRef fetched {crossref_fetched} records...", "info")
            time.sleep(0.05)

        log_cb(f"[API] OpenAlex query: {query_str}", "step")
        openalex_fetched = 0
        page = 1
        while openalex_fetched < source_quota and not stop_event.is_set():
            per_page = min(200, source_quota - openalex_fetched)
            res_oa = _http_get_json("https://api.openalex.org/works", params={
                "search": query_str, "filter": f"from_publication_date:{year_from}-01-01,type:article",
                "per_page": per_page, "page": page
            })
            results = (res_oa or {}).get("results") or []
            if not results:
                break
            for r in results:
                title = r.get("title") or ""
                if not _title_matches_geo(title, geo_terms):
                    continue
                loc = r.get("primary_location") or {}
                src = loc.get("source") or {}
                _add_record(
                    all_items,
                    doi=(r.get("doi") or "").replace("https://doi.org/", ""),
                    title=title,
                    year=r.get("publication_year"),
                    journal=src.get("display_name") or "Global Venue",
                    publisher=src.get("host_organization_name"),
                    pdf_url=(r.get("open_access") or {}).get("oa_url") or loc.get("pdf_url") or "",
                    abstract=r.get("abstract") or "",
                    source="OpenAlex"
                )
            openalex_fetched += len(results)
            page += 1
            if len(results) < per_page:
                break
            log_cb(f"[API] OpenAlex fetched {openalex_fetched} records...", "info")
            time.sleep(0.05)

        log_cb(f"[API] PubMed query: {query_str}", "step")
        res_pm = _http_get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params={
            "db": "pubmed", "term": f"{query_str} {year_from}:3000[pdat]", "retmode": "json", "retmax": source_quota
        })
        ids = (((res_pm or {}).get("esearchresult") or {}).get("idlist") or [])
        if ids:
            for pos in range(0, len(ids), 200):
                if stop_event.is_set():
                    break
                chunk = ids[pos:pos + 200]
                res_sum = _http_get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi", params={
                    "db": "pubmed", "id": ",".join(chunk), "retmode": "json"
                })
                result = (res_sum or {}).get("result") or {}
                for uid in result.get("uids") or []:
                    entry = result.get(uid) or {}
                    title = entry.get("title") or ""
                    if not _title_matches_geo(title, geo_terms):
                        continue
                    year_match = re.search(r"\d{4}", entry.get("pubdate") or "")
                    _add_record(
                        all_items,
                        title=title,
                        year=int(year_match.group(0)) if year_match else year_from,
                        journal=entry.get("fulljournalname") or entry.get("source") or "PubMed",
                        publisher=OTHER_JOURNALS,
                        source="PubMed"
                    )
                log_cb(f"[API] PubMed summarized {min(pos + 200, len(ids))} records...", "info")
                time.sleep(0.05)

        log_cb(f"[API] CORE query: {query_str}", "step")
        res_core = _http_get_json("https://api.core.ac.uk/v3/search/works", params={
            "q": query_str, "limit": min(source_quota, 1000)
        })
        for item in (res_core or {}).get("results") or []:
            title = item.get("title") or ""
            if not _title_matches_geo(title, geo_terms):
                continue
            journals = item.get("journals") or []
            _add_record(
                all_items,
                doi=item.get("doi") or "",
                title=title,
                year=item.get("yearPublished") or item.get("publishedYear") or year_from,
                journal=(journals[0].get("title") if journals else "") or "CORE",
                publisher=item.get("publisher"),
                pdf_url=item.get("downloadUrl") or item.get("fullTextLink") or "",
                abstract=item.get("abstract") or "",
                source="CORE"
            )

    seen, deduped = {}, []
    for item in all_items:
        if selected_journal_names:
            j = item["journal"].lower().strip()
            if not any(sel in j or j in sel for sel in selected_journal_names):
                continue
        d_key = item["doi"].lower().strip() or item["title"].lower().strip()
        if d_key not in seen:
            seen[d_key] = item
            deduped.append(item)
        if len(deduped) >= max_results:
            break

    log_rows = []
    if download_mode == "csv":
        log_cb("[PIPELINE] Building index sheets metadata database...", "step")
        for p in deduped:
            log_rows.append({"file": "CSV Mode Only", "title": p["title"], "year": p["year"],
                            "journal": p["journal"], "doi": p["doi"], "status": f"CSV Mode Enabled ({p['_source']})"})
    else:
        log_cb(
            f"[PIPELINE] Running data acquisition stream over {len(deduped)} targets...", "step")
        for i, p in enumerate(deduped, 1):
            if stop_event.is_set():
                break
            fname = _safe_filename(
                p["title"], p["doi"], p["year"], p["authors"], p["journal"])
            fpath = os.path.join(download_dir, fname)
            short_t = p["title"][:45]

            if os.path.exists(fpath):
                log_cb(f"[SKIP] Cache hit found: {short_t}...", "warn")
                status = "already_exists"
            else:
                url_target = ""
                if p["doi"]:
                    url_target = _resolve_unpaywall_pdf(p["doi"], email)
                if not url_target and p["doi"]:
                    url_target = _resolve_semantic_scholar_pdf(p["doi"])
                if not url_target and "http" in p["pdf_url"] and p["_source"] != "CrossRef":
                    url_target = p["pdf_url"]
                ok = _download_file(url_target, fpath, email) if url_target else False
                status = "success" if ok else "metadata_only"
                if ok:
                    log_cb(f"Downloaded {p['_source']} record: {short_t}...", "success")
                else:
                    log_cb(
                        f"[INFO] PDF unavailable; metadata retained: {short_t}...", "warn")

            log_rows.append({"file": fname, "title": p["title"], "year": p["year"],
                            "journal": p["journal"], "doi": p["doi"], "status": status})
            time.sleep(0.15)

    if log_rows:
        try:
            with open(os.path.join(download_dir, "download_log.csv"), "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(
                    fh, fieldnames=["file", "title", "year", "journal", "doi", "status"])
                w.writeheader()
                w.writerows(log_rows)
        except:
            pass

    if download_mode != "csv":
        run_post_download_integrity_purge(download_dir, log_cb)

    log_cb("[DONE] Processing thread execution completed.", "done")
