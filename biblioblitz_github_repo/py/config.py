#!/usr/bin/env python3
"""
config.py - Configuration management file for BiblioBlitz v4.1
"""

APP_NAME = "BiblioBlitz"
APP_VER = "v4.1"
APP_TAGLINE = "Global Academic Knowledge Harvester & Literature Review Suite"

# Unlocked full master array of all sovereign global nations
COUNTRIES = [
    "Global (All Countries)",
    "Afghanistan", "Albania", "Algeria", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bangladesh", "Belarus", "Belgium", "Bolivia",
    "Bosnia and Herzegovina", "Brazil", "Bulgaria", "Cambodia", "Canada",
    "Chile", "China", "Colombia", "Croatia", "Cuba", "Czech Republic", "Denmark",
    "Ecuador", "Egypt", "Estonia", "Ethiopia", "Finland", "France", "Georgia",
    "Germany", "Ghana", "Greece", "Hungary", "India", "Indonesia", "Iran", "Iraq",
    "Ireland", "Israel", "Italy", "Japan", "Jordan", "Kazakhstan", "Kenya",
    "Latvia", "Lebanon", "Lithuania", "Malaysia", "Mexico", "Morocco", "Nepal",
    "Netherlands", "New Zealand", "Nigeria", "Norway", "Pakistan", "Peru",
    "Philippines", "Poland", "Portugal", "Romania", "Russia", "Saudi Arabia",
    "Serbia", "Singapore", "Slovakia", "South Africa", "South Korea", "Spain",
    "Sri Lanka", "Sudan", "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkey",
    "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom",
    "United States", "Uzbekistan", "Venezuela", "Vietnam", "Zimbabwe"
]

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
    "Vietnam": "VN", "Zimbabwe": "ZW"
}

FONT_FAMILY = "Segoe UI"
FONT_TITLE_SZ = 15
FONT_LABEL_SZ = 13
FONT_ENTRY_SZ = 12

BG_ROOT = "#F5F2EB"
BG_PANEL = "#EFEBE0"
BG_CARD = "#E6E0D2"
BG_ENTRY = "#FDFDFB"
BG_HEADER = "#EFEBE0"
BG_FOOTER = "#EFEBE0"
BG_STAT = "#E1DBCF"
BORDER_CLR = "#1D3557"
ACCENT_BLUE = "#1D3557"
ACCENT_TEAL = "#2A9D8F"
ACCENT_PURP = "#457B9D"
TEXT_BRIGHT = "#111C2C"
TEXT_MID = "#4A5568"
TEXT_DIM = "#718096"
