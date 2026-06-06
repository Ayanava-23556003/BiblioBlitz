# BiblioBlitz v4.1
### Global Academic Knowledge Harvester & Literature Review Suite

BiblioBlitz is a desktop application for automated academic literature retrieval, PDF harvesting, and publication trend analysis. It queries multiple open scholarly APIs simultaneously, applies geographic and journal-level filters, and downloads verified open-access PDFs to a local directory — all through a clean graphical interface.

---

## Features

### Literature Retrieval
- Queries **four independent APIs in parallel**: CrossRef, OpenAlex, PubMed, and CORE
- Fetches up to **10,000 records per API per query**, with multi-country query fan-out
- Deduplicates records across all sources before processing
- Retains full metadata (title, DOI, year, journal, authors, abstract, source) for all records, even when PDFs are unavailable

### PDF Download Pipeline
- Resolves open-access PDFs via a **three-tier fallback chain**:
  1. Unpaywall (primary — returns verified PDF URLs)
  2. Semantic Scholar OA index (secondary fallback)
  3. Direct source URLs from non-CrossRef APIs (tertiary fallback)
- Post-download integrity sweep: verifies every file starts with `%PDF` header and is non-trivially sized; permanently removes corrupted or HTML-disguised files
- Skips already-downloaded files (cache-aware)
- Exports a `download_log.csv` with title, DOI, year, journal, and download status for every processed record

### Filtering
- **Country filter**: select one or more countries; queries are geo-expanded to include the country name as a title search term
- **State/region filter**: cascading sub-national filter loaded from a local `states.csv`, with a live web fallback if the country is not found locally
- **Journal filter**: select specific publication venues from a dynamically fetched list; uses substring matching so variant journal name formats are handled correctly
- **Year filter**: restricts records to a minimum publication year
- **Max results cap**: user-defined ceiling on the number of records sent to the download pipeline

### Publication Trend Analysis (Tab 2)
- Queries CrossRef and OpenAlex for a keyword set and year range
- Renders three live matplotlib charts:
  - Scholarly output volume over time (line plot)
  - Top 3 publication venues by year (grouped bar chart)
  - Document type composition (pie chart)
- Chart rendering runs on the main UI thread to prevent freezing

### Output Modes
- **PDF + CSV**: download PDFs and write a metadata log
- **CSV only**: write metadata log without attempting PDF downloads
- **Both**: same as PDF + CSV

---

## Installation

**Requirements:** Python 3.9+

```bash
pip install customtkinter matplotlib requests
```

Place the following files in the same directory:

```
biblioblitz_project/
├── main.py
├── core_engine.py
├── utils.py
├── config.py
├── states.csv          # Administrative divisions data
├── biblioblitz.ico     # App icon (Windows taskbar)
└── biblioblitz.png     # App icon (fallback)
```

**Run:**

```bash
python main.py
```

---

## Usage

1. Enter your **search keywords** (comma, semicolon, or pipe-separated for multi-term queries)
2. Enter a **valid email address** — required by the Unpaywall and CrossRef polite pool APIs
3. Select a **download directory**
4. Optionally click **Extract Mapped Publication Portals** to fetch available journals, then filter by venue
5. Optionally select **countries** and **states** to narrow by geographic relevance in titles
6. Set a **year range** and **maximum result count**
7. Click **Download PDFs**, **Export CSV**, or **Both**

Progress is logged in real time. A `download_log.csv` is written to the download directory on completion.

---

## File Structure

| File | Role |
|---|---|
| `main.py` | GUI controller — all windows, dialogs, and event wiring |
| `core_engine.py` | API fetch logic, download pipeline, integrity sweep, trend charts |
| `utils.py` | HTTP helpers, file download, filename sanitizer, UI utilities |
| `config.py` | App constants, color palette, country list and ISO codes |
| `states.csv` | Local source for sub-national administrative divisions |

---

## API Sources

| API | Use |
|---|---|
| [CrossRef](https://api.crossref.org) | Journal article metadata, DOIs, publisher data |
| [OpenAlex](https://openalex.org) | Open metadata with OA PDF URLs |
| [PubMed / NCBI E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/) | Biomedical and life sciences literature |
| [CORE](https://core.ac.uk) | Open access full-text repository |
| [Unpaywall](https://unpaywall.org) | Verified open-access PDF resolution by DOI |
| [Semantic Scholar](https://www.semanticscholar.org/product/api) | Secondary OA PDF fallback |

All APIs are used without authentication keys (public/polite-pool access). Rate limiting is respected with small inter-request delays.

---

## Notes

- PubMed coverage is strongest for biomedical topics. For earth sciences and hydrology, CrossRef and OpenAlex will provide the majority of records.
- The proportion of downloadable PDFs depends on open-access availability of the literature. Paywalled papers have their metadata retained in the CSV log.
- For very large result sets (>5,000 records), runtime is dominated by Unpaywall API calls (~0.15s per record).

---

## License

MIT License. See `LICENSE` for details.

---

## Author

Ayanava Poddar  
Junior Research Fellow, Department of Hydrology, IIT Roorkee
