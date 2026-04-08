# CIP Project: Winter Olympics — Deconstructing the Home Advantage

**Repository:** `CIP_FS2026_Group109`

This repository contains the code and data for our group project in the CIP module at HSLU. We investigate the "home advantage" at the Winter Olympics across three research questions: quantifying the host-country effect, testing whether it differs between subjectively and objectively judged sports, and examining whether it spills over to neighbouring nations.

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
| `Scraper/wikipedia_medals_scraper.py` | Static scraping (`requests`, `BeautifulSoup`) | `Data_raw/raw_wikipedia_medals.csv` |
| `Scraper/wikipedia_hosts_scraper.py` | Static scraping with custom User-Agent | `Data_raw/raw_wikipedia_hosts.csv` |
| `Scraper/olympedia_scraper.py` | Static scraping (`requests`, `BeautifulSoup`) | `Data_raw/raw_olympedia_medals.csv` |
| `Scraper/olympics_com_scraper.py` | Dynamic scraping (`Selenium`) — retained to demonstrate interaction with dynamic web elements | `Data_raw/raw_olympics_com_medals_milano-cortina-2026.csv` |
| `Scraper/restcountries_api_collector.py` | REST API (`restcountries.com`) | `Data_raw/raw_restcountries_api.json` |

> **Note on Olympics.com:** This site was initially targeted as the primary source for historical medal data. However, different editions of the Games use structurally different web layouts, making consistent extraction across years unfeasible. We pivoted to Olympedia as the main historical source. The Olympics.com scraper is retained to demonstrate handling of dynamic elements such as cookie consent banners and virtualized DOM scrollers.

### 2. Data Cleaning & Transformation

| Script | Role | Output |
|---|---|---|
| `Feature Engineering & Hypothesis/H1_H3_integration_and_preprocessing.py` | Cleans raw Olympic medal data, standardizes host countries, merges neighbours, and produces the H1/H3 analysis-ready dataset | `Data_clean/clean_wikipedia_medals_features.csv` |
| `Feature Engineering & Hypothesis/H2_integration_and_preprocessing.py` | Builds the master DiD dataset by merging olympedia medals with sport categorisation and host mapping | `Data_clean/clean_olympedia_master.csv` |

### 3. Analysis & Visualisation

| Script | Hypothesis | Methods |
|---|---|---|
| `Feature Engineering & Hypothesis/H1_analysis_and_visualization.py` | RQ1 | Panel regression, country fixed effects, clustered SEs (`scipy`, `numpy`) |
| `Feature Engineering & Hypothesis/H2_analysis_and_visualization.py` | RQ2 | DiD with interaction term, event-study specification (`statsmodels`) |
| `Feature Engineering & Hypothesis/H3_analysis_and_visualization.py` | RQ3 | OLS regression, boxplots, scatterplots (`statsmodels`, `seaborn`, `matplotlib`) |

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
python "Scraper/wikipedia_medals_scraper.py"
python "Scraper/wikipedia_hosts_scraper.py"
python "Scraper/olympedia_scraper.py"
python "Scraper/restcountries_api_collector.py"

# Step 2 — Cleaning & Transformation
python "Feature Engineering & Hypothesis/H1_H3_integration_and_preprocessing.py"
python "Feature Engineering & Hypothesis/H2_integration_and_preprocessing.py"

# Step 3 — Analysis
python "Feature Engineering & Hypothesis/H1_analysis_and_visualization.py"
python "Feature Engineering & Hypothesis/H2_analysis_and_visualization.py"
python "Feature Engineering & Hypothesis/H3_analysis_and_visualization.py"
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

- Birk Diener: Feasability Study, Olympics Scraper, Olympedia Scraper & Hypothesis 1
- Stefan Génevaux: Feasability Study, Olympics Scraper & Hypothesis 2
- Pascal Ingold: Feasability Study, Wikipedia Scraper, Olympics Scraper, Countries API & Hypothesis 3
