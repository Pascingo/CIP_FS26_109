# Documentation

## Introduction
In this CIP project, we go through a typical data science journey to apply Python skills in data acquisition, preparation, and analysis. The primary motivation of this study is to investigate the performance of nations at the Winter Olympics, specifically focusing on the host country effect and geographic proximity spillover effects on medal shares. By combining multiple data sources, we aim to expose new information and answer complex research questions regarding athletic success factors
## Data

### Sources
To comprehensively answer our research questions, we gathered data from various complementary locations. Our primary data sources include:

- Wikipedia & Olympedia: Used to extract historical medal tables and baseline performance metrics.

- Olympics.com: Targeted for highly specific, modern event data (e.g., Milano Cortina 2026 categories).

- REST Countries API: Utilized to acquire geographic data, specifically neighboring country codes (ISO-3 borders), to evaluate geographic spillover effects.

Throughout the data collection process, we strictly respected legal boundary conditions by consulting the robots.txt files of the respective domains and implementing appropriate delays (rate limiting) to avoid server overloads.
### Creation
Since the effort to acquire data via APIs is relatively low, we supplemented our dataset using advanced web scraping techniques.

For static HTML pages, we utilized the requests library in combination with BeautifulSoup to parse table structures efficiently.

To acquire data hidden behind dynamic elements, we implemented Selenium. This allowed us to automatically handle cookie consent banners, execute JavaScript, and interact with dynamic elements like expanding buttons within virtualized DOM scrollers.

### Transformation
Real-world scraped data is rarely perfectly clean, making data transformation a critical phase of this project. We utilized the pandas and numpy libraries extensively to address poor data quality and format the dataset appropriately. The mandatory cleansing steps included:

Resolving Schema Inconsistencies: We identified and corrected issues such as swapped Rank/Nation columns and merged aggregate rows that were mixed with country data.

Standardization: Country names were standardized into ISO-3 (CCA3) codes using the pycountry library and custom mappings for historical entities (e.g., Soviet Union, Yugoslavia) to ensure accurate dataset integration.

Data Types and Missing Values: Columns were cast to their appropriate numeric datatypes, and missing total medal counts were recomputed by aggregating Gold, Silver, and Bronze values.

Data Enrichment: We enriched the dataset by merging the historical medal data with host information and dynamically calculating boolean columns such as Is_Host and Is_Host_Neighbour to support our analysis

### Presentation
Each group member decided for himself to choose a presentation framework with which he liked to work with. H3 was using Seaborn for the Boxplot and Matplotlib for the Scatterplot.

## Discussion

### Hypothesis 1

### Hypothesis 2
**Can we determine a difference in the effects of being the host of the events when comparing subjective and objective sports?**

#### Identification Strategy
We estimate the effect of hosting the Olympic Games on medal performance using a difference‑in‑differences–style research design implemented via fixed‑effects linear regression. Identification comes from comparing host and non‑host countries within the same Olympic Games, exploiting the fact that each Games features one treated unit (the host country) and many control units (non‑hosts). Repeating this comparison across Olympic years allows us to identify the average host‑country advantage while controlling for time‑invariant country characteristics and common Olympic‑year shocks.
Although the model is estimated using ordinary least squares, the identifying variation corresponds to a DiD logic: the coefficient of interest captures systematic differences between host and non‑host countries within a given Games, net of country and year fixed effects. Regression provides a flexible framework that allows us to incorporate fixed effects and conduct inference with clustered standard errors.

#### Heterogeneity by Judging Type
To examine whether host‑country advantages differ by the nature of performance evaluation, we allow the host effect to vary between subjectively judged sports and objectively scored sports. Objectively scored sports (e.g., time‑ or distance‑based events) serve as the baseline category.
Formally, we estimate regressions of the form:
Ycts=β1 Hostct+β2 Subjectives+β3(Hostct×Subjectives)+αc+λt+εcts,Y_{c t s}
=
\beta_1\,\text{Host}_{c t}
+
\beta_2\,\text{Subjective}_{s}
+
\beta_3(\text{Host}_{c t} \times \text{Subjective}_{s})
+
\alpha_c
+
\lambda_t
+
\varepsilon_{c t s},Ycts​=β1​Hostct​+β2​Subjectives​+β3​(Hostct​×Subjectives​)+αc​+λt​+εcts​,
where YctsY_{c t s}Ycts​ denotes country ccc’s medal share in year ttt and sport category sss. αc\alpha_cαc​ and λt\lambda_tλt​ denote country and year fixed effects. The coefficient β1\beta_1β1​ captures the host advantage in objectively scored sports, while β3\beta_3β3​ captures whether this host advantage is incrementally larger in subjectively judged sports relative to objective sports.

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

