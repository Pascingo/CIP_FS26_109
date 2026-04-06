# Documentation: Deconstructing the "Home Advantage" at the Winter Olympics

## Introduction

The Winter Olympic Games require massive financial and infrastructural investments from host nations, an effort often justified by the promise of economic stimulus and national prestige. A central pillar of this prestige is the well-documented "home advantage". However, while the existence of this effect is widely accepted, the underlying mechanisms that drive it are complex and remain ready for a deeper analysis.

This project investigates three related aspects of the home advantage at the Winter Olympics. First, by isolating the host "bump" from a nation's historical baseline, we provide a precise measurement of the "athletic return on investment", moving beyond raw medal counts to a standardized measure of success. Second, by contrasting subjectively judged sports with objectively measured ones, we interrogate the human element of Olympic scoring: is the home advantage driven purely by elevated athlete performance, or is it artificially inflated by unconscious judge bias? Third, by investigating regional spillovers, we test whether "home advantage" is just a proxy for geographical and logistical benefits — such as climate familiarity, shared training infrastructure, and the absence of jet lag.

To answer these questions, we go through a full data science project journey: acquiring data from multiple complementary sources using web scraping and APIs, cleaning and transforming the raw data with pandas and numpy, and applying econometric models to derive statistically grounded answers.

## Methods

### Data Sources

To comprehensively answer our research questions, we gathered data from various complementary locations. Our primary data sources include:

- **Olympics.com:** The official IOC website, initially targeted as the primary source for historical medal standings. However, different editions of the Games use structurally different web layouts, making consistent automated extraction across years unfeasible. We therefore pivoted to Olympedia as our main historical data source. The Olympics.com scraper was retained to demonstrate interaction with dynamic web elements such as cookie consent banners and virtualized DOM scrollers.
- **Wikipedia & Olympedia:** Used to extract historical medal tables and baseline performance metrics across all past Winter Games. Wikipedia served as a robust supplementary source and immediate backup, ensuring consistent historical coverage even where other sources lacked specific records.
- **REST Countries API:** Utilized to acquire structured geographic data, specifically neighboring country codes (ISO-3 borders), to evaluate geographic spillover effects. This allowed us to enrich our primary dataset with spatial information and merge the different subsets to generate new insights.

Throughout the data collection process, we strictly respected legal boundary conditions by consulting the `robots.txt` files of the respective domains and implementing appropriate delays (rate limiting) to avoid server overloads.

### Data Acquisition

For static HTML pages, we utilized the `requests` library in combination with `BeautifulSoup` to parse table structures efficiently.

To acquire data hidden behind dynamic elements, we implemented `Selenium`. This allowed us to automatically handle cookie consent banners, execute JavaScript, and interact with dynamic elements such as dropdown menus, search filters, and expanding buttons within virtualized DOM scrollers.

### Data Transformation & Cleaning

Real-world scraped data is rarely perfectly clean, making data transformation a critical phase of this project. We utilized the `pandas` and `numpy` libraries extensively to address poor data quality and format the dataset appropriately. The mandatory cleansing steps included:

**Resolving Schema Inconsistencies:** We identified and corrected issues such as swapped Rank/Nation columns and merged aggregate rows that were mixed with country data. Where two countries shared a rank, one entry was recorded as 0 — since the ranking column was not required for the analysis, we dropped it entirely rather than attempt an error-prone repair.

**Standardization:** Country names were standardized into ISO-3 (CCA3) codes using the `pycountry` library and custom mappings for historical entities (e.g., Soviet Union, Yugoslavia, East/West Germany) to ensure accurate dataset integration across decades of changing borders. This addressed the geopolitical inconsistencies inherent in a dataset spanning the full history of the Winter Olympics.

**Data Types and Missing Values:** Columns were cast to their appropriate numeric datatypes, and missing total medal counts were recomputed by aggregating Gold, Silver, and Bronze values.

**Outlier Treatment:** Outlier flags were computed per medal type and year to allow for sensitivity checks in the regression models without discarding data outright.

**Data Enrichment:** We enriched the dataset by merging the historical medal data with host information and dynamically calculating boolean columns such as `Is_Host` and `Is_Host_Neighbour`, and by computing each country's historical rolling baseline from the previous three Winter Games to serve as a control variable in the regression models.

