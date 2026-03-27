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