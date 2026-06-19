#!/usr/bin/env python3
"""
engine/geo.py - Geographic Helper Functions
"""

import re

from py.config import COUNTRY_ISO2
from py.utils import _http_get_json

OTHER_JOURNALS = "Other journals"


def _journal_name(label):
    return label.split("::", 1)[1].strip() if "::" in label else label.strip()


def _clean_publisher(value):
    value = (value or "").strip()
    if not value or value.lower() in {"unknown", "none", "null", "n/a"}:
        return OTHER_JOURNALS
    return value


def _geo_terms(countries=None):
    terms = []
    for country in countries or []:
        if country and country not in terms:
            terms.append(country)
    return terms


def _title_matches_geo(title, terms):
    if not terms:
        return True
    title_l = (title or "").lower()
    return any(term.lower() in title_l for term in terms)


def _title_matches_keywords(title, abstract, keywords_str, operator="OR"):
    """
    Keyword matching against title + abstract combined.

    Phrases are separated by '|' (OR) or '&' (AND):
        '|' → at least ONE phrase must match (OR logic)
        '&' → ALL phrases must match (AND logic)

    A phrase matches when every word in it appears in the combined
    title+abstract text (in any order).
    """
    if not keywords_str or not keywords_str.strip():
        return True

    combined = ((title or "") + " " + (abstract or "")).lower()

    # Detect operator from the raw string
    if "&" in keywords_str:
        phrases = [p.strip().lower() for p in keywords_str.split("&") if p.strip()]
        use_and = True
    else:
        phrases = [p.strip().lower() for p in re.split(r"[,;|]+", keywords_str) if p.strip()]
        use_and = False

    if not phrases:
        return True

    def _phrase_matches(phrase):
        words = [w for w in phrase.split() if w]
        return bool(words) and all(w in combined for w in words)

    if use_and:
        return all(_phrase_matches(ph) for ph in phrases)
    else:
        return any(_phrase_matches(ph) for ph in phrases)