### Analysis Methods

Each research question is addressed with a dedicated econometric approach. For RQ1, we apply a panel data regression with country and year fixed effects to isolate the host-country bump from a nation's historical baseline. For RQ2, we implement a Difference-in-Differences (DiD) framework with an interaction term between host status and sport type (subjective vs. objective), complemented by an event-study specification to test for pre-trends. For RQ3, we extend the baseline OLS model with a geographic proximity indicator to test for a statistically significant spillover effect on neighbouring countries' medal shares. Subjective and objective sports were categorized manually and validated, with a third "mixed" category used for hybrid disciplines such as ski jumping.

## Discussion

### Hypothesis 1
**Does hosting the Winter Olympics confer a statistically significant advantage in medal share, controlling for the host country's historical performance?**

#### Approach
We estimate a country fixed-effects regression in which the dependent variable is each country's share of total medals per Games (in percentage points). Country fixed effects absorb time-invariant differences such as sporting tradition and infrastructure. A rolling average of the preceding three Games controls for recent performance trajectories. Standard errors are clustered at the country level.

#### Results

![Medal share uplift for host nations relative to their 3-game rolling average baseline]

Hosting the Winter Olympics increases a country's medal share by **3.08 percentage points** (SE = 0.78, p < 0.001, 95% CI [1.50, 4.66]), a statistically and practically significant effect given that the median country wins fewer than 5% of all medals. The rolling average coefficient (β₂ = 0.47, p < 0.001) confirms that past performance is the strongest predictor of current medal share.

The figure shows the raw uplift — actual share minus rolling baseline — for all 18 host events with sufficient historical data. **83% are positive**, with a mean of +2.51 pp and a median of +2.20 pp. The effect is not uniform: gains range from +9.14 pp (Switzerland 1948) and +7.73 pp (USA 2002) to −3.58 pp (Austria 1976) and −2.88 pp (Italy 2006), indicating that idiosyncratic factors can offset the structural home advantage in individual editions.

#### Conclusion
The evidence confirms that hosting is a measurable driver of medal success. The host-country advantage is consistent with mechanisms documented in the sports economics literature, including relaxed qualification rules for the host nation, venue familiarity, and logistical advantages in preparation.

### Hypothesis 2
**Can we determine a difference in the effects of being the host of the events when comparing subjective and objective sports?**

#### Identification Strategy
We estimate the effect of hosting the Olympic Games on medal performance using a difference‑in‑differences–style research design implemented via fixed‑effects linear regression. Identification comes from comparing host and non‑host countries within the same Olympic Games, exploiting the fact that each Games features one treated unit (the host country) and many control units (non‑hosts). Repeating this comparison across Olympic years allows us to identify the average host‑country advantage while controlling for time‑invariant country characteristics and common Olympic‑year shocks.
Although the model is estimated using ordinary least squares, the identifying variation corresponds to a DiD logic: the coefficient of interest captures systematic differences between host and non‑host countries within a given Games, net of country and year fixed effects. Regression provides a flexible framework that allows us to incorporate fixed effects and conduct inference with clustered standard errors.

#### Heterogeneity by Judging Type
To examine whether host‑country advantages differ by the nature of performance evaluation, we allow the host effect to vary between subjectively judged sports and objectively scored sports. Objectively scored sports (e.g., time‑ or distance‑based events) serve as the baseline category.
Formally, we estimate regressions of the form:

$$Y_{cts} = \beta_1 \, \text{Host}_{ct} + \beta_2 \, \text{Subjective}_{s} + \beta_3 (\text{Host}_{ct} \times \text{Subjective}_{s}) + \alpha_c + \lambda_t + \varepsilon_{cts}$$

where $Y_{cts}$ denotes country $c$'s medal share in year $t$ and sport category $s$. $\alpha_c$ and $\lambda_t$ denote country and year fixed effects. The coefficient $\beta_1$ captures the host advantage in objectively scored sports, while $\beta_3$ captures whether this host advantage is incrementally larger in subjectively judged sports relative to objective sports.

