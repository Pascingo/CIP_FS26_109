"""
Panel Data Regression: Host Country Effect on Winter Olympics Medal Share
=========================================================================
Model:
  medal_share_it = β₀ + β₁·is_host_it + β₂·rolling_avg_it + αᵢ [+ γₜ] + εᵢₜ

Two models:
  M1 — Country FE only
  M2 — Country FE + Year FE

Robustness check:
  M3 — Country FE only, small nations excluded (avg medal share < 1%)

Standard errors clustered at country level (implemented manually via sandwich estimator).
"""

import pandas as pd
import numpy as np
from scipy import stats


# ══════════════════════════════════════════════════════════════════════════════
# 1. Load & feature engineering
# ══════════════════════════════════════════════════════════════════════════════

df = pd.read_csv("../Data_clean/winter_olympics_medals_clean.csv")

# Host mapping (host country name must match Country column in dataset)
HOSTS = {
    1924: "France",        1928: "Switzerland",  1932: "United States",
    1936: "Germany",       1948: "Switzerland",  1952: "Norway",
    1956: "Italy",         1960: "United States",1964: "Austria",
    1968: "France",        1972: "Japan",         1976: "Austria",
    1980: "United States", 1984: "Yugoslavia",    1988: "Canada",
    1992: "France",        1994: "Norway",        1998: "Japan",
    2002: "United States", 2006: "Italy",         2010: "Canada",
    2014: "Russia",        2018: "South Korea",   2022: "China",
    2026: "Italy",
}

# Total medals per year (sum of all countries' Totals)
year_totals = df.groupby("Year")["Total"].sum().rename("year_total")
df = df.merge(year_totals, on="Year")

# Medal share (%)
df["medal_share"] = df["Total"] / df["year_total"] * 100

# Host dummy
df["is_host"] = df.apply(
    lambda r: 1 if HOSTS.get(r["Year"]) == r["Country"] else 0, axis=1
)

# Sort for rolling calculation
df = df.sort_values(["Country", "Year"]).reset_index(drop=True)

# Rolling 3-game average of medal_share (strictly preceding games)
def rolling_prev3(series):
    return series.shift(1).rolling(window=3, min_periods=3).mean()

df["rolling_avg"] = df.groupby("Country")["medal_share"].transform(rolling_prev3)

# Drop rows without a full 3-game history
df_reg = df.dropna(subset=["rolling_avg"]).copy()

print(f"Full dataset:    {len(df)} observations, {df['Country'].nunique()} countries")
print(f"After filtering: {len(df_reg)} observations, {df_reg['Country'].nunique()} countries")
print(f"Host obs in regression sample: {df_reg['is_host'].sum()}")
print(f"Host events: {df_reg[df_reg['is_host']==1][['Year','Country']].to_string(index=False)}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. Within (Fixed Effects) estimator with clustered SEs
# ══════════════════════════════════════════════════════════════════════════════

def within_transform(data, group_col, cols):
    """Demean each column within groups (Within estimator)."""
    out = data[cols].copy()
    means = data.groupby(group_col)[cols].transform("mean")
    return out - means


def ols_with_clustered_se(y, X, cluster_ids):
    """
    OLS estimator with cluster-robust (sandwich) standard errors.
    Returns: coef, se, t_stat, p_value, n, k
    """
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    coef = XtX_inv @ X.T @ y
    resid = y - X @ coef

    # Cluster-robust variance (Liang-Zeger sandwich)
    clusters = np.unique(cluster_ids)
    G = len(clusters)
    meat = np.zeros((k, k))
    for c in clusters:
        mask = cluster_ids == c
        Xc = X[mask]
        ec = resid[mask]
        score = Xc.T @ ec
        meat += np.outer(score, score)

    # Small-sample correction
    correction = (G / (G - 1)) * ((n - 1) / (n - k))
    V = correction * XtX_inv @ meat @ XtX_inv

    se = np.sqrt(np.diag(V))
    t_stat = coef / se
    # Use t-distribution with G-1 df (conservative, cluster-level)
    p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), df=G - 1))

    # R² (within)
    ss_res = np.sum(resid**2)
    ss_tot = np.sum((y - y.mean())**2)
    r2_within = 1 - ss_res / ss_tot

    return coef, se, t_stat, p_value, r2_within, n, G


