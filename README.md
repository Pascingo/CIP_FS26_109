# CIP Project: Winter Olympics Medal Analysis

**Repository Naming Convention:** `CIP_FS2026_Group109`

This repository contains the code and data for our project in the **CIP (Data Collection, Integration, and Preprocessing)** 
module at HSLU. We analyze historical data from the Winter Olympics to identify trends and answer specific
research questions (e.g., the "Host Country Effect").

## Table of Contents
1. [Project Description & Research Questions](#project-description--research-questions)
2. [Project Structure](#project-structure)
3. [Setup & Installation](#setup--installation)
4. [Usage (Pipeline)](#usage-pipeline)
5. [Legal & Ethical Aspects](#legal--ethical-aspects)
6. [Team & Contributions](#team--contributions)

---

## Project Description & Research Questions
This project covers a complete data science pipeline:
* **Research Question:** Is there a "Host Country Effect" (home advantage) at the Winter Olympics that results
* in a significantly higher medal share for the host nation?
* **Data Collection:** Web scraping of Wikipedia (historical data) and olympics.com (current data),
* plus geographical data enrichment via a REST API.
* **Data Cleaning:** Harmonization of data schemas, handling of missing values, and type casting using `pandas`.
* **Analysis:** Panel data regression for statistical evaluation.

---

## Project Structure

Our pipeline is divided into three main phases, reflecting the CIP module requirements:

### 1. Data Collection (Scraping & APIs)
* `wiki_scraper.py`: Extracts historical medal tables (1924-2026) from Wikipedia using `requests` and `BeautifulSoup` (Static Scraping).
* `olympics_com_scraper.py`: An advanced scraper for dynamic content (Milano-Cortina 2026) using `selenium`. It bypasses dynamic loading and renders JavaScript.
* `countries_api_get.py`: Queries the `restcountries.com` API to retrieve country codes (`cca3`) and geographical neighbors (Output: `countries_neighbors.json`).

### 2. Data Cleaning & Transformation
* `clean_winter_olympics.py`: The core data preparation script using `pandas`. It resolves inconsistencies in the
* raw master CSV file. It fixes column schemas ('NOC' vs. 'Nation'), removes aggregate rows (e.g., "Totals") and
* non-national entries ("Mixed team"), recalculates missing `Total` values, and corrects data types (Output: `winter_olympics_medals_clean.csv`).

### 3. Analysis & Presentation
* `panel_regression.py`: Performs a panel regression to isolate the Host Country Effect, utilizing Country Fixed Effects
* and Year Fixed Effects (`scipy`, `pandas`, `numpy`).

---

## Setup & Installation

Please ensure Python 3.9+ is installed. We highly recommend using a virtual environment (`venv` or `conda`).

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Pascingo/CIP-groupwork]
   
2. **Install dependencies:**
   Using the provided `requirements.txt` file, install all necessary packages in your virtual environment:
   ```bash
   pip install -r requirements.txt
  
## Usage (Pipeline)
To run the pipeline from scratch, execute the scripts in the following order:
1. **Collect Data:**
    python wiki_scraper.py
    python olympics_com_scraper.py
    python countries_api_get.py
2. **Clean Data**
    python clean_winter_olympics.py
3. **Run Analysis**
    python panel_regression.py
ZU ERGÄNZEN MIT ANALYSE 2 UND 3

## Legal & Ethical Aspects (Web Scraping)
We adhered to web scraping best practices during data collection:

- robots.txt: Before scraping, we checked the robots.txt of the respective sites (e.g., Wikipedia) to ensure the endpoints were allowed for crawlers.
- Rate Limiting: A time.sleep(5) was implemented in wiki_scraper.py to minimize server load.
- User-Agent: A legitimate User-Agent header is sent with our static requests.
- Open Data: The utilized API (restcountries.com) is freely available and does not require an API key.

## Team & Contributions
- Birk Diener: Feasability Study, Olympics Scraper & Hypothesis 1
- Stefan Génevaux: Feasability Study, Olympics Scraper & Hypothesis 2
- Pascal Ingold: Feasability Study, Wikipedia Scraper, Olympics Scraper, Countries API & Hypothesis 3