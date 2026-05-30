# BiblioBlitz v3.0
### Q1 Open-Access Academic Paper Downloader

---

## What's New in v3

| Feature | v2 (PaperFinder) | v3 (BiblioBlitz) |
|---|---|---|
| App name | PaperFinder | **BiblioBlitz** |
| Backend | R + PowerShell | **Pure Python** (no R needed) |
| System requirement | Windows 64-bit | **Any OS, any arch** |
| Max papers | 10,000 | **1,00,000** |
| Journal filter | All journals | **Q1 only** (Nature, Science, EGU, AGU, Elsevier…) |
| Input placeholders | Hard-coded defaults | **Smart placeholders** (auto-clear on type) |
| Logo | File path dependent | **Always visible** (rendered in-app) |

---

## Requirements

- **Python 3.9+** (only needed to build the EXE; end users need nothing)
- Internet connection

### To build the standalone EXE (Windows)
```
double-click  build_exe.bat
```
The output `dist\BiblioBlitz.exe` runs on **any Windows 10/11 PC** (32-bit or 64-bit) — no R, no Python, no extra setup.

---

## Q1 Journal Coverage

BiblioBlitz fetches papers **only from Q1-ranked journals**, including:

- **Nature** family (Nature, Nature Climate Change, Nature Geoscience, Nature Water…)
- **Science / AAAS** (Science, Science Advances)
- **EGU / Copernicus** (HESS, NHESS, The Cryosphere, ACP, Biogeosciences…)
- **AGU / Wiley** (GRL, JGR series, Water Resources Research…)
- **Elsevier** (Journal of Hydrology, Advances in Water Resources, STOTEN, Catena, Geoderma, Geomorphology…)
- **AMS** (Journal of Climate, Journal of Hydrometeorology…)
- **Springer** (Climatic Change, Climate Dynamics, Hydrogeology Journal…)
- **MDPI Q1** (Remote Sensing, Water, Atmosphere…)

---

## How It Works

1. Searches **CrossRef API** with your keywords
2. Filters results to **Q1 journals** and title keyword match
3. Checks **Unpaywall** for open-access PDF links
4. Downloads PDFs directly — no R, no PowerShell
5. Saves a `download_log.csv` summary

---

## Tips

- Use broad keywords (e.g. `hydrology, streamflow`) for more results
- Max 1,00,000 papers supported (large runs may take hours)
- Use **Run PDF Integrity Check** after downloading to quarantine corrupt files
