<p align="center">
  <img src="biblioblitz_logo.png" alt="BiblioBlitz Logo" width="180"/>
</p>

<h1 align="center">BiblioBlitz v4.1</h1>
<p align="center"><em>Global Academic Knowledge Harvester & Literature Review Suite</em></p>

<p align="center">
  <a href="https://doi.org/10.5281/zenodo.20573666">
    <img src="https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20573666-blue?style=flat-square&logo=zenodo" alt="DOI"/>
  </a>
  &nbsp;
  <a href="https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v4.1/BiblioBlitz_Setup_v4.1.exe">
    <img src="https://img.shields.io/badge/Download-Windows%20EXE%20v4.1-2A9D8F?style=flat-square&logo=windows" alt="Download EXE"/>
  </a>
  &nbsp;
  <img src="https://img.shields.io/badge/Python-3.9%2B-1D3557?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  &nbsp;
  <img src="https://img.shields.io/badge/Platform-Windows-457B9D?style=flat-square&logo=windows" alt="Platform"/>
  &nbsp;
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License"/>
</p>

---

BiblioBlitz is a desktop application for automated academic literature retrieval, open-access PDF harvesting, and publication trend analysis. It queries multiple scholarly APIs simultaneously, applies geographic and journal-level filters, and downloads verified PDFs to a local directory — all through a clean graphical interface built for researchers.

---

## ⬇️ Download

| Platform | Link |
|---|---|
| Windows (installer) | [**BiblioBlitz_Setup_v4.1.exe**](https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v4.1/BiblioBlitz_Setup_v4.1.exe) |
| Run from source | See [Installation](#installation) below |

---

## Features

### 📡 Multi-API Literature Retrieval
- Queries **CrossRef, OpenAlex, PubMed, and CORE** simultaneously
- Fetches up to **10,000 records per API per query** with multi-country query fan-out
- Deduplicates records across all sources before processing
- Retains full metadata (title, DOI, year, journal, authors, abstract, source) for every record

### 📄 PDF Download Pipeline
- Three-tier open-access PDF resolution:
  1. **Unpaywall** — primary, returns publisher-verified PDF URLs
  2. **Semantic Scholar** — secondary fallback by DOI
  3. **Direct source URLs** — tertiary, for OpenAlex and CORE records only
- Post-download integrity sweep: verifies every file starts with `%PDF`, removes corrupted or HTML-disguised files
- Cache-aware: skips already-downloaded files
- Exports `download_log.csv` with title, DOI, year, journal, and download status for every processed record

### 🌍 Geographic Filtering
- Select one or more **countries** — each expands into a separate geo-targeted API query
- Cascading **state/region filter** loaded from a local `states.csv`, with live web fallback

### 📋 Journal Filtering
- Fetches a live venue list from CrossRef, OpenAlex, PubMed, and CORE for your keyword set
- Select specific journals via a searchable two-panel dialog (Available ↔ Selected)
- Uses **substring matching** to handle variant journal name formats across APIs

### 📈 Live Publication Trend Analysis
- Queries CrossRef and OpenAlex for a keyword + year range
- Renders three live matplotlib charts:
  - Scholarly output volume over time (line)
  - Top 3 venues by year (grouped bar)
  - Document type composition (pie)

### 📤 Output Modes
- **PDF + CSV** — download PDFs and write metadata log
- **CSV only** — metadata log without PDF downloads
- **Both** — combined output

---

## Installation

**Requirements:** Python 3.9+

```bash
pip install customtkinter matplotlib Pillow
```

Clone or download the repository and ensure the following structure is intact:

```
BiblioBlitz/
├── main.py
├── states.csv
├── biblioblitz.ico
├── biblioblitz.png
└── py/
    ├── app.py
    ├── config.py
    ├── utils.py
    ├── dialogs.py
    ├── splash.py
    ├── tabs/
    │   ├── tab_acquisition.py
    │   ├── tab_statistics.py
    │   └── tab_slr.py
    └── engine/
        ├── geo.py
        ├── journals.py
        ├── downloader.py
        └── trends.py
```

```bash
python main.py
```

---

## Usage

1. Enter **search keywords** (comma, semicolon, or pipe-separated for multi-term)
2. Enter a **valid email** — required by Unpaywall and CrossRef polite pool
3. Select a **download directory**
4. Optionally click **Extract Mapped Publication Portals** → filter by journal venue
5. Optionally select **countries** and **states** to narrow by geographic relevance in titles
6. Set a **year range** and **maximum result count**
7. Click **Download PDFs**, **Export CSV**, or **Both**

Progress is logged in real time. A `download_log.csv` is written to the output directory on completion.

---

## File Structure

```
BiblioBlitz/
├── main.py                          # Entry point
├── build_exe.bat                    # Windows build script
├── BiblioBlitz_Setup.iss            # Inno Setup installer script
├── states.csv                       # Sub-national administrative divisions
├── biblioblitz.ico                  # App icon
├── biblioblitz.png                  # App logo
└── py/
    ├── app.py                       # Main application window
    ├── config.py                    # Constants, colors, country data
    ├── utils.py                     # HTTP helpers, filename sanitizer, UI utilities
    ├── dialogs.py                   # Reusable selector dialog widgets
    ├── splash.py                    # Splash screen
    ├── tabs/
    │   ├── tab_acquisition.py       # Literature retrieval tab
    │   ├── tab_statistics.py        # Live trend analysis tab
    │   └── tab_slr.py               # Systematic review tab
    └── engine/
        ├── geo.py                   # Geographic filter and states lookup
        ├── journals.py              # Journal fetch and filter logic
        ├── downloader.py            # PDF download pipeline and integrity sweep
        └── trends.py               # CrossRef/OpenAlex trend chart generation
```

---

## API Sources

| API | Purpose |
|---|---|
| [CrossRef](https://api.crossref.org) | Journal article metadata, DOIs, publisher data |
| [OpenAlex](https://openalex.org) | Open metadata with OA PDF URLs |
| [PubMed / NCBI](https://www.ncbi.nlm.nih.gov/home/develop/api/) | Biomedical and life sciences literature |
| [CORE](https://core.ac.uk) | Open access full-text repository |
| [Unpaywall](https://unpaywall.org) | Verified OA PDF resolution by DOI |
| [Semantic Scholar](https://www.semanticscholar.org/product/api) | Secondary OA PDF fallback |

No API keys required. All services are accessed via public or polite-pool endpoints with rate-limit-compliant delays.

---

## Citation

If you use BiblioBlitz in your research, please cite:

```
Poddar, A. & Bhattacharjee, S. (2026). BiblioBlitz: Global Academic Knowledge Harvester & Literature Review Suite (v4.1).
Zenodo. https://doi.org/10.5281/zenodo.20573666
```

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20573666-blue?style=flat-square&logo=zenodo)](https://doi.org/10.5281/zenodo.20573666)

---

## Notes

- The proportion of downloadable PDFs depends on open-access availability of the literature. Paywalled papers have metadata retained in the CSV log.
- For large result sets (>5,000 records), runtime is dominated by Unpaywall API calls (~0.15s per record).
- PubMed coverage is strongest for biomedical topics; CrossRef and OpenAlex provide the majority of records for earth and environmental sciences.

---

## License

MIT License. See [`LICENSE`](LICENSE) for details.

---

<p align="center">
  Developed by <strong>Ayanava Poddar</strong><br>
  Junior Research Fellow and PhD Scholar, Department of Hydrology, IIT Roorkee<br>
  <strong>Subhrajyoti Bhattacharjee</strong><br>
  PhD Scholar, Department of Hydrology, IIT Roorkee
</p>