#### Main Results
The estimates reveal a statistically significant host‑country advantage in objectively scored sports. Hosting the Olympic Games increases a country’s medal share in objective events by approximately 1.3 percentage points, a magnitude that is both statistically significant and economically meaningful. This finding is consistent with existing evidence of a general host‑country advantage operating through mechanisms such as increased participation, familiarity with venues, or logistical advantages.
However, we find no evidence that this host‑country advantage is systematically larger in subjectively judged sports. The interaction between host status and subjective judging is positive but statistically indistinguishable from zero. This implies that, while hosting improves medal performance overall, subjectively judged sports do not exhibit an additional host‑specific boost relative to objectively scored sports.
Taken together, the estimates indicate that the host‑country effect is present across the Olympic program but does not appear to be driven by differential treatment or bias in judged events.

#### Fixed Effects and Inference
Country fixed effects absorb all time‑invariant differences across countries (e.g., long‑run sports institutions, population size, or historical sporting strength), while year fixed effects capture shocks common to all countries in a given Olympic Games (e.g., changes in the event program or scoring rules). Standard errors are clustered at the country level to allow for arbitrary serial correlation in medal outcomes within countries over time.

#### Event‑Study Diagnostics
To assess the plausibility of the identifying assumptions and to explore the dynamics of host effects, we estimate a stacked event‑study specification that traces medal outcomes across Olympic cycles relative to the host year. This approach allows us to test for differential pre‑trends and to examine whether host effects persist beyond the host Games.
The event‑study estimates show no evidence of differential pre‑trends between future host and non‑host countries in subjectively judged sports prior to hosting, lending support to the identifying assumptions of the main specification. In the host year itself, countries experience a pronounced and statistically significant increase in medal share, driven primarily by objectively scored sports.
Crucially, the event‑study reveals no statistically significant incremental host effect in subjectively judged sports either in the host year or in subsequent Olympic cycles. Post‑host estimates remain small and imprecise, suggesting that any potential judging‑related advantages are neither large nor persistent.

#### Interpretation
Overall, the results indicate that hosting the Olympic Games confers a clear performance advantage, but this advantage does not differ meaningfully between subjectively judged and objectively measured sports. These findings suggest that the host‑country effect operates primarily through structural or institutional channels rather than through systematic bias in subjective evaluation. While concerns about judging discretion are often raised in public discourse, our evidence does not support the presence of a differential host advantage in judged events.


### Hypothesis 3
**Is there a correlation between being neighbor or being host and the medals won?**


#### 1. Overall Model Fit  
The Ordinary Least Squares (OLS) regression model produces an R-squared value of 0.541. This suggests that the model explains approximately 54.1% of the variation in Olympic medal share.

#### 2. Control Variables (Isolating the Effect)  
To assess the spatial spillover effect accurately, two key confounding factors were controlled for:

**Historical Baseline (Past Performance):**  
As expected, this variable is the strongest predictor in the model (coefficient = 0.6718, p-value < 0.001). A country’s medal share in the previous Winter Olympics is strongly associated with its current performance, making it an essential control variable.

**Home Advantage (Is_Host):**  
The results confirm the presence of a home advantage (coefficient = 0.0406, p-value < 0.001). On average, hosting the Winter Olympics increases a country’s medal share by around 4.06%.

#### 3. Research Question: The Geographic Spillover Effect  
The main focus of this analysis is the variable *Is_Host_Neighbour*:

**Coefficient (0.0090):**  
The model indicates a small positive effect, suggesting that countries neighbouring the host may experience an average increase of about 0.9% in their medal share.

**Statistical Significance (p-value = 0.087):**  
Typically, a significance level of 0.05 is required to reject the null hypothesis. Since the p-value exceeds this threshold, the observed effect is not statistically significant at the 5% level, although it can be considered marginally significant at the 10% level.

#### 4. Conclusion  
Based on both the statistical and spatial analysis, the research question can be answered in the negative. After controlling for past performance and the host country’s advantage, sharing a land border with the host does not lead to a statistically significant increase in Olympic medal share. This conclusion is further supported by the visual analysis (boxplots and scatterplots), which shows considerable overlap in performance between neighbouring and non-neighbouring countries.



## Conclusion

### Learnings

### Limitations

### Outlook & Further Steps
