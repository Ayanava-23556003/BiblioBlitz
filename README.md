# BiblioBlitz v3.2
### Global Open-Access Academic Paper Downloader

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20469653.svg)](https://doi.org/10.5281/zenodo.20469653)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)

---

## Quick Start Guide

No installation required! Just download and run:

* **Step 1:** Download **[BiblioBlitz_Setup.exe](https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v3.2.0/BiblioBlitz_Setup.exe)**
* **Step 2:** Double-click to launch — no Python, no R, no setup needed
* **Step 3:** Enter your email, keywords, select journals, and click **Start Download**

---

## What's New

### v3.2
| Feature | Details |
|---|---|
| **Bug fixes** | Fixed NoneType crash on missing journal names |
| **OpenAlex filter** | Corrected country-code filter for author affiliation |
| **Taskbar icon** | Proper `.ico` support for Windows title bar and taskbar |
| **Privacy notice** | Clear disclosure of API data usage |

### v3.1 → v3.2 (from PaperFinder v2)
| Feature | v2 (PaperFinder) | v3+ (BiblioBlitz) |
|---|---|---|
| App name | PaperFinder | **BiblioBlitz** |
| Backend | R + PowerShell | **Pure Python** (no R needed) |
| System requirement | Windows 64-bit | **Any OS, any arch** |
| Max papers | 10,000 | **1,00,000** |
| Journal filter | Hardcoded Q1 list | **Live fetch — all journals worldwide** |
| Journal selection | None | **Searchable multi-select dialog** |
| Search sources | CrossRef only | **6 APIs** (CrossRef, OpenAlex, Semantic Scholar, PubMed, CORE, Unpaywall) |
| Region filter | None | **80+ countries or Global** |
| Input placeholders | Hard-coded defaults | **Smart placeholders** (auto-clear on type) |
| Logo | File path dependent | **Always visible** (bundled in EXE) |
| Close confirmation | None | **Exit prompt** (warns if download running) |

---

## Requirements

- **Python 3.9+** — only needed to **build** the EXE on your machine
- End users need **nothing** — just the EXE file
- Internet connection required at runtime

### To build the standalone EXE (Windows)
```
double-click  build_exe.bat
```
The output `dist\BiblioBlitz.exe` runs on **any Windows 10/11 PC** (32-bit or 64-bit).

---

## How It Works

BiblioBlitz runs a 7-stage pipeline:

1. **Fetch Journals** — queries CrossRef & OpenAlex with your keywords to build a live journal list
2. **Select Journals** — searchable multi-select dialog; leave empty to search all journals
3. **Multi-source Search** — queries 5 APIs simultaneously:
   - CrossRef (150M+ works)
   - OpenAlex (250M+ works)
   - Semantic Scholar (200M+ papers)
   - PubMed / NCBI (35M+ records)
   - CORE (200M+ open-access documents)
4. **Deduplication** — merges all results and removes duplicates by DOI
5. **Journal + Keyword Filter** — retains only papers matching your selected journals and keywords
6. **Unpaywall Check** — resolves open-access PDF links for papers missing a direct URL
7. **PDF Download** — downloads PDFs and saves a `download_log.csv` summary

---

## Search Sources

| Source | Coverage | Contribution |
|---|---|---|
| **CrossRef** | 150M+ works | Primary journal article metadata |
| **OpenAlex** | 250M+ works | Modern open index with OA signals |
| **Semantic Scholar** | 200M+ papers | AI-enriched metadata, interdisciplinary |
| **PubMed / NCBI** | 35M+ records | Biomedical and environmental health |
| **CORE** | 200M+ OA docs | Direct open-access PDF links |
| **Unpaywall** | 50M+ OA links | Best-available PDF URL resolution by DOI |

All sources are **free, official, and legal APIs** — no scraping, no Terms of Service violations.

---

## Region / Country Filter

BiblioBlitz can filter papers by **author affiliation country**, including:
India, China, United States, United Kingdom, Germany, France, Australia, Brazil, and 75+ more.

Select **"Global (All Countries)"** to search without any geographic restriction.

---

## Tips

- Enter keywords first, then click **"Fetch Journals"** to load the journal list
- Select specific journals from the dialog, or leave unselected to use all journals
- Use broad keywords (e.g. `soil erosion, runoff`) for more results
- Max **1,00,000 papers** supported — large runs may take several hours
- Use **Run PDF Integrity Check** after downloading to quarantine corrupt files
- The `download_log.csv` in your download folder lists every paper with title, DOI, journal, year, source, country filter, and download status

---

## Privacy

BiblioBlitz is designed with user privacy in mind.

- Your **email address** is sent only to CrossRef and Unpaywall as required by their fair-use policies. It is **not stored** by BiblioBlitz anywhere.
- Your **keywords, country, and journal selections** are sent to the search APIs to retrieve results. They are not stored or logged.
- **No data is ever sent to the BiblioBlitz developers** or any third party beyond the APIs listed above.
- **No usage analytics, telemetry, or tracking** of any kind is collected.
- All processing happens **locally on your machine**.

---

## Citation

If you use BiblioBlitz in your research, please cite:

> Poddar, A., & Bhattacharjee, S. (2026). BiblioBlitz v3.2: A Multi-Source Global Open-Access Academic Paper Downloader with Country Filtering and Dynamic Journal Selection (v3.2.0). Zenodo. https://doi.org/10.5281/zenodo.20469653

**BibTeX:**
```bibtex
@software{biblioblitz2026,
  author    = {Poddar, Ayanava and Bhattacharjee, Subhrajyoti},
  title     = {BiblioBlitz v3.2: A Multi-Source Global Open-Access Academic Paper Downloader with Country Filtering and Dynamic Journal Selection (v3.2.0)},
  year      = {2026},
  publisher = {Zenodo},
  version   = {3.2},
  doi       = {10.5281/zenodo.20469653},
  url       = {https://doi.org/10.5281/zenodo.20469653}
}
```

```md
## Contributors

| Name | Contribution |
|---|---|
| **Ayanava Poddar** | Software design, implementation, integration, packaging, and maintenance |
| **Subhrajyoti Bhattacharjee** | Initial conceptual input and project discussions |
```
---

## License

MIT License — free to use, modify, and distribute with attribution.

---

## Acknowledgements

BiblioBlitz uses the following free and open academic APIs:
[CrossRef](https://www.crossref.org) · [OpenAlex](https://openalex.org) · [Semantic Scholar](https://www.semanticscholar.org) · [PubMed/NCBI](https://pubmed.ncbi.nlm.nih.gov) · [CORE](https://core.ac.uk) · [Unpaywall](https://unpaywall.org)
