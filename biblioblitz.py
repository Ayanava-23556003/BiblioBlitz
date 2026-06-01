#!/usr/bin/env python3
"""
BiblioBlitz v4.0
- All journals worldwide (fetched live from CrossRef/OpenAlex)
- User selects journals from a searchable multi-select list
- Region/country filter (Global or country-specific)
- Logo from file (bundled in EXE via --add-data)
- Pure Python backend, no R/PowerShell
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os, sys, re, time, json, csv, urllib.request, urllib.parse
from pathlib import Path

try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

APP_NAME    = "BiblioBlitz"
APP_VER     = "v3.2"
APP_TAGLINE = "Global Open-Access Academic Paper Downloader"

# ── Country list for region filter ────────────────────────────
COUNTRIES = [
    "Global (All Countries)",
    "Afghanistan","Albania","Algeria","Argentina","Armenia","Australia",
    "Austria","Azerbaijan","Bangladesh","Belarus","Belgium","Bolivia",
    "Bosnia and Herzegovina","Brazil","Bulgaria","Cambodia","Canada",
    "Chile","China","Colombia","Croatia","Cuba","Czech Republic","Denmark",
    "Ecuador","Egypt","Estonia","Ethiopia","Finland","France","Georgia",
    "Germany","Ghana","Greece","Hungary","India","Indonesia","Iran","Iraq",
    "Ireland","Israel","Italy","Japan","Jordan","Kazakhstan","Kenya",
    "Latvia","Lebanon","Lithuania","Malaysia","Mexico","Morocco","Nepal",
    "Netherlands","New Zealand","Nigeria","Norway","Pakistan","Peru",
    "Philippines","Poland","Portugal","Romania","Russia","Saudi Arabia",
    "Serbia","Singapore","Slovakia","South Africa","South Korea","Spain",
    "Sri Lanka","Sudan","Sweden","Switzerland","Taiwan","Thailand","Turkey",
    "Uganda","Ukraine","United Arab Emirates","United Kingdom",
    "United States","Uzbekistan","Venezuela","Vietnam","Zimbabwe",
]

# ── Country → CrossRef/PubMed affiliation search strings ──────
COUNTRY_CODES = {
    "India": "India", "China": "China", "United States": "United States",
    "United Kingdom": "United Kingdom", "Germany": "Germany", "France": "France",
    "Australia": "Australia", "Canada": "Canada", "Japan": "Japan",
    "Brazil": "Brazil", "Italy": "Italy", "Spain": "Spain",
    "Netherlands": "Netherlands", "South Korea": "South Korea",
    "Russia": "Russia", "Sweden": "Sweden", "Switzerland": "Switzerland",
    "Pakistan": "Pakistan", "Bangladesh": "Bangladesh", "Iran": "Iran",
    "Turkey": "Turkey", "Poland": "Poland", "Belgium": "Belgium",
    "Norway": "Norway", "Denmark": "Denmark", "Finland": "Finland",
    "Portugal": "Portugal", "Mexico": "Mexico", "Argentina": "Argentina",
    "South Africa": "South Africa", "Egypt": "Egypt", "Nigeria": "Nigeria",
    "Indonesia": "Indonesia", "Malaysia": "Malaysia",
    "New Zealand": "New Zealand", "Singapore": "Singapore",
    "Austria": "Austria", "Czech Republic": "Czech Republic",
    "Greece": "Greece", "Hungary": "Hungary", "Romania": "Romania",
    "Ukraine": "Ukraine", "Israel": "Israel",
}

# ── Country → ISO 3166-1 alpha-2 codes (for OpenAlex) ─────────
COUNTRY_ISO2 = {
    "Afghanistan": "AF", "Albania": "AL", "Algeria": "DZ", "Argentina": "AR",
    "Armenia": "AM", "Australia": "AU", "Austria": "AT", "Azerbaijan": "AZ",
    "Bangladesh": "BD", "Belarus": "BY", "Belgium": "BE", "Bolivia": "BO",
    "Bosnia and Herzegovina": "BA", "Brazil": "BR", "Bulgaria": "BG",
    "Cambodia": "KH", "Canada": "CA", "Chile": "CL", "China": "CN",
    "Colombia": "CO", "Croatia": "HR", "Cuba": "CU", "Czech Republic": "CZ",
    "Denmark": "DK", "Ecuador": "EC", "Egypt": "EG", "Estonia": "EE",
    "Ethiopia": "ET", "Finland": "FI", "France": "FR", "Georgia": "GE",
    "Germany": "DE", "Ghana": "GH", "Greece": "GR", "Hungary": "HU",
    "India": "IN", "Indonesia": "ID", "Iran": "IR", "Iraq": "IQ",
    "Ireland": "IE", "Israel": "IL", "Italy": "IT", "Japan": "JP",
    "Jordan": "JO", "Kazakhstan": "KZ", "Kenya": "KE", "Latvia": "LV",
    "Lebanon": "LB", "Lithuania": "LT", "Malaysia": "MY", "Mexico": "MX",
    "Morocco": "MA", "Nepal": "NP", "Netherlands": "NL", "New Zealand": "NZ",
    "Nigeria": "NG", "Norway": "NO", "Pakistan": "PK", "Peru": "PE",
    "Philippines": "PH", "Poland": "PL", "Portugal": "PT", "Romania": "RO",
    "Russia": "RU", "Saudi Arabia": "SA", "Serbia": "RS", "Singapore": "SG",
    "Slovakia": "SK", "South Africa": "ZA", "South Korea": "KR", "Spain": "ES",
    "Sri Lanka": "LK", "Sudan": "SD", "Sweden": "SE", "Switzerland": "CH",
    "Taiwan": "TW", "Thailand": "TH", "Turkey": "TR", "Uganda": "UG",
    "Ukraine": "UA", "United Arab Emirates": "AE", "United Kingdom": "GB",
    "United States": "US", "Uzbekistan": "UZ", "Venezuela": "VE",
    "Vietnam": "VN", "Zimbabwe": "ZW",
}

# ── HTTP helpers ───────────────────────────────────────────────
def _http_get_json(url, params=None, timeout=20):
    if params:
        url = url + "?" + urllib.parse.urlencode(
            {k: str(v) for k, v in params.items()})
    req = urllib.request.Request(
        url, headers={"User-Agent": "BiblioBlitz/4.0 (academic-tool)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

def _download_file(url, dest_path, email):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"BiblioBlitz/4.0 ({email})",
        "Accept": "application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r, \
             open(dest_path, "wb") as fh:
            while True:
                chunk = r.read(65536)
                if not chunk: break
                fh.write(chunk)
        return True
    except Exception:
        if os.path.exists(dest_path):
            try: os.remove(dest_path)
            except: pass
        return False

def _safe_filename(title, doi):
    t = re.sub(r"[^\w\s-]", "_", title)
    t = re.sub(r"\s+", "_", t).strip("_")[:70]
    d = doi.replace("/", "_").replace("\\", "_")
    return f"{t} [{d}].pdf"

# ── Fetch journals live from CrossRef for given keywords ───────
def fetch_journals_for_keywords(keywords, log_cb=None):
    """
    Query CrossRef & OpenAlex with keywords, collect unique journal names.
    Returns sorted list of journal names.
    """
    kw = " ".join(k.strip() for k in re.split(r"[,;|]+", keywords) if k.strip())
    journals = set()
    offset = 0
    fetched = 0
    target = 3000  # fetch up to 3000 records to gather a comprehensive journal list

    while fetched < target:
        res = _http_get_json(
            "https://api.crossref.org/works",
            params={
                "query": kw,
                "filter": "type:journal-article",
                "rows": 100,
                "offset": offset,
                "select": "container-title",
            }
        )
        if not res or not res.get("message") or not res["message"].get("items"):
            break
        items = res["message"]["items"]
        if not items:
            break
        for item in items:
            ct = (item.get("container-title") or [""])[0]
            if ct and ct.strip():
                journals.add(ct.strip())
        fetched += len(items)
        offset += len(items)
        time.sleep(0.3)
        if log_cb:
            log_cb(f"[INFO] CrossRef: {fetched} records scanned, {len(journals)} journals found…", "info")
        if len(items) < 100:
            break  # no more results

    # Also query OpenAlex for more journals — paginate multiple pages
    try:
        oa_page = 1
        oa_fetched = 0
        oa_target = 2000
        while oa_fetched < oa_target:
            res2 = _http_get_json(
                "https://api.openalex.org/works",
                params={
                    "search": kw,
                    "filter": "type:journal-article",
                    "per-page": 200,
                    "page": oa_page,
                }
            )
            if not res2 or not res2.get("results"):
                break
            batch = res2["results"]
            if not batch:
                break
            for r in batch:
                loc = r.get("primary_location") or {}
                src = loc.get("source") or {}
                name = src.get("display_name") or ""
                if name:
                    journals.add(name.strip())
            oa_fetched += len(batch)
            oa_page += 1
            time.sleep(0.3)
            if log_cb:
                log_cb(f"[INFO] OpenAlex: {oa_fetched} records scanned, {len(journals)} journals total…", "info")
            if len(batch) < 200:
                break
    except Exception:
        pass

    return sorted(journals, key=lambda x: x.lower())


# ── Main download worker ───────────────────────────────────────
def run_download(
    email, download_dir, keywords, max_results, year_from,
    selected_journals,   # list of journal names chosen by user; empty = all
    country,             # "Global (All Countries)" or country name
    log_cb, stop_event,
):
    os.makedirs(download_dir, exist_ok=True)
    kw_parts   = [k.strip() for k in re.split(r"[,;|]+", keywords) if k.strip()]
    kw_pattern = "|".join(re.escape(k.lower()) for k in kw_parts)
    query_str  = " ".join(kw_parts)

    # Build journal filter set (lower-cased)
    journal_filter = {j.lower() for j in selected_journals} if selected_journals else set()

    # Country filter string
    country_str = ""
    if country and country != "Global (All Countries)":
        country_str = COUNTRY_CODES.get(country, country)

    log_cb(f"[INFO] Keywords   : {query_str}", "info")
    log_cb(f"[INFO] Year from  : {year_from}  |  Max: {max_results:,}", "info")
    log_cb(f"[INFO] Country    : {country or 'Global'}", "info")
    log_cb(f"[INFO] Journals   : {len(journal_filter) if journal_filter else 'All'}", "info")
    log_cb(f"[INFO] Save to    : {download_dir}", "info")
    log_cb("─" * 55, "sep")

    # ── Search CrossRef ────────────────────────────────────────
    log_cb("[STEP 1/5] Searching CrossRef…", "step")
    all_items = []
    offset = 0
    cr_query = query_str
    if country_str:
        cr_query = f"{query_str} {country_str}"

    while len(all_items) < max_results:
        if stop_event.is_set(): break
        to_fetch = min(100, max_results - len(all_items))
        res = _http_get_json(
            "https://api.crossref.org/works",
            params={
                "query": cr_query,
                "filter": f"from-pub-date:{year_from},type:journal-article",
                "rows": to_fetch, "offset": offset, "mailto": email,
                "select": "DOI,title,published,container-title,author",
            }
        )
        if not res or not res.get("message") or not res["message"].get("items"):
            break
        batch = res["message"]["items"]
        if not batch: break
        # Normalise
        for item in batch:
            title = (item.get("title") or [""])[0]
            doi   = item.get("DOI", "")
            ct    = (item.get("container-title") or [""])[0]
            year  = None
            try: year = item["published"]["date-parts"][0][0]
            except: pass
            if title and doi:
                all_items.append({
                    "doi": doi, "title": title, "year": year,
                    "journal": ct, "pdf_url": "", "_source": "CrossRef"
                })
        offset += len(batch)
        time.sleep(0.4)
    log_cb(f"[INFO] CrossRef: {len(all_items)} results", "info")

    # ── Search OpenAlex ────────────────────────────────────────
    log_cb("[STEP 2/5] Searching OpenAlex…", "step")
    oa_items = []
    oa_filter = f"publication_year:>{year_from-1},type:journal-article"
    if country and country != "Global (All Countries)":
        iso2 = COUNTRY_ISO2.get(country, "")
        if iso2:
            oa_filter += f",institutions.country_code:{iso2}"
    page = 1
    while len(oa_items) < max_results:
        if stop_event.is_set(): break
        res = _http_get_json(
            "https://api.openalex.org/works",
            params={
                "search": query_str, "filter": oa_filter,
                "per-page": min(200, max_results - len(oa_items)),
                "page": page,
                "mailto": email,
            }
        )
        if not res or not res.get("results"): break
        batch = res["results"]
        if not batch: break
        for r in batch:
            doi   = (r.get("doi") or "").replace("https://doi.org/", "")
            title = r.get("title") or ""
            year  = r.get("publication_year")
            loc   = r.get("primary_location") or {}
            src   = loc.get("source") or {}
            journal = src.get("display_name") or ""
            # oa_url can be in open_access dict or primary_location
            oa_url = (r.get("open_access") or {}).get("oa_url") or \
                     loc.get("pdf_url") or ""
            if doi and title:
                oa_items.append({
                    "doi": doi, "title": title, "year": year,
                    "journal": journal, "pdf_url": oa_url or "",
                    "_source": "OpenAlex"
                })
        page += 1
        time.sleep(0.3)
    log_cb(f"[INFO] OpenAlex: {len(oa_items)} results", "info")

    # ── Search Semantic Scholar ────────────────────────────────
    log_cb("[STEP 3/5] Searching Semantic Scholar…", "step")
    ss_items = []
    ss_offset = 0
    ss_limit  = min(max_results, 500)   # S2 caps at 10k total; be polite
    ss_retries = 0
    while len(ss_items) < ss_limit:
        if stop_event.is_set(): break
        res = _http_get_json(
            "https://api.semanticscholar.org/graph/v1/paper/search/bulk",
            params={
                "query": query_str,
                "fields": "title,year,externalIds,venue,openAccessPdf",
                "limit": min(100, ss_limit - len(ss_items)),
                "offset": ss_offset,
            }
        )
        if res is None:
            # Possible 429 — back off and retry once
            ss_retries += 1
            if ss_retries <= 2:
                time.sleep(5)
                continue
            break
        if not res.get("data"): break
        ss_retries = 0
        for r in res["data"]:
            doi    = (r.get("externalIds") or {}).get("DOI", "")
            title  = r.get("title", "") or ""
            year   = r.get("year")
            journal= r.get("venue", "") or ""
            oa     = r.get("openAccessPdf") or {}
            pdf_url= oa.get("url", "")
            if title and (year is None or year >= year_from):
                ss_items.append({
                    "doi": doi, "title": title, "year": year,
                    "journal": journal, "pdf_url": pdf_url,
                    "_source": "SemanticScholar"
                })
        ss_offset += len(res["data"])
        time.sleep(1.0)  # S2 is strict on rate limits
    log_cb(f"[INFO] Semantic Scholar: {len(ss_items)} results", "info")

    # ── Search PubMed ─────────────────────────────────────────
    log_cb("[STEP 4/5] Searching PubMed…", "step")
    pm_items = []
    pm_query = query_str
    if country_str:
        pm_query += f" AND {country_str}[affiliation]"
    import datetime as _dt
    current_year = _dt.date.today().year
    s = _http_get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed", "term": f"{pm_query} AND {year_from}:{current_year}[pdat]",
                "retmax": min(max_results, 10000), "retmode": "json"}
    )
    if s:
        ids = s.get("esearchresult", {}).get("idlist", [])
        for i in range(0, min(len(ids), max_results), 200):
            if stop_event.is_set(): break
            summ = _http_get_json(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "pubmed", "id": ",".join(ids[i:i+200]), "retmode": "json"}
            )
            if not summ: continue
            result = summ.get("result", {})
            for uid in ids[i:i+200]:
                rec = result.get(uid, {})
                title   = rec.get("title", "")
                journal = rec.get("fulljournalname", "")
                year    = None
                try: year = int(rec.get("pubdate", "")[:4])
                except: pass
                doi = ""
                for aid in rec.get("articleids", []):
                    if aid.get("idtype") == "doi":
                        doi = aid.get("value", ""); break
                if title:
                    pm_items.append({
                        "doi": doi, "title": title, "year": year,
                        "journal": journal, "pdf_url": "", "_source": "PubMed"
                    })
            time.sleep(0.34)
    log_cb(f"[INFO] PubMed: {len(pm_items)} results", "info")

    # ── Search CORE ───────────────────────────────────────────
    log_cb("[STEP 5/5] Searching CORE…", "step")
    core_items = []
    core_q = query_str + (f" {country_str}" if country_str else "")
    c_page = 1
    while len(core_items) < min(max_results, 500):
        if stop_event.is_set(): break
        res = _http_get_json(
            "https://api.core.ac.uk/v3/search/works",
            params={"q": core_q,
                    "limit": min(100, max_results - len(core_items)),
                    "offset": (c_page-1)*100}
        )
        if not res or not res.get("results"): break
        for r in res["results"]:
            doi    = r.get("doi", "") or ""
            title  = r.get("title", "") or ""
            year   = r.get("yearPublished")
            jlist  = r.get("journals") or [{}]
            journal= jlist[0].get("title", "") if jlist else ""
            pdf_url= r.get("downloadUrl", "") or ""
            if title and (year is None or year >= year_from):
                core_items.append({
                    "doi": doi, "title": title, "year": year,
                    "journal": journal, "pdf_url": pdf_url, "_source": "CORE"
                })
        c_page += 1
        time.sleep(0.4)
    log_cb(f"[INFO] CORE: {len(core_items)} results", "info")

    # ── Merge & Deduplicate ───────────────────────────────────
    all_raw = all_items + oa_items + ss_items + pm_items + core_items
    log_cb(f"[INFO] Total raw: {len(all_raw)} — deduplicating…", "info")
    seen = {}
    deduped = []
    for item in all_raw:
        doi = (item.get("doi") or "").strip().lower()
        if not doi:
            deduped.append(item); continue
        if doi not in seen:
            seen[doi] = item; deduped.append(item)
        else:
            if item.get("pdf_url") and not seen[doi].get("pdf_url"):
                seen[doi]["pdf_url"] = item["pdf_url"]
    log_cb(f"[INFO] After dedup: {len(deduped)}", "info")

    # ── Journal filter ────────────────────────────────────────
    if journal_filter:
        def _jmatch(j):
            if not j:
                return False
            jl = j.lower()
            for f in journal_filter:
                if f in jl or jl in f:
                    return True
            return False
        papers = [p for p in deduped if _jmatch(p.get("journal") or "")]
        log_cb(f"[INFO] After journal filter: {len(papers)}", "info")
    else:
        papers = deduped

    # Keyword filter on title (match ANY keyword, not all)
    # Build individual keyword patterns
    kw_list = [re.escape(k.lower()) for k in kw_parts]
    if kw_list:
        filtered_kw = [
            p for p in papers
            if p.get("title") and any(
                re.search(pat, p["title"].lower()) for pat in kw_list
            )
        ]
        # Only apply if it doesn't eliminate everything
        if filtered_kw:
            papers = filtered_kw
            log_cb(f"[INFO] After keyword filter: {len(papers)}", "info")
        else:
            log_cb(f"[INFO] Keyword filter skipped (would remove all results); keeping {len(papers)}", "warn")
    else:
        log_cb(f"[INFO] After keyword filter: {len(papers)}", "info")

    if not papers:
        log_cb("[WARN] No papers matched. Try broader keywords or select more journals.", "warn")
        return

    # ── Unpaywall supplement ──────────────────────────────────
    need_oa = [p for p in papers if not p.get("pdf_url") and p.get("doi")]
    log_cb(f"[INFO] Checking Unpaywall for {len(need_oa)} papers…", "info")
    for i, p in enumerate(need_oa, 1):
        if stop_event.is_set(): break
        enc = urllib.parse.quote(p["doi"], safe="")
        data = _http_get_json(f"https://api.unpaywall.org/v2/{enc}",
                              params={"email": email})
        if data:
            loc = data.get("best_oa_location") or {}
            p["pdf_url"] = loc.get("url_for_pdf") or loc.get("url") or ""
        if i % 10 == 0 or i == len(need_oa):
            log_cb(f"[INFO] Unpaywall: {i}/{len(need_oa)}", "info")
        time.sleep(0.25)

    papers_oa = [p for p in papers if p.get("pdf_url")]
    log_cb(f"[INFO] Papers with PDF: {len(papers_oa)}", "info")

    if not papers_oa:
        log_cb("[WARN] No open-access PDFs found.", "warn")
        return

    # ── Download ──────────────────────────────────────────────
    log_cb("[STEP] Downloading PDFs…", "step")
    n_ok = n_skip = n_err = 0
    log_rows = []

    for i, p in enumerate(papers_oa, 1):
        if stop_event.is_set():
            log_cb("[INFO] Stopped by user.", "warn"); break
        fname = _safe_filename(p["title"], p.get("doi") or f"no-doi-{i}")
        fpath = os.path.join(download_dir, fname)
        short = p["title"][:55]
        if os.path.exists(fpath):
            status = "already_exists"; n_skip += 1
            log_cb(f"[SKIP]  [{i}/{len(papers_oa)}] {short}", "warn")
        else:
            ok = _download_file(p["pdf_url"], fpath, email)
            if ok:
                status = "success"; n_ok += 1
                log_cb(f"[OK]    [{i}/{len(papers_oa)}] {short}", "success")
            else:
                status = "error"; n_err += 1
                log_cb(f"[FAIL]  [{i}/{len(papers_oa)}] {short}", "error")
        log_rows.append({
            "title": p["title"], "doi": p.get("doi",""),
            "year": p.get("year",""), "journal": p.get("journal",""),
            "country_filter": country or "Global",
            "source": p.get("_source",""), "status": status,
            "pdf_url": p.get("pdf_url",""), "file": fname,
        })
        time.sleep(0.5)

    if log_rows:
        log_path = os.path.join(download_dir, "download_log.csv")
        try:
            with open(log_path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=log_rows[0].keys())
                w.writeheader(); w.writerows(log_rows)
            log_cb(f"[LOG]   Saved: {log_path}", "info")
        except Exception as e:
            log_cb(f"[WARN]  CSV error: {e}", "warn")

    log_cb("─" * 55, "sep")
    log_cb(f"[DONE]  Downloaded: {n_ok}  |  Skipped: {n_skip}  |  Errors: {n_err}", "done")


def run_pdf_integrity_check(folder, log_cb, stop_event, email=""):
    bad_folder = os.path.join(folder, "Corrupted_PDFs")
    os.makedirs(bad_folder, exist_ok=True)
    pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
    log_cb(f"[INFO] Found {len(pdfs)} PDF(s).", "info")
    ok_count = bad_count = 0
    results = []
    bad_files = []  # list of (original_fname, dest_path)

    for fname in pdfs:
        if stop_event.is_set(): break
        fpath = os.path.join(folder, fname)
        status = "OK"
        try:
            with open(fpath, "rb") as fh:
                hdr = fh.read(8)
            if len(hdr) < 4: status = "TooSmall"
            elif hdr[:4] != b"%PDF": status = "InvalidHeader"
        except Exception as e:
            status = f"CannotOpen:{e}"
        size_mb = round(os.path.getsize(fpath)/(1024*1024), 3) if os.path.exists(fpath) else 0
        if status == "OK":
            ok_count += 1
            log_cb(f"[OK]    {fname}", "success")
        else:
            dest = os.path.join(bad_folder, fname)
            c = 1
            while os.path.exists(dest):
                base, ext = os.path.splitext(fname)
                dest = os.path.join(bad_folder, f"{base}_dup{c}{ext}"); c += 1
            try:
                os.replace(fpath, dest)
                log_cb(f"[MOVED] {fname} → Corrupted_PDFs/ ({status})", "warn")
                bad_files.append((fname, fpath))
            except Exception as e:
                log_cb(f"[ERROR] {fname}: {e}", "error")
                status = f"MoveError:{status}"
            bad_count += 1
        results.append({"FileName": fname, "Status": status, "SizeMB": size_mb})

    try:
        rp = os.path.join(folder, "pdf_integrity_report.csv")
        with open(rp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["FileName","Status","SizeMB"])
            w.writeheader(); w.writerows(results)
        log_cb(f"[REPORT] {rp}", "info")
    except Exception as e:
        log_cb(f"[WARN] {e}", "warn")

    log_cb(f"[DONE]  OK: {ok_count}  |  Corrupted/moved: {bad_count}", "done")

    # ── Re-download corrupted files from download_log.csv ──────
    if bad_files and not stop_event.is_set():
        log_cb("─" * 55, "sep")
        log_cb(f"[STEP] Attempting re-download for {len(bad_files)} corrupted file(s)…", "step")
        log_path = os.path.join(folder, "download_log.csv")
        # Build a lookup: filename → pdf_url from log
        url_map = {}
        if os.path.exists(log_path):
            try:
                with open(log_path, newline="", encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        fn = row.get("file", "")
                        url = row.get("pdf_url", "") or row.get("url", "")
                        doi = row.get("doi", "")
                        if fn and (url or doi):
                            url_map[fn] = {"url": url, "doi": doi,
                                           "title": row.get("title", "")}
            except Exception as e:
                log_cb(f"[WARN] Could not read download_log.csv: {e}", "warn")

        re_ok = re_fail = re_skip = 0
        for fname, fpath in bad_files:
            if stop_event.is_set(): break
            info = url_map.get(fname)
            if not info:
                log_cb(f"[SKIP]  No URL in log for: {fname[:60]}", "warn")
                re_skip += 1
                continue

            pdf_url = info.get("url", "")
            doi = info.get("doi", "")

            # Try Unpaywall if no direct url
            if not pdf_url and doi and email:
                enc = urllib.parse.quote(doi, safe="")
                data = _http_get_json(f"https://api.unpaywall.org/v2/{enc}",
                                      params={"email": email})
                if data:
                    loc = data.get("best_oa_location") or {}
                    pdf_url = loc.get("url_for_pdf") or loc.get("url") or ""

            if not pdf_url:
                log_cb(f"[SKIP]  No PDF URL found for: {fname[:60]}", "warn")
                re_skip += 1
                continue

            log_cb(f"[RETRY] {fname[:60]}", "info")
            ok = _download_file(pdf_url, fpath, email or "biblioblitz@tool")
            if ok:
                # Verify the re-downloaded file
                try:
                    with open(fpath, "rb") as fh:
                        hdr2 = fh.read(4)
                    if hdr2 == b"%PDF":
                        log_cb(f"[OK]    Re-downloaded successfully: {fname[:60]}", "success")
                        re_ok += 1
                    else:
                        log_cb(f"[FAIL]  Still corrupt after retry: {fname[:60]}", "error")
                        if os.path.exists(fpath):
                            try: os.remove(fpath)
                            except: pass
                        re_fail += 1
                except Exception:
                    re_fail += 1
            else:
                log_cb(f"[FAIL]  Re-download failed: {fname[:60]}", "error")
                re_fail += 1
            time.sleep(0.5)

        log_cb(f"[DONE]  Re-download: {re_ok} success  |  {re_fail} failed  |  {re_skip} skipped", "done")


# ── Placeholder helper ─────────────────────────────────────────
def _add_placeholder(entry, placeholder, ph_color="#4B5563", act_color="#CBD5E1"):
    entry._ph_text  = placeholder
    entry._ph_color = ph_color
    entry._act_color= act_color
    def _show():
        entry.configure(text_color=ph_color)
        if not entry.get(): entry.insert(0, placeholder)
    def _hide(e=None):
        if entry.get() == placeholder: entry.delete(0,"end")
        entry.configure(text_color=act_color)
    def _leave(e=None):
        if not entry.get(): _show()
    def _key(e=None):
        if entry.cget("text_color") == ph_color: _hide()
    _show()
    entry.bind("<FocusIn>",  _hide)
    entry.bind("<FocusOut>", _leave)
    entry.bind("<Key>",      _key)

def _get_val(entry):
    v = entry.get().strip()
    ph = getattr(entry, "_ph_text", None)
    return "" if v == ph else v


# ══════════════════════════════════════════════════════════════
#  JOURNAL SELECTOR DIALOG
# ══════════════════════════════════════════════════════════════
class JournalSelectorDialog(ctk.CTkToplevel):
    """
    Modal dialog showing all fetched journals as a searchable
    multi-select checklist. Returns selected journal names.
    """
    def __init__(self, parent, journals):
        super().__init__(parent)
        self.title("Select Journals")
        self.geometry("560x580")
        self.resizable(True, True)
        self.grab_set()
        self.focus_set()

        self._all_journals = journals
        self._vars         = {}   # journal → BooleanVar
        self._selected     = []
        self._filtered     = list(journals)

        self._build()

    def _build(self):
        # Search bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))

        ctk.CTkLabel(top, text="🔍 Filter journals:",
                     font=ctk.CTkFont(size=11), text_color="#CBD5E1"
                     ).pack(side="left", padx=(0,8))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(top, textvariable=self._search_var, height=32,
                     font=ctk.CTkFont(size=11),
                     fg_color="#0D1117", border_color="#1E3A5F", border_width=1
                     ).pack(side="left", fill="x", expand=True)

        # Select all / none
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(btn_row, text="Select All", width=100, height=28,
                      fg_color="#1E3A5F", hover_color="#2563EB",
                      font=ctk.CTkFont(size=10),
                      command=self._select_all).pack(side="left", padx=(0,6))
        ctk.CTkButton(btn_row, text="Deselect All", width=100, height=28,
                      fg_color="#1E293B", hover_color="#334155",
                      font=ctk.CTkFont(size=10),
                      command=self._deselect_all).pack(side="left")

        self._count_lbl = ctk.CTkLabel(btn_row, text="",
                                        font=ctk.CTkFont(size=10),
                                        text_color="#4B5563")
        self._count_lbl.pack(side="right")

        # Scrollable checklist
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="#060D18", corner_radius=8,
            scrollbar_button_color="#1E293B")
        self._scroll.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        # Bottom buttons
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=14, pady=(0,12))

        ctk.CTkButton(bf, text="✔  Confirm Selection", height=36,
                      fg_color="#2563EB", hover_color="#1D4ED8",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._confirm).pack(side="left", fill="x", expand=True, padx=(0,6))
        ctk.CTkButton(bf, text="✖  Cancel", height=36, width=90,
                      fg_color="#450A0A", hover_color="#7F1D1D",
                      font=ctk.CTkFont(size=12),
                      command=self.destroy).pack(side="right")

        self._render_list()

    def _render_list(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        for jname in self._filtered:
            if jname not in self._vars:
                self._vars[jname] = tk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(
                self._scroll, text=jname,
                variable=self._vars[jname],
                font=ctk.CTkFont(size=10),
                text_color="#CBD5E1",
                fg_color="#2563EB", hover_color="#1D4ED8",
                checkmark_color="#FFFFFF",
                command=self._update_count
            )
            cb.pack(anchor="w", padx=8, pady=2)
        self._update_count()

    def _on_search(self, *_):
        q = self._search_var.get().lower()
        self._filtered = [j for j in self._all_journals if q in j.lower()]
        self._render_list()

    def _select_all(self):
        for j in self._filtered:
            if j in self._vars: self._vars[j].set(True)
        self._update_count()

    def _deselect_all(self):
        for j in self._filtered:
            if j in self._vars: self._vars[j].set(False)
        self._update_count()

    def _update_count(self):
        n = sum(1 for v in self._vars.values() if v.get())
        self._count_lbl.configure(text=f"{n} selected")

    def _confirm(self):
        self._selected = [j for j, v in self._vars.items() if v.get()]
        self.destroy()

    def get_selected(self):
        return self._selected


# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════
class BiblioBlitzApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_NAME}  ·  {APP_TAGLINE}")
        icon_path = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'biblioblitz.ico')
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        self.geometry("1100x800")
        self.minsize(900, 680)

        self._running       = False
        self._stop_event    = threading.Event()
        self._log_lines     = 0
        self._selected_journals = []   # user-chosen journal list
        self._fetched_journals  = []   # fetched from APIs

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self._running:
            if not messagebox.askyesno("Download Running",
                "A download is running. Stop and exit BiblioBlitz?"):
                return
            self._stop_event.set()
        else:
            if not messagebox.askyesno("Exit BiblioBlitz",
                "Are you sure you want to close BiblioBlitz?"):
                return
        self.destroy()

    # ── Build UI ──────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 0))

        left = ctk.CTkFrame(body, width=370, fg_color="#111827", corner_radius=10)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self._build_config_panel(left)

        right = ctk.CTkFrame(body, fg_color="#0D1117", corner_radius=10)
        right.pack(side="left", fill="both", expand=True)
        self._build_log_panel(right)

        self._build_footer()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="#0B1628", corner_radius=0, height=68)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # ── Logo: try bundle path, then Downloads, then glyph ──
        logo_loaded = False
        if _PIL_OK:
            try:
                base = getattr(sys, "_MEIPASS",
                               os.path.dirname(os.path.abspath(__file__)))
                candidates = [
                    os.path.join(base, "biblioblitz.png"),
                ]
                for logo_path in candidates:
                    if os.path.isfile(logo_path):
                        img = Image.open(logo_path).convert("RGBA")
                        img.thumbnail((44, 44), Image.LANCZOS)
                        ctk_img = ctk.CTkImage(
                            light_image=img, dark_image=img,
                            size=(img.width, img.height)
                        )
                        ctk.CTkLabel(hdr, image=ctk_img, text="",
                                     bg_color="transparent"
                                     ).pack(side="left", padx=(14, 8))
                        # keep reference so GC doesn't collect it
                        hdr._logo_img = ctk_img
                        logo_loaded = True
                        break
            except Exception:
                pass

        if not logo_loaded:
            ctk.CTkLabel(hdr, text="✦", font=ctk.CTkFont(size=26),
                         text_color="#3B82F6"
                         ).pack(side="left", padx=(18, 6))

        ctk.CTkLabel(hdr, text=APP_NAME,
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color="#3B82F6"
                     ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(hdr, text=APP_TAGLINE,
                     font=ctk.CTkFont(size=12), text_color="#64748B"
                     ).pack(side="left")

        ctk.CTkLabel(hdr, text=APP_VER,
                     font=ctk.CTkFont(size=11), text_color="#374151"
                     ).pack(side="right", padx=(0, 8))
        ctk.CTkLabel(hdr, text="⬤  Pure Python  •  5 APIs  •  All Journals",
                     font=ctk.CTkFont(size=11), text_color="#34D399"
                     ).pack(side="right", padx=(20, 8))

    def _field_label(self, parent, text, hint=None):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#CBD5E1"
                     ).pack(anchor="w", padx=12, pady=(6, 1))
        if hint:
            ctk.CTkLabel(parent, text=hint,
                         font=ctk.CTkFont(size=9), text_color="#4B5563"
                         ).pack(anchor="w", padx=12, pady=(0, 3))

    def _build_config_panel(self, parent):
        ctk.CTkLabel(parent, text="CONFIGURATION",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#374151"
                     ).pack(anchor="w", padx=16, pady=(14, 0))
        ctk.CTkLabel(parent, text="Search & Download Settings",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#F1F5F9"
                     ).pack(anchor="w", padx=16, pady=(2, 4))
        ctk.CTkFrame(parent, height=1, fg_color="#1E293B"
                     ).pack(fill="x", padx=16, pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_button_color="#1E293B")
        scroll.pack(fill="both", expand=True, padx=4)

        # Email
        self._field_label(scroll, "📧  Email Address",
                          hint="Used for CrossRef & Unpaywall API")
        self._e_email = ctk.CTkEntry(scroll, height=35,
                                      font=ctk.CTkFont(size=11),
                                      fg_color="#0D1117",
                                      border_color="#1E3A5F", border_width=1)
        self._e_email.pack(fill="x", padx=12, pady=(0, 12))
        _add_placeholder(self._e_email, "e.g. yourname@university.edu")

        # Download dir
        self._field_label(scroll, "📁  Download Directory")
        df = ctk.CTkFrame(scroll, fg_color="transparent")
        df.pack(fill="x", padx=12, pady=(0, 12))
        self.v_dir = ctk.StringVar(value=str(Path.home() / "Papers"))
        ctk.CTkEntry(df, textvariable=self.v_dir, height=35,
                     font=ctk.CTkFont(size=11),
                     fg_color="#0D1117", border_color="#1E3A5F", border_width=1
                     ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(df, text="⋯", width=38, height=35,
                      fg_color="#1E293B", hover_color="#334155",
                      font=ctk.CTkFont(size=14),
                      command=self._browse_dir).pack(side="right")

        # Keywords
        self._field_label(scroll, "🔍  Keywords",
                          hint="Comma-separated • press 'Fetch Journals' after entering")
        self._e_keywords = ctk.CTkEntry(scroll, height=35,
                                         font=ctk.CTkFont(size=11),
                                         fg_color="#0D1117",
                                         border_color="#1E3A5F", border_width=1)
        self._e_keywords.pack(fill="x", padx=12, pady=(0, 6))
        _add_placeholder(self._e_keywords, "e.g. soil erosion, runoff, climate")

        # Fetch Journals button
        self._btn_fetch_journals = ctk.CTkButton(
            scroll, text="🔎   Fetch Journals for These Keywords",
            height=34, font=ctk.CTkFont(size=11),
            fg_color="#0F2040", hover_color="#1E3A5F",
            border_width=1, border_color="#1E3A5F",
            command=self._fetch_journals_clicked)
        self._btn_fetch_journals.pack(fill="x", padx=12, pady=(0, 4))

        self._lbl_journals_status = ctk.CTkLabel(
            scroll, text="No journals loaded yet",
            font=ctk.CTkFont(size=9), text_color="#4B5563")
        self._lbl_journals_status.pack(anchor="w", padx=12, pady=(0, 4))

        # Select Journals button
        self._btn_select_journals = ctk.CTkButton(
            scroll, text="📋   Select Journals (0 selected — all used)",
            height=34, font=ctk.CTkFont(size=11),
            fg_color="#1E293B", hover_color="#334155",
            border_width=1, border_color="#374151",
            command=self._open_journal_selector,
            state="disabled")
        self._btn_select_journals.pack(fill="x", padx=12, pady=(0, 12))

        # Region / Country
        self._field_label(scroll, "🌍  Region / Country Filter",
                          hint="Choose country to filter by author affiliation")
        self.v_country = ctk.StringVar(value="Global (All Countries)")
        ctk.CTkComboBox(
            scroll, variable=self.v_country,
            values=COUNTRIES, height=35,
            font=ctk.CTkFont(size=11),
            fg_color="#0D1117", border_color="#1E3A5F", border_width=1,
            button_color="#1E3A5F", button_hover_color="#2563EB",
            dropdown_fg_color="#0D1117", dropdown_hover_color="#1E293B",
            state="readonly"
        ).pack(fill="x", padx=12, pady=(0, 12))

        # Max papers
        self._field_label(scroll, "📦  Max Papers to Fetch")
        self.v_max = ctk.IntVar(value=1000)
        mf = ctk.CTkFrame(scroll, fg_color="transparent")
        mf.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkEntry(mf, textvariable=self.v_max, width=90, height=35,
                     font=ctk.CTkFont(size=11),
                     fg_color="#0D1117", border_color="#1E3A5F", border_width=1
                     ).pack(side="left", padx=(0, 8))
        ctk.CTkSlider(mf, from_=100, to=100000, number_of_steps=999,
                      variable=self.v_max,
                      button_color="#3B82F6", button_hover_color="#2563EB",
                      progress_color="#1E3A5F"
                      ).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(scroll, text="100 — 1,00,000 papers",
                     font=ctk.CTkFont(size=9), text_color="#4B5563"
                     ).pack(anchor="e", padx=12, pady=(0, 10))

        # Starting year
        self._field_label(scroll, "📅  Starting Year")
        self.v_year = ctk.IntVar(value=2015)
        yf = ctk.CTkFrame(scroll, fg_color="transparent")
        yf.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkEntry(yf, textvariable=self.v_year, width=90, height=35,
                     font=ctk.CTkFont(size=11),
                     fg_color="#0D1117", border_color="#1E3A5F", border_width=1
                     ).pack(side="left", padx=(0, 8))
        ctk.CTkSlider(yf, from_=1990, to=2025, number_of_steps=35,
                      variable=self.v_year,
                      button_color="#3B82F6", button_hover_color="#2563EB",
                      progress_color="#1E3A5F"
                      ).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(scroll, text="1990 — 2025",
                     font=ctk.CTkFont(size=9), text_color="#4B5563"
                     ).pack(anchor="e", padx=12, pady=(0, 10))

        # PDF Integrity check
        ctk.CTkFrame(scroll, height=1, fg_color="#1E293B"
                     ).pack(fill="x", padx=12, pady=(6, 12))
        ctk.CTkLabel(scroll, text="🔬  PDF Integrity Check",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#93C5FD").pack(anchor="w", padx=12)
        ctk.CTkLabel(scroll,
                     text="Scans folder for corrupt PDFs and quarantines them.",
                     font=ctk.CTkFont(size=10), text_color="#6B7280",
                     justify="left").pack(anchor="w", padx=12, pady=(3, 8))
        ctk.CTkButton(scroll, text="🔬   Run PDF Integrity Check",
                      height=36, fg_color="#0F2040", hover_color="#1E3A5F",
                      border_width=1, border_color="#1E3A5F",
                      font=ctk.CTkFont(size=12),
                      command=self._run_pdf_check
                      ).pack(fill="x", padx=12, pady=(0, 14))

    def _build_log_panel(self, parent):
        lhdr = ctk.CTkFrame(parent, fg_color="transparent")
        lhdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(lhdr, text="Activity Log",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#F1F5F9").pack(side="left")
        ctk.CTkButton(lhdr, text="Clear", width=60, height=26,
                      fg_color="#1E293B", hover_color="#334155",
                      font=ctk.CTkFont(size=10),
                      command=self._clear_log).pack(side="right")

        stats = ctk.CTkFrame(parent, fg_color="#0B1628",
                              corner_radius=8, height=58)
        stats.pack(fill="x", padx=14, pady=(0, 8))
        stats.pack_propagate(False)
        self._s_fetched  = self._make_stat(stats, "Fetched",     "#3B82F6")
        self._s_journals = self._make_stat(stats, "Journals",    "#A78BFA")
        self._s_oa       = self._make_stat(stats, "Open Access", "#8B5CF6")
        self._s_done     = self._make_stat(stats, "Downloaded",  "#10B981")
        self._s_errors   = self._make_stat(stats, "Errors",      "#EF4444")
        self._s_skipped  = self._make_stat(stats, "Skipped",     "#F59E0B")

        self._log = ctk.CTkTextbox(parent,
                                    font=ctk.CTkFont(family="Consolas", size=11),
                                    fg_color="#060D18", text_color="#CBD5E1",
                                    corner_radius=8, wrap="none",
                                    scrollbar_button_color="#1E293B")
        self._log.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._log.configure(state="disabled")
        for tag, color in [
            ("step","#A78BFA"),("info","#60A5FA"),("success","#34D399"),
            ("warn","#FCD34D"),("error","#F87171"),("sep","#1E293B"),("done","#6EE7B7")
        ]:
            self._log.tag_config(tag, foreground=color)

    def _make_stat(self, parent, label, color):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", expand=True)
        val = ctk.CTkLabel(f, text="—",
                            font=ctk.CTkFont(size=17, weight="bold"),
                            text_color=color)
        val.pack(pady=(6, 0))
        ctk.CTkLabel(f, text=label,
                     font=ctk.CTkFont(size=9), text_color="#374151").pack()
        return val

    def _build_footer(self):
        foot = ctk.CTkFrame(self, fg_color="#060D18", corner_radius=0, height=70)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        self._pbar = ctk.CTkProgressBar(foot, height=3, mode="indeterminate",
                                         progress_color="#3B82F6",
                                         fg_color="#0B1628")
        self._pbar.pack(fill="x")
        self._pbar.set(0)

        btn_row = ctk.CTkFrame(foot, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(6, 0))

        self._btn_start = ctk.CTkButton(
            btn_row, text="▶   Start Download", height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563EB", hover_color="#1D4ED8",
            command=self._start_download)
        self._btn_start.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._btn_stop = ctk.CTkButton(
            btn_row, text="⏹  Stop", height=38, width=90,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#450A0A", hover_color="#7F1D1D",
            state="disabled", command=self._stop)
        self._btn_stop.pack(side="right")

        self._lbl_status = ctk.CTkLabel(
            foot, text="Ready  •  No R or Python required",
            font=ctk.CTkFont(size=10), text_color="#374151")
        self._lbl_status.pack(pady=(2, 0))

    # ── Helpers ──────────────────────────────────────────────

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select Download Folder")
        if d: self.v_dir.set(d)

    def _set_running(self, state):
        self._running = state
        self.after(0, lambda: self._btn_start.configure(
            state="disabled" if state else "normal"))
        self.after(0, lambda: self._btn_stop.configure(
            state="normal" if state else "disabled"))
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
        patterns = [
            (r"Total raw.*?(\d+)", self._s_fetched),
            (r"After journal filter: (\d+)|After keyword filter: (\d+)", self._s_journals),
            (r"Papers with PDF: (\d+)", self._s_oa),
            (r"Downloaded: (\d+)", self._s_done),
            (r"Errors: (\d+)", self._s_errors),
            (r"Skipped: (\d+)", self._s_skipped),
        ]
        for pat, lbl in patterns:
            m = re.search(pat, line)
            if m:
                v = next(g for g in m.groups() if g is not None) if m.lastindex and m.lastindex > 1 else m.group(1)
                self.after(0, lambda v=v, l=lbl: l.configure(text=v))

    # ── Fetch journals ────────────────────────────────────────

    def _fetch_journals_clicked(self):
        keywords = _get_val(self._e_keywords)
        if not keywords:
            messagebox.showerror("Input Error", "Enter keywords first.")
            return
        self._btn_fetch_journals.configure(state="disabled",
                                            text="⏳ Fetching journals…")
        self._lbl_journals_status.configure(text="Fetching from APIs…",
                                             text_color="#FCD34D")
        self._append_log("[INFO] Fetching journal list from CrossRef & OpenAlex…", "step")

        def _worker():
            journals = fetch_journals_for_keywords(keywords, self._append_log)
            self._fetched_journals = journals
            self._selected_journals = []
            def _done():
                self._btn_fetch_journals.configure(
                    state="normal",
                    text="🔎   Fetch Journals for These Keywords")
                self._lbl_journals_status.configure(
                    text=f"✅ {len(journals)} journals loaded",
                    text_color="#34D399")
                self._btn_select_journals.configure(
                    state="normal",
                    text=f"📋   Select Journals (0 of {len(journals)} — all used)")
                self._append_log(
                    f"[INFO] {len(journals)} unique journals loaded.", "success")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def _open_journal_selector(self):
        if not self._fetched_journals:
            messagebox.showinfo("No Journals",
                "Please click 'Fetch Journals' first.")
            return
        dlg = JournalSelectorDialog(self, self._fetched_journals)
        self.wait_window(dlg)
        self._selected_journals = dlg.get_selected()
        n = len(self._selected_journals)
        total = len(self._fetched_journals)
        if n == 0:
            label = f"📋   Select Journals (0 selected — all {total} used)"
        else:
            label = f"📋   Select Journals ({n} of {total} selected)"
        self._btn_select_journals.configure(text=label)
        self._append_log(
            f"[INFO] Journal selection: {n if n else 'all'} journal(s) active.", "info")

    # ── Validate ──────────────────────────────────────────────

    def _validate_inputs(self):
        email    = _get_val(self._e_email)
        keywords = _get_val(self._e_keywords)
        dl_dir   = self.v_dir.get().strip()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            messagebox.showerror("Input Error",
                "Please enter a valid email address.")
            return False
        if not keywords:
            messagebox.showerror("Input Error", "Enter at least one keyword.")
            return False
        if not dl_dir:
            messagebox.showerror("Input Error", "Set a Download Directory.")
            return False
        try:
            import datetime as _dt
            cur_yr = _dt.date.today().year
            if not (1 <= int(self.v_max.get()) <= 100000):
                raise ValueError
            if not (1990 <= int(self.v_year.get()) <= cur_yr):
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Input Error",
                f"Max papers: 1–1,00,000\nStarting year: 1990–{cur_yr}")
            return False
        return True

    # ── Start download ────────────────────────────────────────

    def _start_download(self):
        if not self._validate_inputs():
            return
        for lbl in [self._s_fetched, self._s_journals, self._s_oa,
                    self._s_done, self._s_errors, self._s_skipped]:
            lbl.configure(text="—")
        self._clear_log()
        self._stop_event.clear()
        self._set_running(True)
        self._status("Running…")

        params = dict(
            email           = _get_val(self._e_email),
            download_dir    = self.v_dir.get().strip().replace("\\", "/"),
            keywords        = _get_val(self._e_keywords),
            max_results     = int(self.v_max.get()),
            year_from       = int(self.v_year.get()),
            selected_journals = list(self._selected_journals),
            country         = self.v_country.get(),
            log_cb          = self._append_log,
            stop_event      = self._stop_event,
        )

        threading.Thread(
            target=self._worker, kwargs=params, daemon=True
        ).start()

    def _worker(self, **kwargs):
        try:
            run_download(**kwargs)
            self._status("Completed ✓")
        except Exception as exc:
            self._append_log(f"[ERROR] {exc}", "error")
            self._status("Error occurred")
        finally:
            self._set_running(False)

    def _stop(self):
        self._stop_event.set()
        self._append_log("[INFO] Stop requested…", "warn")
        self._status("Stopping…")
        self._set_running(False)

    # ── PDF check ─────────────────────────────────────────────

    def _run_pdf_check(self):
        folder = self.v_dir.get().strip()
        if not folder:
            messagebox.showerror("Error", "Set Download Directory first.")
            return
        if not os.path.isdir(folder):
            if messagebox.askyesno("Not Found", f"Create folder?\n{folder}"):
                os.makedirs(folder, exist_ok=True)
            else:
                return
        self._append_log("─" * 55, "sep")
        self._append_log("[STEP] Starting PDF integrity check…", "step")
        self._stop_event.clear()
        self._set_running(True)
        self._status("Running PDF checker…")
        threading.Thread(target=self._worker_pdf,
                         args=(folder,), daemon=True).start()

    def _worker_pdf(self, folder):
        try:
            email = _get_val(self._e_email)
            run_pdf_integrity_check(folder, self._append_log, self._stop_event, email=email)
            self._status("PDF check complete ✓")
        except Exception as exc:
            self._append_log(f"[ERROR] {exc}", "error")
            self._status("PDF check error")
        finally:
            self._set_running(False)


if __name__ == "__main__":
    app = BiblioBlitzApp()
    app.mainloop()
