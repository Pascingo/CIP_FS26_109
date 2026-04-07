# CIP Project: Winter Olympics — Deconstructing the Home Advantage

**Repository:** `CIP_FS2026_Group109`

This repository contains the code and data for our group project in the **CIP** module at HSLU. We investigate the "home advantage" at the Winter Olympics across three research questions: quantifying the host-country effect, testing whether it differs between subjectively and objectively judged sports, and examining whether it spills over to neighbouring nations.

## Table of Contents
1. [Research Questions](#research-questions)
2. [Project Structure](#project-structure)
3. [Setup & Installation](#setup--installation)
4. [Pipeline](#pipeline)
5. [Legal & Ethical Aspects](#legal--ethical-aspects)
6. [Team & Contributions](#team--contributions)

---

## Research Questions

**RQ1 — Host Country Effect:** Using a panel regression with country fixed effects, what is the statistically significant impact of host country status on a nation's medal share, compared to its rolling baseline from the previous three Winter Games?

**RQ2 — Subjective vs. Objective Sports:** Applying a Difference-in-Differences framework, is the host-country advantage significantly larger in subjectively judged sports (e.g., figure skating) than in objectively measured ones (e.g., alpine skiing)?

**RQ3 — Neighbour Spillover Effect:** Does sharing a land border with the host country confer a statistically significant positive effect on a neighbouring nation's medal share, holding historical baseline performance constant?

---

## Project Structure

### 1. Data Collection

| Script | Method | Output |
|---|---|---|
| `wiki_scraper.py` | Static scraping (`requests`, `BeautifulSoup`) | `winter_olympics_medals_master.csv` |
| `wikipedia_hostcountries_scraper.py` | Static scraping with custom User-Agent | `winter_olympics_hosts_raw.csv` |
| `olympedia_org_scraper.py` | Static scraping (`requests`, `BeautifulSoup`) | `olympedia_medals_all.csv` |
| `olympics_com_scraper.py` | Dynamic scraping (`Selenium`) — retained to demonstrate interaction with dynamic web elements | — |
| `scraper_countries_api_get.py` | REST API (`restcountries.com`) | `countries_neighbors.json` |

> **Note on Olympics.com:** This site was initially targeted as the primary source for historical medal data. However, different editions of the Games use structurally different web layouts, making consistent extraction across years unfeasible. We pivoted to Olympedia as the main historical source. The Olympics.com scraper is retained to demonstrate handling of dynamic elements such as cookie consent banners and virtualized DOM scrollers.

### 2. Data Cleaning & Transformation

| Script | Role | Output |
|---|---|---|
| `clean_winter_olympics.py` | Resolves schema inconsistencies, fixes column types, recomputes missing totals, flags outliers | `winter_olympics_medals_clean.csv` |
| `H2_preprocessing.py` | Builds the master DiD dataset by merging medal data with sport categorisation | `Data_clean/winter_olympics_medals_did_clean.csv` |
| `feature_engineering_h3.py` | Standardises country names to ISO-3, merges host and neighbour data, computes `Is_Host`, `Is_Host_Neighbour`, and rolling baseline | `winter_olympics_analysis_ready.csv` |

### 3. Analysis & Visualisation

| Script | Hypothesis | Methods |
|---|---|---|
| `panel_regression.py` | RQ1 | Panel regression, country & year fixed effects (`statsmodels`) |
| `H2_analysis_and_visualization.py` | RQ2 | DiD with interaction term, event-study specification (`statsmodels`) |
| `H3_analysis_and_visualization.py` | RQ3 | OLS regression, boxplots, scatterplots (`statsmodels`, `seaborn`, `matplotlib`) |

---

## Setup & Installation

Python 3.9+ required. A virtual environment is recommended.

```bash
# 1. Clone the repository
git clone https://github.com/Pascingo/CIP-groupwork

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Pipeline

Run scripts in the following order to reproduce all results from scratch:

```bash
# Step 1 — Data Collection
python wiki_scraper.py
python wikipedia_hostcountries_scraper.py
python olympedia_org_scraper.py
python scraper_countries_api_get.py

# Step 2 — Cleaning & Transformation
python clean_winter_olympics.py
python "Feature Engineering & Hypothesis/H2_preprocessing.py"
python feature_engineering_h3.py

# Step 3 — Analysis
python "Feature Engineering & Hypothesis/H2_analysis_and_visualization.py"
python H3_analysis_and_visualization.py
```

> `olympics_com_scraper.py` is not part of the production pipeline and does not need to be executed to reproduce results.

---

## Legal & Ethical Aspects

- **`robots.txt`:** Consulted prior to scraping for all targeted domains.
- **Rate limiting:** `time.sleep()` delays are implemented in all scrapers to avoid server overload.
- **User-Agent:** A descriptive User-Agent header is sent with all static requests.
- **API:** `restcountries.com` is freely available and requires no authentication.

---

## Team & Contributions

- Birk Diener: Feasability Study, Olympics Scraper & Hypothesis 1
- Stefan Génevaux: Feasability Study, Olympics Scraper & Hypothesis 2
- Pascal Ingold: Feasability Study, Wikipedia Scraper, Olympics Scraper, Countries API & Hypothesis 3
