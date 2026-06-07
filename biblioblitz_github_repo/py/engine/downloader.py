#!/usr/bin/env python3
"""
engine/downloader.py - PDF Resolution, Record Building, Download Pipeline, Integrity Purge
"""

import os
import re
import csv
import time

from py.utils import _http_get_json, _download_file, _safe_filename
from py.engine.geo import (
    OTHER_JOURNALS, _clean_publisher, _geo_terms, _title_matches_geo,
    _state_name, _journal_name
)


def _query_variants(keywords, geo_terms):
    base = " ".join(k.strip() for k in re.split(r"[,;|]+", keywords) if k.strip())
    if not geo_terms:
        return [base]
    return [f"{base} {term}" for term in geo_terms]


def _resolve_unpaywall_pdf(doi, email):
    if not doi:
        return ""
    res = _http_get_json(f"https://api.unpaywall.org/v2/{doi}", params={"email": email})
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
        "doi":       (kwargs.get("doi") or "").strip(),
        "title":     title,
        "year":      kwargs.get("year"),
        "journal":   kwargs.get("journal") or "Global Venue",
        "publisher": _clean_publisher(kwargs.get("publisher")),
        "pdf_url":   kwargs.get("pdf_url") or "",
        "authors":   kwargs.get("authors") or [],
        "abstract":  kwargs.get("abstract") or "",
        "_source":   kwargs.get("source") or "Open API",
    })


def run_post_download_integrity_purge(download_dir, log_cb):
    if not os.path.exists(download_dir):
        return
    existing_pdfs = [f for f in os.listdir(download_dir) if f.lower().endswith(".pdf")]
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
        f"[INTEGRITY COMPLETE] Verified {ok_c} intact documents. "
        f"Permanently deleted {del_c} unopenable files.", "success")
    log_cb("─" * 65, "sep")


def run_download(
    email, download_dir, keywords, max_results, year_from,
    selected_journals, countries, download_mode, log_cb, stop_event,
    states=None, basins=None
):
    os.makedirs(download_dir, exist_ok=True)
    geo_terms_list = _geo_terms(countries, states)
    query_list = _query_variants(keywords, geo_terms_list)
    selected_journal_names = {_journal_name(j).lower() for j in selected_journals or []}

    log_cb(f"[INFO] Keywords   : {keywords}", "info")
    if countries:
        log_cb(f"[INFO] Country Title Search Active: {', '.join(countries)}", "info")
    if states:
        log_cb(f"[INFO] State Title Search Active: {', '.join(_state_name(s) for s in states)}", "info")
    if selected_journal_names:
        log_cb(f"[INFO] Journal Filter Active: {len(selected_journal_names)} selected venues", "info")
    log_cb(f"[INFO] Target Path: {download_dir}", "info")
    log_cb("─" * 65, "sep")

    all_items = []
    source_quota = max(1, min(int(max_results), 100000))

    for query_str in query_list:
        if stop_event.is_set():
            break

        # ── CrossRef ────────────────────────────────────────────────────────
        log_cb(f"[API] CrossRef query: {query_str}", "step")
        crossref_fetched = 0
        while crossref_fetched < source_quota and not stop_event.is_set():
            rows = min(1000, source_quota - crossref_fetched)
            res = _http_get_json("https://api.crossref.org/works", params={
                "query.title": query_str,
                "filter": f"from-pub-date:{year_from},type:journal-article",
                "rows": rows, "offset": crossref_fetched, "mailto": email
            })
            items = ((res or {}).get("message") or {}).get("items") or []
            if not items:
                break
            for item in items:
                title = (item.get("title") or [""])[0]
                if not _title_matches_geo(title, geo_terms_list):
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

        # ── OpenAlex ────────────────────────────────────────────────────────
        log_cb(f"[API] OpenAlex query: {query_str}", "step")
        openalex_fetched = 0
        page = 1
        while openalex_fetched < source_quota and not stop_event.is_set():
            per_page = min(200, source_quota - openalex_fetched)
            res_oa = _http_get_json("https://api.openalex.org/works", params={
                "search": query_str,
                "filter": f"from_publication_date:{year_from}-01-01,type:article",
                "per_page": per_page, "page": page
            })
            results = (res_oa or {}).get("results") or []
            if not results:
                break
            for r in results:
                title = r.get("title") or ""
                if not _title_matches_geo(title, geo_terms_list):
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

        # ── PubMed ──────────────────────────────────────────────────────────
        log_cb(f"[API] PubMed query: {query_str}", "step")
        res_pm = _http_get_json(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": f"{query_str} {year_from}:3000[pdat]",
                    "retmode": "json", "retmax": source_quota})
        ids = (((res_pm or {}).get("esearchresult") or {}).get("idlist") or [])
        if ids:
            for pos in range(0, len(ids), 200):
                if stop_event.is_set():
                    break
                chunk = ids[pos:pos + 200]
                res_sum = _http_get_json(
                    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                    params={"db": "pubmed", "id": ",".join(chunk), "retmode": "json"})
                result = (res_sum or {}).get("result") or {}
                for uid in result.get("uids") or []:
                    entry = result.get(uid) or {}
                    title = entry.get("title") or ""
                    if not _title_matches_geo(title, geo_terms_list):
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

        # ── CORE ────────────────────────────────────────────────────────────
        log_cb(f"[API] CORE query: {query_str}", "step")
        res_core = _http_get_json("https://api.core.ac.uk/v3/search/works",
                                  params={"q": query_str, "limit": min(source_quota, 1000)})
        for item in (res_core or {}).get("results") or []:
            title = item.get("title") or ""
            if not _title_matches_geo(title, geo_terms_list):
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

    # ── Dedup + journal filter ───────────────────────────────────────────────
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

    # ── Download / CSV write ─────────────────────────────────────────────────
    log_rows = []
    if download_mode == "csv":
        log_cb("[PIPELINE] Building index sheets metadata database...", "step")
        for p in deduped:
            log_rows.append({
                "file": "CSV Mode Only", "title": p["title"], "year": p["year"],
                "journal": p["journal"], "doi": p["doi"],
                "status": f"CSV Mode Enabled ({p['_source']})"
            })
    else:
        log_cb(f"[PIPELINE] Running data acquisition stream over {len(deduped)} targets...", "step")
        for i, p in enumerate(deduped, 1):
            if stop_event.is_set():
                break
            fname = _safe_filename(p["title"], p["doi"], p["year"], p["authors"], p["journal"])
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
                    log_cb(f"[INFO] PDF unavailable; metadata retained: {short_t}...", "warn")

            log_rows.append({
                "file": fname, "title": p["title"], "year": p["year"],
                "journal": p["journal"], "doi": p["doi"], "status": status
            })
            time.sleep(0.15)

    if log_rows:
        try:
            with open(os.path.join(download_dir, "download_log.csv"), "w",
                      newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(
                    fh, fieldnames=["file", "title", "year", "journal", "doi", "status"])
                w.writeheader()
                w.writerows(log_rows)
        except Exception:
            pass

    if download_mode != "csv":
        run_post_download_integrity_purge(download_dir, log_cb)

    log_cb("[DONE] Processing thread execution completed.", "done")