def run_model(data, model_name, year_fe=False):
    """Run within-FE model, return formatted results dict."""
    cols = ["medal_share", "is_host", "rolling_avg"]

    # Within-transform on country dimension
    d = within_transform(data, "Country", cols)

    # Add year FE as dummies (within-transformed country means already absorbed)
    if year_fe:
        year_dummies = pd.get_dummies(data["Year"], prefix="yr", drop_first=True).astype(float)
        year_dummies.index = data.index
        # Demean year dummies within country
        tmp = data[["Country"]].join(year_dummies)
        yd_means = tmp.groupby("Country")[year_dummies.columns].transform("mean")
        yd_dm = year_dummies - yd_means
        X = np.column_stack([d["is_host"].values, d["rolling_avg"].values, yd_dm.values])
    else:
        X = np.column_stack([d["is_host"].values, d["rolling_avg"].values])

    y = d["medal_share"].values
    cluster_ids = data["Country"].values

    coef, se, t_stat, p_val, r2, n, G = ols_with_clustered_se(y, X, cluster_ids)

    # Only report main coefficients (not year FE dummies)
    labels = ["is_host", "rolling_avg"]
    results = {
        "model": model_name,
        "n_obs": n,
        "n_countries": G,
        "r2_within": round(r2, 4),
        "coefs": {}
    }
    for i, label in enumerate(labels):
        stars = ""
        if p_val[i] < 0.01:  stars = "***"
        elif p_val[i] < 0.05: stars = "**"
        elif p_val[i] < 0.1:  stars = "*"
        results["coefs"][label] = {
            "coef": round(coef[i], 4),
            "se":   round(se[i], 4),
            "t":    round(t_stat[i], 3),
            "p":    round(p_val[i], 4),
            "sig":  stars,
        }
    return results


# ══════════════════════════════════════════════════════════════════════════════
# 3. Run the three models
# ══════════════════════════════════════════════════════════════════════════════

m1 = run_model(df_reg, "M1: Country FE", year_fe=False)
m2 = run_model(df_reg, "M2: Country FE + Year FE", year_fe=True)

# Robustness: exclude small nations (avg medal share < 1%)
avg_share = df_reg.groupby("Country")["medal_share"].mean()
large_nations = avg_share[avg_share >= 1.0].index
df_robust = df_reg[df_reg["Country"].isin(large_nations)].copy()
m3 = run_model(df_robust, "M3: Country FE (large nations only)", year_fe=False)

models = [m1, m2, m3]


# ══════════════════════════════════════════════════════════════════════════════
# 4. Print results table
# ══════════════════════════════════════════════════════════════════════════════

def print_results(models):
    SEP = "─" * 72
    print(f"\n{'HOST COUNTRY EFFECT ON WINTER OLYMPICS MEDAL SHARE':^72}")
    print(f"{'Panel Data Regression — Country Fixed Effects':^72}")
    print(SEP)
    print(f"{'Dependent variable: medal_share (% of total medals)':^72}")
    print(SEP)

    header = f"{'':28}" + "".join(f"{m['model']:>22}" for m in models)
    print(header)
    print(SEP)

    for var, label in [("is_host", "Host country (β₁)"), ("rolling_avg", "3-game rolling avg (β₂)")]:
        coef_row  = f"{label:<28}"
        se_row    = f"{'':28}"
        for m in models:
            c = m["coefs"][var]
            coef_row += f"  {c['coef']:>8.4f}{c['sig']:<3}      "
            se_row   += f"  {'(' + str(c['se']) + ')':>12}      "
        print(coef_row)
        print(se_row)
        print()

    print(SEP)
    for m in models:
        print(f"  {m['model']}")
        print(f"    Observations : {m['n_obs']}")
        print(f"    Countries    : {m['n_countries']}")
        print(f"    R² (within)  : {m['r2_within']}")
    print(SEP)
    print("  Significance: *** p<0.01  ** p<0.05  * p<0.1")
    print("  Standard errors (in parentheses) clustered at country level")
    print(SEP)

print_results(models)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Save detailed results to CSV
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for m in models:
    for var, d in m["coefs"].items():
        rows.append({
            "model": m["model"],
            "variable": var,
            "coefficient": d["coef"],
            "std_error": d["se"],
            "t_statistic": d["t"],
            "p_value": d["p"],
            "significance": d["sig"],
            "n_obs": m["n_obs"],
            "n_countries": m["n_countries"],
            "r2_within": m["r2_within"],
        })

results_df = pd.DataFrame(rows)
results_df.to_csv("regression_results.csv", index=False)
print("\nDetailed results saved.")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Descriptive check: actual medal share in host vs non-host years
# ══════════════════════════════════════════════════════════════════════════════

print("\n── Descriptive: medal share for host nations ──────────────────────────")
host_obs = df_reg[df_reg["is_host"] == 1][["Year", "Country", "rolling_avg", "medal_share"]].copy()
host_obs["uplift"] = host_obs["medal_share"] - host_obs["rolling_avg"]
host_obs.columns = ["Year", "Country", "Rolling Avg", "Actual Share", "Uplift (pp)"]
print(host_obs.round(2).to_string(index=False))
print(f"\nMean uplift: {host_obs['Uplift (pp)'].mean():.2f} percentage points")
