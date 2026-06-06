# BiblioBlitz v4.1

<p align="center">
  <img src="biblioblitz.png" alt="BiblioBlitz Logo" width="300">
</p>

<h3 align="center">Global Academic Knowledge Harvester & Literature Review Suite</h3>

<p align="center">
  <a href="https://doi.org/10.5281/zenodo.20469653">
    <img src="https://zenodo.org/badge/DOI/10.5281/zenodo.20469653.svg" alt="DOI">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.9%2B-green.svg" alt="Python">
  </a>
</p>

<p align="center">
  <b>DOI:</b> <a href="https://doi.org/10.5281/zenodo.20469653">10.5281/zenodo.20469653</a>
  <br>
  <b>Windows Installer:</b>
  <a href="https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v4.1.0/BiblioBlitz_Setup_v4.1.exe">
    Download BiblioBlitz v4.1
  </a>
</p>

---

## Overview

BiblioBlitz is a desktop application for automated academic literature retrieval, PDF harvesting, and publication trend analysis. It queries multiple open scholarly APIs simultaneously, applies geographic and journal-level filters, and downloads verified open-access PDFs to a local directory through a clean graphical interface.

---

## Features

### Literature Retrieval

* Queries **four independent APIs simultaneously**:

  * CrossRef
  * OpenAlex
  * PubMed
  * CORE
* Fetches up to **10,000 records per API per query**
* Supports multi-country query expansion
* Deduplicates records across all sources
* Retains complete metadata:

  * Title
  * DOI
  * Publication Year
  * Journal
  * Authors
  * Abstract
  * Source API

### PDF Download Pipeline

BiblioBlitz employs a three-tier PDF resolution workflow:

1. **Unpaywall**
2. **Semantic Scholar Open Access Index**
3. **Direct repository/source URLs**

Additional safeguards:

* Automatic PDF integrity validation
* Verifies `%PDF` file headers
* Removes corrupted or HTML-disguised downloads
* Cache-aware duplicate prevention
* Generates `download_log.csv` containing:

  * Title
  * DOI
  * Year
  * Journal
  * Download Status

### Advanced Filtering

#### Geographic Filters

* Multi-country selection
* State/Province filtering
* Cascading administrative divisions
* Local `states.csv` database
* Live fallback retrieval when regions are unavailable locally

#### Journal Filters

* Dynamic venue extraction
* Publisher-grouped journal selection
* Substring-based journal matching
* Supports variant journal naming conventions

#### Additional Filters

* Publication year threshold
* Maximum record limit
* Keyword expansion

---

## Publication Trend Analysis

The Statistics module generates live analytical visualizations.

### Available Charts

#### Scholarly Output Velocity

* Publication volume by year
* Line chart visualization

#### Publication Venue Analysis

* Top three publication venues
* Grouped annual bar charts

#### Dataset Composition

* Publication type distribution
* Pie chart visualization

Rendering is performed safely on the UI thread to prevent interface instability.

---

## Output Modes

### PDF Mode

Downloads verified PDFs only.

### CSV Mode

Exports metadata without attempting downloads.

### Combined Mode

Downloads PDFs and exports metadata simultaneously.

---

## Installation

### Download Precompiled Release (Recommended)

Download the latest Windows installer:

**BiblioBlitz v4.1**

https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v4.1.0/BiblioBlitz_Setup_v4.1.exe

No Python installation is required for end users.

---

## Installation from Source

### Requirements

* Python 3.9+
* Internet Connection

Install dependencies:

```bash
pip install customtkinter matplotlib requests
```

### Project Structure

```text
biblioblitz_project/
├── main.py
├── core_engine.py
├── utils.py
├── config.py
├── states.csv
├── biblioblitz.ico
├── biblioblitz.png
├── README.md
├── LICENSE
└── requirements.txt
```

### Run

```bash
python main.py
```

---

## Usage

1. Enter search keywords
2. Enter a valid email address
3. Select a download directory
4. Extract publication portals (optional)
5. Select journals (optional)
6. Select countries and states (optional)
7. Set publication year threshold
8. Define maximum record count
9. Choose:

   * Download PDFs
   * Export CSV
   * Both

Progress is displayed in real time and a `download_log.csv` file is generated upon completion.

---

## File Structure

| File              | Description                                 |
| ----------------- | ------------------------------------------- |
| `main.py`         | GUI controller and application entry point  |
| `core_engine.py`  | API retrieval, PDF pipeline, trend analysis |
| `utils.py`        | Utility functions and download helpers      |
| `config.py`       | Application settings, countries, themes     |
| `states.csv`      | Administrative division database            |
| `biblioblitz.ico` | Windows application icon                    |
| `biblioblitz.png` | Repository logo                             |

---

## Data Sources

| Service          | Purpose                                 |
| ---------------- | --------------------------------------- |
| CrossRef         | Metadata, DOI and publisher information |
| OpenAlex         | Scholarly metadata and OA links         |
| PubMed           | Biomedical literature retrieval         |
| CORE             | Open-access repository aggregation      |
| Unpaywall        | DOI-to-PDF resolution                   |
| Semantic Scholar | Secondary PDF resolution                |

All services are accessed through publicly available endpoints.

No API keys are required.

---

## Performance Notes

* PubMed performs best for biomedical research.
* CrossRef and OpenAlex provide the strongest coverage for environmental sciences, hydrology, geosciences, and engineering disciplines.
* PDF availability depends entirely on publisher open-access policies.
* Metadata is retained even when PDFs cannot be downloaded.
* Very large retrieval jobs (>5,000 records) may require additional runtime due to DOI resolution requests.

---

## Citation

If you use BiblioBlitz in your research, please cite:

```text
Poddar, A., & Bhattacharjee, S. (2025).
BiblioBlitz v4.1: Global Academic Knowledge Harvester &
Literature Review Suite.
Zenodo.
https://doi.org/10.5281/zenodo.20469653
```

---

## Authors

### Ayanava Poddar

Junior Research Fellow (JRF) & PhD Scholar
Department of Hydrology
Indian Institute of Technology Roorkee, India

### Subhrajyoti Bhattacharjee

PhD Scholar
Department of Hydrology
Indian Institute of Technology Roorkee, India

---

## License

This project is distributed under the MIT License.

See the `LICENSE` file for details.

---

## Links

* DOI Archive: https://doi.org/10.5281/zenodo.20469653
* GitHub Repository: https://github.com/Ayanava-23556003/BiblioBlitz
* Latest Release: https://github.com/Ayanava-23556003/BiblioBlitz/releases/download/v4.1.0/BiblioBlitz_Setup_v4.1.exe
