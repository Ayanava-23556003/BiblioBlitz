# BiblioBlitz v3.0
### Q1 Open-Access Academic Paper Downloader

---

## Quick Start

[(https://zenodo.org/badge/DOI/10.5281/zenodo.20466893.svg)](https://doi.org/10.5281/zenodo.20466893)

No installation required! Just download the standalone executable and run it immediately:

* **Step 1:** Download **[BiblioBlitz.exe](https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v3.0.0/BiblioBlitz.exe)**.
* **Step 2:** Double-click the file to launch the graphical interface (no Python setup needed).

---

## What's New in v3

| Feature | v2 (PaperFinder) | v3 (BiblioBlitz) |
|---|---|---|
| App name | PaperFinder | **BiblioBlitz** |
| Backend | R + PowerShell | **Pure Python** (no R needed) |
| System requirement | Windows 64-bit | **Any OS, any arch** |
| Max papers | 10,000 | **1,00,000** |
| Journal filter | All journals | **Q1 only** (Nature, Science, EGU, AGU, Elsevier…) |
| Search sources | CrossRef only | **5 APIs** (CrossRef, OpenAlex, Semantic Scholar, PubMed, CORE) |
| Input placeholders | Hard-coded defaults | **Smart placeholders** (auto-clear on type) |
| Logo | File path dependent | **Always visible** (rendered in-app) |
| Close confirmation | None | **Exit prompt** (warns if download is running) |

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

BiblioBlitz runs a 6-stage pipeline:

1. **Multi-source Search** — Queries up to 5 APIs simultaneously: CrossRef, OpenAlex, Semantic Scholar, PubMed/NCBI, and CORE
2. **Deduplication** — Merges all results and removes duplicates by DOI
3. **Q1 Filter** — Retains only papers from the 80+ whitelisted Q1 journal titles
4. **Keyword Filter** — Retains only papers where the title matches your keywords
5. **Unpaywall Check** — Resolves open-access PDF links for papers missing a direct URL
6. **PDF Download** — Downloads PDFs and saves a `download_log.csv` summary

---

## Search Sources

| Source | Coverage | Contribution |
|---|---|---|
| **CrossRef** | 150M+ works | Primary journal article metadata |
| **OpenAlex** | 250M+ works | Modern open index with OA signals |
| **Semantic Scholar** | 200M+ papers | AI-enriched metadata, interdisciplinary |
| **PubMed / NCBI** | 35M+ records | Biomedical and environmental health |
| **CORE** | 200M+ OA docs | Direct open-access PDF links |
| **Unpaywall** | 50M+ OA links | Best-available PDF URL by DOI |

All sources are **free and official APIs** — no scraping, no ToS violations.

---

## Tips

- Use broad keywords (e.g. `hydrology, streamflow`) for more results
- Enable all 5 sources for maximum coverage
- Max 1,00,000 papers supported (large runs may take hours)
- Use **Run PDF Integrity Check** after downloading to quarantine corrupt files
- The `download_log.csv` in your download folder lists every paper with title, DOI, journal, year, source, and download status

---

## Citation

If you use BiblioBlitz in your research, please cite:

> Patra, A. (2026). *BiblioBlitz v3.0 — Q1 Open-Access Academic Paper Downloader*. Zenodo. https://doi.org/10.5281/zenodo.20466893

**BibTeX:**
```bibtex
@software{biblioblitz2026,
  author    = {Patra, Ayanava},
  title     = {BiblioBlitz v3.0 — Q1 Open-Access Academic Paper Downloader},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20466893},
  url       = {https://doi.org/10.5281/zenodo.20466893}
}
```

---

## License

MIT License — free to use, modify, and distribute with attribution.
