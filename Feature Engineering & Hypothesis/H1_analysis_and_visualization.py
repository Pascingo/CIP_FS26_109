"""
H1 — Host Country Effect on Winter Olympics Medal Share
========================================================
Question:
    Using a panel data regression with country fixed effects, what is the statistically significant impact of
    host country status on a nation’s medal share (measured as the percentage of total contested medals),
    compared to its baseline performance rolling average from the previous three Winter Olympic Games?

Hypothesis:
    Hosting the Winter Olympics significantly increases the host country's
    share of total medals won, even after controlling for the country's
    historical performance.

Model (M1 — Country FE):
    medal_share_it = β₁·is_host_it + β₂·rolling_avg_it + αᵢ + εᵢₜ

    where αᵢ = country fixed effects absorbed via within-transformation.
    β₁ captures the average host-country advantage in percentage points
    of total medal share, net of each country's time-invariant baseline.

Standard errors clustered at country level (Liang–Zeger sandwich).
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ══════════════════════════════════════════════════════════════════════════════
# 0. Paths
# ══════════════════════════════════════════════════════════════════════════════

current_script_dir = Path(__file__).resolve().parent
BASE = current_script_dir.parent

DATA = BASE / "Data_clean" / "winter_olympics_analysis_ready.csv"
OUT_CSV = BASE / "Visualisations"/ "H1_regression_results.csv"
OUT_UPLIFT = BASE / "Visualisations"/ "H1_host_uplift.png"


# ══════════════════════════════════════════════════════════════════════════════
# 1. Load & feature engineering
# ══════════════════════════════════════════════════════════════════════════════

df = pd.read_csv(DATA)

# Is_Host already present as boolean — cast to int for regression
df["is_host"] = df["Is_Host"].astype(int)

# Total medals per year
year_totals = df.groupby("Year")["Total"].sum().rename("year_total")
df = df.merge(year_totals, on="Year")

# Medal share (%)
df["medal_share"] = df["Total"] / df["year_total"] * 100

# Sort for rolling calculation
df = df.sort_values(["Country_ISO3", "Year"]).reset_index(drop=True)


def rolling_prev3(series):
    """Strictly preceding 3-game average (requires full 3-game history)."""
    return series.shift(1).rolling(window=3, min_periods=3).mean()


df["rolling_avg"] = df.groupby("Country_ISO3")["medal_share"].transform(rolling_prev3)

# Drop rows without a full 3-game history
df_reg = df.dropna(subset=["rolling_avg"]).copy().reset_index(drop=True)

print(f"Full dataset:    {len(df)} obs, {df['Country_ISO3'].nunique()} countries")
print(f"After filtering: {len(df_reg)} obs, {df_reg['Country_ISO3'].nunique()} countries")
print(f"Host obs in regression sample: {df_reg['is_host'].sum()}")
print("Host events in sample:")
print(
    df_reg[df_reg["is_host"] == 1][["Year", "Country_ISO3"]]
    .sort_values("Year")
    .to_string(index=False)
)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Fixed Effects estimators
# ══════════════════════════════════════════════════════════════════════════════

def demean_within(vec: np.ndarray, group_ids: np.ndarray) -> np.ndarray:
    """Subtract group means from each observation (one-way within transform)."""
    out = vec.copy().astype(float)
    for g in np.unique(group_ids):
        mask = group_ids == g
        out[mask] -= out[mask].mean()
    return out


def ols_clustered(y: np.ndarray, X: np.ndarray,
                  cluster_ids: np.ndarray) -> tuple:
    """
    OLS with Liang-Zeger cluster-robust standard errors.

    Returns: coef, se, t_stat, p_value, r2_within, G
    """
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    coef = XtX_inv @ X.T @ y
    resid = y - X @ coef

    clusters = np.unique(cluster_ids)
    G = len(clusters)
    meat = np.zeros((k, k))
    for c in clusters:
        mask = cluster_ids == c
        score = X[mask].T @ resid[mask]
        meat += np.outer(score, score)

    correction = (G / (G - 1)) * ((n - 1) / (n - k))
    V = correction * XtX_inv @ meat @ XtX_inv

    se = np.sqrt(np.diag(V))
    t_stat = coef / se
    p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), df=G - 1))

    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2_within = 1 - ss_res / ss_tot

    return coef, se, t_stat, p_value, r2_within, G


def run_model(data: pd.DataFrame) -> dict:
    """
    Fit M1 (Country FE) via within-transformation and clustered SEs.

    Demeans all variables by country mean, then runs OLS on the
    demeaned data. This is the standard within (fixed-effects) estimator.
    """
    country_ids = data["Country_ISO3"].values

    raw = np.column_stack([
        data["medal_share"].values,
        data["is_host"].values,
        data["rolling_avg"].values,
    ])

    dm = np.column_stack([
        demean_within(raw[:, col], country_ids)
        for col in range(raw.shape[1])
    ])

    y = dm[:, 0]
    X = dm[:, 1:]  # [is_host, rolling_avg]

    coef, se, t_stat, p_val, r2, G = ols_clustered(y, X, country_ids)
    n = len(y)

    ci_mult = stats.t.ppf(0.975, df=G - 1)
    labels = ["is_host", "rolling_avg"]
    result = {
        "model": "M1: Country FE",
        "n_obs": n,
        "n_countries": G,
        "r2_within": round(r2, 4),
        "coefs": {},
    }

    for i, label in enumerate(labels):
        p = p_val[i]
        stars = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
        result["coefs"][label] = {
            "coef":  round(coef[i], 4),
            "se":    round(se[i], 4),
            "t":     round(t_stat[i], 3),
            "p":     round(p, 4),
            "ci_lo": round(coef[i] - ci_mult * se[i], 4),
            "ci_hi": round(coef[i] + ci_mult * se[i], 4),
            "sig":   stars,
        }

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 3. Run M1
# ══════════════════════════════════════════════════════════════════════════════

m1 = run_model(df_reg)


# ══════════════════════════════════════════════════════════════════════════════
# 4. Print results table (with confidence intervals)
# ══════════════════════════════════════════════════════════════════════════════

def print_results(m: dict) -> None:
    SEP = "─" * 56
    print(f"\n{'HOST COUNTRY EFFECT — WINTER OLYMPICS MEDAL SHARE':^56}")
    print(f"{'M1: Country Fixed Effects':^56}")
    print(SEP)
    print(f"{'Dependent variable: medal_share (% of total medals)':^56}")
    print(SEP)

    var_labels = {
        "is_host":     "Host country (b1)",
        "rolling_avg": "3-game rolling avg (b2)",
    }
    for var, label in var_labels.items():
        c = m["coefs"][var]
        print(f"  {label:<26}  {c['coef']:>8.4f} {c['sig']:<3}")
        print(f"  {'':26}  {'(' + str(c['se']) + ')':>9}")
        print(f"  {'':26}  [{c['ci_lo']}, {c['ci_hi']}]")
        print()

    print(SEP)
    print(f"  Observations : {m['n_obs']}")
    print(f"  Countries    : {m['n_countries']}")
    print(f"  R2 (within)  : {m['r2_within']}")
    print(SEP)
    print("  Significance: *** p<0.01  ** p<0.05  * p<0.1")
    print("  Standard errors (in parentheses) clustered at country level")
    print("  95% confidence intervals in brackets (t-dist, G-1 df)")
    print(SEP)


print_results(m1)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Save detailed results to CSV
# ══════════════════════════════════════════════════════════════════════════════

rows = []
for var, d in m1["coefs"].items():
    rows.append({
        "model":        m1["model"],
        "variable":     var,
        "coefficient":  d["coef"],
        "std_error":    d["se"],
        "t_statistic":  d["t"],
        "p_value":      d["p"],
        "ci_lower":     d["ci_lo"],
        "ci_upper":     d["ci_hi"],
        "significance": d["sig"],
        "n_obs":        m1["n_obs"],
        "n_countries":  m1["n_countries"],
        "r2_within":    m1["r2_within"],
    })

results_df = pd.DataFrame(rows)
results_df.to_csv(OUT_CSV, index=False)
print(f"\nDetailed results saved to {OUT_CSV.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Visualisation — Host uplift per country (actual vs rolling baseline)
# ══════════════════════════════════════════════════════════════════════════════

host_obs = df_reg[df_reg["is_host"] == 1][
    ["Year", "Country_ISO3", "rolling_avg", "medal_share"]
].copy()
host_obs["uplift"] = host_obs["medal_share"] - host_obs["rolling_avg"]
host_obs = host_obs.sort_values("Year").reset_index(drop=True)
host_obs["label"] = host_obs["Country_ISO3"] + "\n" + host_obs["Year"].astype(str)

mean_uplift = host_obs["uplift"].mean()

n = len(host_obs)
fig, ax = plt.subplots(figsize=(max(9, n * 0.75), 4.8))
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

bar_colors = ["#185FA5" if u >= 0 else "#A32D2D" for u in host_obs["uplift"]]
bars = ax.bar(range(n), host_obs["uplift"], color=bar_colors, width=0.6, zorder=2)

for bar, val in zip(bars, host_obs["uplift"]):
    va = "bottom" if val >= 0 else "top"
    offset = 0.08 if val >= 0 else -0.08
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        val + offset,
        f"{val:+.1f}",
        ha="center", va=va, fontsize=7.5, color="#2C2C2A",
    )

ax.axhline(mean_uplift, color="#854F0B", linewidth=1.2, linestyle="--", zorder=3)
ax.axhline(0, color="#888780", linewidth=0.8, zorder=1)

ax.set_xticks(range(n))
ax.set_xticklabels(host_obs["label"], fontsize=8)
ax.set_ylabel("Uplift vs. 3-game rolling average (pp)", fontsize=9)
ax.set_title(
    "H1 - Medal share uplift for host nations\n"
    "(actual share minus 3-game rolling average baseline)",
    fontsize=10, fontweight="normal", pad=10,
)

pos_patch = mpatches.Patch(color="#185FA5", label="Positive uplift")
neg_patch = mpatches.Patch(color="#A32D2D", label="Negative / no uplift")
mean_line = plt.Line2D([0], [0], color="#854F0B", linestyle="--", linewidth=1.2,
                       label=f"Mean uplift: {mean_uplift:+.2f} pp")
ax.legend(handles=[pos_patch, neg_patch, mean_line], fontsize=8.5, frameon=False)

ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#B4B2A9")
ax.tick_params(colors="#5F5E5A")

plt.tight_layout()
fig.savefig(OUT_UPLIFT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Host uplift chart saved to {OUT_UPLIFT.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 8. Descriptive summary
# ══════════════════════════════════════════════════════════════════════════════

print("\n-- Descriptive: medal share for host nations -------------------------")
display = host_obs[["Year", "Country_ISO3", "rolling_avg", "medal_share", "uplift"]].copy()
display.columns = ["Year", "NOC", "Rolling Avg", "Actual Share", "Uplift (pp)"]
print(display.round(2).to_string(index=False))
print(f"\nMean uplift  : {host_obs['uplift'].mean():+.2f} pp")
print(f"Median uplift: {host_obs['uplift'].median():+.2f} pp")
print(f"% positive   : {(host_obs['uplift'] > 0).mean() * 100:.0f}%")
