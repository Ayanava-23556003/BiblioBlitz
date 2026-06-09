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
    OTHER_JOURNALS, _clean_publisher, _geo_terms,
    _title_matches_geo, _title_matches_keywords, _journal_name
)


# ── APA helpers ──────────────────────────────────────────────────────────────

def _format_authors_apa(authors):
    """Returns APA-style author string from a list of author dicts or strings."""
    if not authors:
        return "Unknown Author"
    parts = []
    for a in authors[:6]:  # APA caps inline at 6, then et al.
        if isinstance(a, dict):
            family = a.get("family") or a.get("name") or ""
            given = a.get("given") or ""
            initials = "".join(f"{n[0]}." for n in given.split() if n) if given else ""
            parts.append(f"{family}, {initials}".strip(", ") if family else "")
        else:
            parts.append(str(a))
    parts = [p for p in parts if p]
    if len(authors) > 6:
        parts.append("et al.")
    return "; ".join(parts)


def _build_apa(authors, year, title, journal, doi):
    author_str = _format_authors_apa(authors)
    year_str = str(year) if year else "n.d."
    title_str = (title or "Untitled").strip()
    journal_str = (journal or "").strip()
    doi_str = f"https://doi.org/{doi}" if doi else ""
    citation = f"{author_str} ({year_str}). {title_str}. {journal_str}."
    if doi_str:
        citation += f" {doi_str}"
    return citation.strip()


# ── Record builder ───────────────────────────────────────────────────────────

def _add_record(pool, **kwargs):
    title = (kwargs.get("title") or "").strip()
    if not title:
        return
    pool.append({
        "doi":        (kwargs.get("doi") or "").strip(),
        "pmid":       (kwargs.get("pmid") or "").strip(),
        "ss_id":      (kwargs.get("ss_id") or "").strip(),
        "title":      title,
        "year":       kwargs.get("year"),
        "journal":    kwargs.get("journal") or "Global Venue",
        "publisher":  _clean_publisher(kwargs.get("publisher")),
        "pdf_url":    kwargs.get("pdf_url") or "",
        "authors":    kwargs.get("authors") or [],
        "abstract":   kwargs.get("abstract") or "",
        "country":    kwargs.get("country") or "",
        "pub_type":   kwargs.get("pub_type") or "Journal Article",
        "is_oa":      kwargs.get("is_oa") or False,
        "_source":    kwargs.get("source") or "Open API",
    })


# ── Deduplication ────────────────────────────────────────────────────────────

def _normalize_title(title):
    return re.sub(r"[^a-z0-9]", "", (title or "").lower())


def _deduplicate(records):
    seen_doi   = {}
    seen_pmid  = {}
    seen_ss    = {}
    seen_title = {}
    deduped    = []

    for rec in records:
        doi   = rec["doi"].lower().strip()
        pmid  = rec["pmid"].strip()
        ss_id = rec["ss_id"].strip()
        nt    = _normalize_title(rec["title"])

        if doi and doi in seen_doi:
            continue
        if pmid and pmid in seen_pmid:
            continue
        if ss_id and ss_id in seen_ss:
            continue
        if nt and nt in seen_title:
            continue

        if doi:   seen_doi[doi]   = True
        if pmid:  seen_pmid[pmid] = True
        if ss_id: seen_ss[ss_id]  = True
        if nt:    seen_title[nt]  = True

        deduped.append(rec)

    return deduped


# ── PDF resolution ───────────────────────────────────────────────────────────

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


# ── PDF validation ────────────────────────────────────────────────────────────

def _is_valid_pdf(path):
    try:
        if os.path.getsize(path) < 100:
            return False
        with open(path, "rb") as fh:
            return fh.read(4) == b"%PDF"
    except Exception:
        return False


# ── Post-download integrity purge ─────────────────────────────────────────────

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
        if not _is_valid_pdf(fpath):
            try:
                os.remove(fpath)
                del_c += 1
            except Exception:
                pass
        else:
            ok_c += 1

    log_cb(
        f"[INTEGRITY COMPLETE] Verified {ok_c} intact documents. "
        f"Permanently deleted {del_c} corrupted files.", "success")
    log_cb("─" * 65, "sep")


# ── API fetchers ──────────────────────────────────────────────────────────────

