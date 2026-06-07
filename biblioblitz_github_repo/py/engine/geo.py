#!/usr/bin/env python3
"""
engine/geo.py - Geographic Helper Functions, States CSV Loader, World States Fetcher
"""

import os
import sys
import csv

from py.config import COUNTRY_ISO2
from py.utils import _http_get_json

OTHER_JOURNALS = "Other journals"

_STATES_CACHE = None


def _get_states_csv_path():
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        # Walk up from engine/ to project root where states.csv lives
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "states.csv")


_STATES_CSV_PATHS = [_get_states_csv_path()]


def _state_name(label):
    return label.split("::", 1)[1].strip() if "::" in label else label.strip()


def _journal_name(label):
    return label.split("::", 1)[1].strip() if "::" in label else label.strip()


def _clean_publisher(value):
    value = (value or "").strip()
    if not value or value.lower() in {"unknown", "none", "null", "n/a"}:
        return OTHER_JOURNALS
    return value


def _geo_terms(countries=None, states=None):
    terms = []
    for country in countries or []:
        if country and country not in terms:
            terms.append(country)
    for state in states or []:
        name = _state_name(state)
        if name and name not in terms:
            terms.append(name)
    return terms


def _title_matches_geo(title, terms):
    if not terms:
        return True
    title_l = (title or "").lower()
    return any(term.lower() in title_l for term in terms)


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
    Loads administrative divisions from states.csv, with a web fallback only
    when the local CSV does not contain the selected country.
    """
    csv_states = _load_states_from_csv().get(country_name)
    if csv_states:
        return csv_states

    iso_code = COUNTRY_ISO2.get(country_name)
    if not iso_code:
        return []

    url = "https://secure.geonames.org/childrenJSON"
    res = _http_get_json(
        url, params={"geonameId": "0", "username": "demo", "country": iso_code})

    if not res or not res.get("geonames"):
        url = "https://api.allorigins.win/raw"
        target = f"https://restcountries.com/v3.1/alpha/{iso_code}"
        res_raw = _http_get_json(url, params={"url": target})
        try:
            if res_raw and "subregion" in res_raw:
                return [res_raw["subregion"]]
        except Exception:
            pass

    if res and res.get("geonames"):
        return sorted([item["name"] for item in res["geonames"] if item.get("name")])

    defaults = {
        "India": ["Uttarakhand", "Delhi", "West Bengal", "Maharashtra",
                  "Karnataka", "Uttar Pradesh", "Tamil Nadu"],
        "United States": ["California", "Texas", "New York", "Florida",
                          "Illinois", "Pennsylvania", "Ohio", "Washington"],
        "Canada": ["Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba"],
        "United Kingdom": ["England", "Scotland", "Wales", "Northern Ireland"],
        "Australia": ["New South Wales", "Queensland", "Victoria",
                      "Western Australia", "South Australia"],
    }
    return defaults.get(country_name, ["Region Area Alpha", "Region Area Beta", "Region Area Gamma"])
