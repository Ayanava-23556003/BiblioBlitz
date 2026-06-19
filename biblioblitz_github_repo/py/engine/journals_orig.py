#!/usr/bin/env python3
"""
engine/journals.py - Journal Discovery and Venue Mapping via Public APIs
"""

import re
import time

from py.utils import _http_get_json
from py.engine.geo import OTHER_JOURNALS, _clean_publisher


def fetch_journals_for_keywords(keywords, log_cb=None):
    kw = " ".join(k.strip() for k in re.split(r"[,;|]+", keywords) if k.strip())
    journal_dict = {}
    offset, fetched, target = 0, 0, 10000

    # ── CrossRef ────────────────────────────────────────────────────────────
    while fetched < target:
        res = _http_get_json(
            "https://api.crossref.org/works",
            params={"query": kw, "filter": "type:journal-article",
                    "rows": 1000, "offset": offset,
                    "select": "container-title,publisher"})
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

    # ── OpenAlex ────────────────────────────────────────────────────────────
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

    # ── PubMed ──────────────────────────────────────────────────────────────
    res_pm = _http_get_json("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                            params={"db": "pubmed", "term": kw, "retmode": "json", "retmax": 2000})
    ids = (((res_pm or {}).get("esearchresult") or {}).get("idlist") or [])
    if ids:
        for pos in range(0, len(ids), 200):
            res_sum = _http_get_json(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
                params={"db": "pubmed", "id": ",".join(ids[pos:pos + 200]), "retmode": "json"})
            result = (res_sum or {}).get("result") or {}
            for uid in result.get("uids") or []:
                entry = result.get(uid) or {}
                journal = (entry.get("fulljournalname") or entry.get("source") or "").strip()
                if journal and journal not in journal_dict:
                    journal_dict[journal] = OTHER_JOURNALS
        if log_cb:
            log_cb(f"PubMed expanded the venue map to {len(journal_dict)} journals...", "info")

    # ── CORE ────────────────────────────────────────────────────────────────
    res_core = _http_get_json("https://api.core.ac.uk/v3/search/works",
                              params={"q": kw, "limit": 1000})
    for item in (res_core or {}).get("results") or []:
        journal = ((item.get("journals") or [{}])[0].get("title")
                   if item.get("journals") else "") or ""
        publisher = _clean_publisher(item.get("publisher"))
        if journal and journal not in journal_dict:
            journal_dict[journal.strip()] = publisher
    if res_core and log_cb:
        log_cb(f"CORE expanded the venue map to {len(journal_dict)} journals...", "info")

    sorted_journals = [{"journal": j, "publisher": p} for j, p in journal_dict.items()]
    sorted_journals.sort(key=lambda x: (x["publisher"].lower(), x["journal"].lower()))
    return sorted_journals