def _fetch_crossref(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    fetched = 0
    while fetched < source_quota and not stop_event.is_set():
        rows = min(1000, source_quota - fetched)
        res = _http_get_json("https://api.crossref.org/works", params={
            "query": query_str,
            "filter": f"from-pub-date:{year_from},type:journal-article",
            "rows": rows, "offset": fetched,
        })
        items = ((res or {}).get("message") or {}).get("items") or []
        if not items:
            break
        for item in items:
            title    = (item.get("title") or [""])[0]
            abstract = item.get("abstract") or ""
            if not _title_matches_keywords(title, abstract, keywords):
                continue
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
            # Country from affiliation
            country = ""
            for auth in (item.get("author") or []):
                for aff in (auth.get("affiliation") or []):
                    name = aff.get("name") or ""
                    if name:
                        country = name.split(",")[-1].strip()
                        break
                if country:
                    break
            _add_record(
                records,
                doi=item.get("DOI", ""),
                title=title,
                year=yr,
                journal=(item.get("container-title") or ["Global Venue"])[0],
                publisher=item.get("publisher"),
                pdf_url=pdf_url,
                authors=item.get("author") or [],
                abstract=abstract,
                country=country,
                pub_type="Journal Article",
                is_oa=False,
                source="CrossRef"
            )
        fetched += len(items)
        if len(items) < rows:
            break
        log_cb(f"[API] CrossRef: {fetched} records fetched...", "info")
        time.sleep(0.05)
    return records


def _fetch_openalex(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    fetched = 0
    page = 1
    while fetched < source_quota and not stop_event.is_set():
        per_page = min(200, source_quota - fetched)
        res = _http_get_json("https://api.openalex.org/works", params={
            "search": query_str,
            "filter": f"from_publication_date:{year_from}-01-01,type:article",
            "per_page": per_page, "page": page
        })
        results = (res or {}).get("results") or []
        if not results:
            break
        for r in results:
            title    = r.get("title") or ""
            abstract = r.get("abstract_inverted_index") or ""
            # OpenAlex abstract comes as inverted index; flatten to string for matching
            if isinstance(abstract, dict):
                words = sorted(abstract.items(), key=lambda x: min(x[1]))
                abstract = " ".join(w for w, _ in words)
            if not _title_matches_keywords(title, abstract, keywords):
                continue
            if not _title_matches_geo(title, geo_terms_list):
                continue
            loc  = r.get("primary_location") or {}
            src  = loc.get("source") or {}
            doi  = (r.get("doi") or "").replace("https://doi.org/", "")
            # Country from institutions
            country = ""
            for auth in (r.get("authorships") or []):
                for inst in (auth.get("institutions") or []):
                    country = inst.get("country_code") or ""
                    if country:
                        break
                if country:
                    break
            raw_type = r.get("type", "").lower()
            if "article" in raw_type or "journal" in raw_type:
                pub_type = "Journal Article"
            elif "book" in raw_type:
                pub_type = "Book/Book Chapter"
            else:
                pub_type = "Report/Thesis"
            _add_record(
                records,
                doi=doi,
                title=title,
                year=r.get("publication_year"),
                journal=src.get("display_name") or "Global Venue",
                publisher=src.get("host_organization_name"),
                pdf_url=(r.get("open_access") or {}).get("oa_url") or loc.get("pdf_url") or "",
                abstract=abstract if isinstance(abstract, str) else "",
                country=country,
                pub_type=pub_type,
                is_oa=(r.get("open_access") or {}).get("is_oa") or False,
                source="OpenAlex"
            )
        fetched += len(results)
        page += 1
        if len(results) < per_page:
            break
        log_cb(f"[API] OpenAlex: {fetched} records fetched...", "info")
        time.sleep(0.05)
    return records


def _fetch_pubmed(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    phrases = [p.strip() for p in re.split(r"[,;|&]+", query_str) if p.strip()]
    title_q = " OR ".join(f'"{ph}"[Title/Abstract]' for ph in phrases)
    res_pm = _http_get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={"db": "pubmed",
                "term": f"({title_q}) AND {year_from}:3000[pdat]",
                "retmode": "json", "retmax": source_quota})
    ids = (((res_pm or {}).get("esearchresult") or {}).get("idlist") or [])
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
            if not _title_matches_keywords(title, "", keywords):
                continue
            if not _title_matches_geo(title, geo_terms_list):
                continue
            year_match = re.search(r"\d{4}", entry.get("pubdate") or "")
            _add_record(
                records,
                pmid=uid,
                title=title,
                year=int(year_match.group(0)) if year_match else year_from,
                journal=entry.get("fulljournalname") or entry.get("source") or "PubMed",
                publisher=OTHER_JOURNALS,
                pub_type="Journal Article",
                source="PubMed"
            )
        log_cb(f"[API] PubMed: {min(pos + 200, len(ids))} records processed...", "info")
        time.sleep(0.05)
    return records


def _fetch_core(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    phrases = [p.strip() for p in re.split(r"[,;|&]+", query_str) if p.strip()]
    core_q  = " OR ".join(f'("{ph}")' for ph in phrases)
    res = _http_get_json("https://api.core.ac.uk/v3/search/works",
                         params={"q": core_q, "limit": min(source_quota, 1000)})
    for item in (res or {}).get("results") or []:
        if stop_event.is_set():
            break
        title    = item.get("title") or ""
        abstract = item.get("abstract") or ""
        if not _title_matches_keywords(title, abstract, keywords):
            continue
        if not _title_matches_geo(title, geo_terms_list):
            continue
        journals = item.get("journals") or []
        _add_record(
            records,
            doi=item.get("doi") or "",
            title=title,
            year=item.get("yearPublished") or item.get("publishedYear") or year_from,
            journal=(journals[0].get("title") if journals else "") or "CORE",
            publisher=item.get("publisher"),
            pdf_url=item.get("downloadUrl") or item.get("fullTextLink") or "",
            abstract=abstract,
            pub_type="Journal Article",
            source="CORE"
        )
    if res:
        log_cb(f"[API] CORE: {len(records)} records fetched...", "info")
    return records


def _fetch_semantic_scholar(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    fetched = 0
    offset  = 0
    limit   = min(100, source_quota)
    while fetched < source_quota and not stop_event.is_set():
        res = _http_get_json(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query_str,
                "fields": "title,abstract,year,journal,authors,externalIds,openAccessPdf,publicationTypes,isOpenAccess",
                "limit": limit,
                "offset": offset,
            })
        items = (res or {}).get("data") or []
        if not items:
            break
        for item in items:
            title    = item.get("title") or ""
            abstract = item.get("abstract") or ""
            if not _title_matches_keywords(title, abstract, keywords):
                continue
            if not _title_matches_geo(title, geo_terms_list):
                continue
            yr  = item.get("year") or year_from
            doi = (item.get("externalIds") or {}).get("DOI") or ""
            ss_id = item.get("paperId") or ""
            pdf_url = (item.get("openAccessPdf") or {}).get("url") or ""
            raw_types = item.get("publicationTypes") or []
            if any("journal" in t.lower() for t in raw_types):
                pub_type = "Journal Article"
            elif any("book" in t.lower() for t in raw_types):
                pub_type = "Book/Book Chapter"
            else:
                pub_type = "Report/Thesis"
            _add_record(
                records,
                doi=doi,
                ss_id=ss_id,
                title=title,
                year=yr,
                journal=(item.get("journal") or {}).get("name") or "Semantic Scholar",
                pdf_url=pdf_url,
                authors=[{"family": a.get("name", "")} for a in (item.get("authors") or [])],
                abstract=abstract,
                pub_type=pub_type,
                is_oa=item.get("isOpenAccess") or False,
                source="SemanticScholar"
            )
        fetched += len(items)
        offset  += len(items)
        if len(items) < limit:
            break
        log_cb(f"[API] Semantic Scholar: {fetched} records fetched...", "info")
        time.sleep(0.1)
    return records


def _fetch_openaire(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    res = _http_get_json(
        "https://api.openaire.eu/search/publications",
        params={
            "keywords": query_str,
            "fromDateAccepted": f"{year_from}-01-01",
            "format": "json",
            "size": min(source_quota, 200),
            "page": 1,
        })
    results = (((res or {}).get("response") or {}).get("results") or {}).get("result") or []
    for item in results:
        if stop_event.is_set():
            break
        metadata = (item.get("metadata") or {}).get("oaf:entity", {}).get("oaf:result", {})
        title_raw = metadata.get("title") or {}
        title = (title_raw.get("$") if isinstance(title_raw, dict) else "") or ""
        if not title:
            continue
        abstract_raw = metadata.get("description") or {}
        abstract = (abstract_raw.get("$") if isinstance(abstract_raw, dict) else "") or ""
        if not _title_matches_keywords(title, abstract, keywords):
            continue
        if not _title_matches_geo(title, geo_terms_list):
            continue
        date_raw = metadata.get("dateofacceptance") or {}
        date_str = (date_raw.get("$") if isinstance(date_raw, dict) else "") or ""
        yr_match = re.search(r"\d{4}", date_str)
        yr = int(yr_match.group(0)) if yr_match else year_from
        pid_list = metadata.get("pid") or []
        doi = ""
        if isinstance(pid_list, list):
            for pid in pid_list:
                if isinstance(pid, dict) and (pid.get("@classid") or "").lower() == "doi":
                    doi = pid.get("$") or ""
                    break
        _add_record(
            records,
            doi=doi,
            title=title,
            year=yr,
            journal="OpenAIRE",
            abstract=abstract,
            pub_type="Journal Article",
            source="OpenAIRE"
        )
    if results:
        log_cb(f"[API] OpenAIRE: {len(records)} records fetched...", "info")
    return records


def _fetch_doaj(query_str, year_from, source_quota, keywords, geo_terms_list, log_cb, stop_event):
    records = []
    res = _http_get_json(
        f"https://doaj.org/api/search/articles/{urllib_quote(query_str)}",
        params={"page": 1, "pageSize": min(source_quota, 100)})
    # DOAJ returns 'results' list
    for item in (res or {}).get("results") or []:
        if stop_event.is_set():
            break
        bibjson = item.get("bibjson") or {}
        title    = bibjson.get("title") or ""
        abstract = bibjson.get("abstract") or ""
        if not _title_matches_keywords(title, abstract, keywords):
            continue
        if not _title_matches_geo(title, geo_terms_list):
            continue
        yr = int(bibjson.get("year") or year_from)
        doi = ""
        for id_obj in (bibjson.get("identifier") or []):
            if (id_obj.get("type") or "").lower() == "doi":
                doi = id_obj.get("id") or ""
                break
        journal_info = bibjson.get("journal") or {}
        pdf_url = ""
        for link in (bibjson.get("link") or []):
            if (link.get("type") or "").lower() in {"fulltext", "pdf"}:
                pdf_url = link.get("url") or ""
                break
        authors_raw = bibjson.get("author") or []
        authors = [{"family": a.get("name", "")} for a in authors_raw]
        _add_record(
            records,
            doi=doi,
            title=title,
            year=yr,
            journal=journal_info.get("title") or "DOAJ",
            publisher=journal_info.get("publisher") or "",
            pdf_url=pdf_url,
            authors=authors,
            abstract=abstract,
            pub_type="Journal Article",
            is_oa=True,
            source="DOAJ"
        )
    if res:
        log_cb(f"[API] DOAJ: {len(records)} records fetched...", "info")
    return records


def _urllib_quote(s):
    import urllib.parse
    return urllib.parse.quote(str(s))

# alias used inside _fetch_doaj
urllib_quote = _urllib_quote


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_download(
    email, download_dir, keywords, max_results, year_from,
    selected_journals, countries, download_mode, log_cb, stop_event
):
    os.makedirs(download_dir, exist_ok=True)
    geo_terms_list       = _geo_terms(countries)
    selected_journal_names = {_journal_name(j).lower() for j in selected_journals or []}

    log_cb(f"[INFO] Keywords      : {keywords}", "info")
    log_cb(f"[INFO] Operator      : {'AND (&)' if '&' in keywords else 'OR (|/,)'}", "info")
    log_cb(f"[INFO] Search fields : Title + Abstract + Keywords", "info")
    if countries:
        log_cb(f"[INFO] Country Filter: {', '.join(countries)}", "info")
    if selected_journal_names:
        log_cb(f"[INFO] Journal Filter: {len(selected_journal_names)} selected venues", "info")
    log_cb(f"[INFO] Target Path   : {download_dir}", "info")
    log_cb("─" * 65, "sep")

    source_quota = max(1, min(int(max_results), 100000))
    # Use full keyword string as query; APIs handle it
    query_str = " ".join(
        p.strip() for p in re.split(r"[,;|&]+", keywords) if p.strip()
    )

    all_items = []

    fetchers = [
        ("CrossRef",         _fetch_crossref),
        ("OpenAlex",         _fetch_openalex),
        ("PubMed",           _fetch_pubmed),
        ("CORE",             _fetch_core),
        ("SemanticScholar",  _fetch_semantic_scholar),
        ("OpenAIRE",         _fetch_openaire),
        ("DOAJ",             _fetch_doaj),
    ]

    for name, fn in fetchers:
        if stop_event.is_set():
            break
        log_cb(f"[API] Querying {name}...", "step")
        try:
            recs = fn(query_str, year_from, source_quota,
                      keywords, geo_terms_list, log_cb, stop_event)
            all_items.extend(recs)
            log_cb(f"[API] {name}: {len(recs)} raw records retrieved.", "info")
        except Exception as e:
            log_cb(f"[WARN] {name} query failed: {e}", "warn")

    log_cb("─" * 65, "sep")
    log_cb(f"[DEDUP] Total before dedup: {len(all_items)}", "info")

    # ── Journal filter ───────────────────────────────────────────────────────
    if selected_journal_names:
        all_items = [
            r for r in all_items
            if any(sel in r["journal"].lower() or r["journal"].lower() in sel
                   for sel in selected_journal_names)
        ]
        log_cb(f"[FILTER] After journal filter: {len(all_items)}", "info")

    # ── Deduplicate ──────────────────────────────────────────────────────────
    deduped = _deduplicate(all_items)
    deduped = deduped[:max_results]
    log_cb(f"[DEDUP] After dedup (capped at {max_results}): {len(deduped)}", "success")
    log_cb("─" * 65, "sep")

    # ── Build CSV rows ────────────────────────────────────────────────────────
    csv_rows = []
    fieldnames = [
        "Authors", "Year", "Title", "Journal", "DOI",
        "APA Citation", "Bibliography (APA)",
        "Open Access/Metadata Only", "Download Status",
        "Source API", "Country", "Publication Type"
    ]

    if download_mode == "csv":
        log_cb("[PIPELINE] Metadata-only mode. Building CSV index...", "step")
        for p in deduped:
            if stop_event.is_set():
                break
            apa = _build_apa(p["authors"], p["year"], p["title"], p["journal"], p["doi"])
            csv_rows.append({
                "Authors":                _format_authors_apa(p["authors"]),
                "Year":                   p["year"] or "",
                "Title":                  p["title"],
                "Journal":                p["journal"],
                "DOI":                    p["doi"],
                "APA Citation":           apa,
                "Bibliography (APA)":     apa,
                "Open Access/Metadata Only": "OA" if p["is_oa"] else "Metadata Only",
                "Download Status":        "Metadata Only",
                "Source API":             p["_source"],
                "Country":                p["country"],
                "Publication Type":       p["pub_type"],
            })

    else:  # pdf mode
        log_cb(f"[PIPELINE] PDF acquisition over {len(deduped)} targets...", "step")
        for i, p in enumerate(deduped, 1):
            if stop_event.is_set():
                break
            short_t  = p["title"][:50]
            fname    = _safe_filename(p["title"], p["doi"], p["year"], p["authors"], p["journal"])
            fpath    = os.path.join(download_dir, fname)
            apa      = _build_apa(p["authors"], p["year"], p["title"], p["journal"], p["doi"])
            oa_flag  = "OA" if p["is_oa"] else "Metadata Only"

            if os.path.exists(fpath) and _is_valid_pdf(fpath):
                log_cb(f"[SKIP] Already exists: {short_t}...", "warn")
                status = "already_exists"
            else:
                url_target = ""
                if p["doi"]:
                    url_target = _resolve_unpaywall_pdf(p["doi"], email)
                if not url_target and p["doi"]:
                    url_target = _resolve_semantic_scholar_pdf(p["doi"])
                if not url_target and p["pdf_url"] and "http" in p["pdf_url"]:
                    url_target = p["pdf_url"]

                if url_target:
                    ok = _download_file(url_target, fpath, email)
                    if ok and not _is_valid_pdf(fpath):
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
                        ok = False
                    if ok:
                        status = "downloaded"
                        log_cb(f"[OK] Downloaded [{p['_source']}]: {short_t}...", "success")
                    else:
                        status = "pdf_unavailable"
                        log_cb(f"[INFO] PDF unavailable; metadata retained: {short_t}...", "warn")
                else:
                    status = "no_url"
                    log_cb(f"[INFO] No OA URL found: {short_t}...", "warn")

            csv_rows.append({
                "Authors":                _format_authors_apa(p["authors"]),
                "Year":                   p["year"] or "",
                "Title":                  p["title"],
                "Journal":                p["journal"],
                "DOI":                    p["doi"],
                "APA Citation":           apa,
                "Bibliography (APA)":     apa,
                "Open Access/Metadata Only": oa_flag,
                "Download Status":        status,
                "Source API":             p["_source"],
                "Country":                p["country"],
                "Publication Type":       p["pub_type"],
            })
            time.sleep(0.15)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    if csv_rows:
        csv_path = os.path.join(download_dir, "biblioblitz_results.csv")
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=fieldnames)
                w.writeheader()
                w.writerows(csv_rows)
            log_cb(f"[CSV] Saved {len(csv_rows)} records → biblioblitz_results.csv", "success")
        except Exception as e:
            log_cb(f"[ERROR] CSV write failed: {e}", "error")

    if download_mode == "pdf":
        run_post_download_integrity_purge(download_dir, log_cb)

    log_cb("[DONE] Processing thread execution completed.", "done")

    # Return records for stats + table display
    return csv_rows