==================================================
--- DIFFERENCE-IN-DIFFERENCES ANALYSIS (OLS) ---
==================================================
                            OLS Regression Results                            
==============================================================================
Dep. Variable:              Medal_Share   R-squared:                       0.525
Model:                            OLS   Adj. R-squared:                  0.464
Method:                 Least Squares   F-statistic:                     56.69
Date:                Sat, 28 Mar 2026   Prob (F-statistic):           5.73e-28
Time:                        15:44:16   Log-Likelihood:                 962.21
No. Observations:                 663   AIC:                           -1772.
Df Residuals:                     587   BIC:                           -1431.
Df Model:                          75                                         
Covariance Type:               cluster                                         
==============================================================================
                                   coef    std err          z      P>|z|     
------------------------------------------------------------------------------
Intercept                        0.0318      0.019      1.713      0.087
is_host                          0.0125      0.006      2.138      0.033
is_host:subjective               0.0067      0.008      0.857      0.392
==============================================================================
Notes:
[1] Country and year fixed effects included.
[2] Standard errors clustered at the country (NOC) level.
[3] Objective sports are the baseline category.
[4] is_host captures the host advantage in objective sports.
[5] is_host:subjective captures the incremental host advantage
    in subjectively judged sports relative to objective sports.
==============================================================================


==================================================
--- EVENT-STUDY ANALYSIS (STACKED DiD, OLS) ---
==================================================
                            OLS Regression Results                            
==============================================================================
Dep. Variable:              Medal_Share   R-squared:                       0.527
Model:                            OLS   Adj. R-squared:                  0.516
Method:                 Least Squares   F-statistic:                 2.73e+08
Date:                Sat, 28 Mar 2026   Prob (F-statistic):          7.72e-190
Time:                        15:44:16   Log-Likelihood:                6013.8
No. Observations:                4135   AIC:                        -11830.
Df Residuals:                    4035   BIC:                        -11190.
Df Model:                          99                                         
Covariance Type:               cluster                                         
==============================================================================
                                   coef    std err          z      P>|z|     
------------------------------------------------------------------------------
is_host_event:C(k)[T.0]          0.0400      0.018      2.200      0.028

is_host_event:C(k)[T.-3]:subj    0.0018      0.030      0.059      0.953
is_host_event:C(k)[T.-2]:subj   -0.0097      0.032     -0.300      0.764
is_host_event:C(k)[T.0]:subj     0.0029      0.037      0.079      0.937
is_host_event:C(k)[T.1]:subj     0.0381      0.022      1.734      0.083
is_host_event:C(k)[T.2]:subj     0.0372      0.027      1.352      0.176
is_host_event:C(k)[T.3]:subj     0.0278      0.017      1.627      0.104
==============================================================================
Notes:
[1] Event time k measured in Olympic cycles relative to host year.
[2] Reference period: k = -1.
[3] Coefficients with suffix ':subj' denote incremental host effects
    in subjectively judged sports relative to objectively scored sports.
[4] Country and year fixed effects included.
[5] Standard errors clustered at the country (NOC) level.
==============================================================================


### Hypothesis 3
**Is there a correlation between being neighbor or being host and the medals won?**

==================================================
--- STATISTICAL ANALYSIS (OLS REGRESSION) ---
==================================================
                            OLS Regression Results                            
==============================================================================
Dep. Variable:            Medal_Share   R-squared:                       0.541
Model:                            OLS   Adj. R-squared:                  0.538
Method:                 Least Squares   F-statistic:                     165.0
Date:                Fri, 27 Mar 2026   Prob (F-statistic):           1.14e-70
Time:                        09:29:24   Log-Likelihood:                 818.01
No. Observations:                 424   AIC:                            -1628.
Df Residuals:                     420   BIC:                            -1612.
Df Model:                           3                                         
Covariance Type:            nonrobust                                         
=======================================================================================
                          coef    std err          t      P>|t|      [0.025      0.975]
---------------------------------------------------------------------------------------
Intercept               0.0138      0.003      5.386      0.000       0.009       0.019
Is_Host_Neighbour       0.0090      0.005      1.713      0.087      -0.001       0.019
Is_Host                 0.0406      0.008      5.344      0.000       0.026       0.056
Historical_Baseline     0.6718      0.031     21.406      0.000       0.610       0.733
==============================================================================
Omnibus:                       90.311   Durbin-Watson:                   2.673
Prob(Omnibus):                  0.000   Jarque-Bera (JB):              335.102
Skew:                           0.909   Prob(JB):                     1.71e-73
Kurtosis:                       6.958   Cond. No.                         18.5
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.

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