"""
DiD analysis pipeline (Steps 2 & 3) — Subjective vs Objective only

Inputs expected (from Step 1):
- master_did.csv (built from olympedia_medals_all.csv, sport_pairs_categorized.csv,
  and winter_olympics_hosts_integrated.csv)

Outputs created:
- panel_agg.csv
    NOC × Year × Category panel with medal/point totals and shares

- did_did_summary_full.txt
    Full statsmodels DiD output (all coefficients incl. fixed effects + diagnostics)
- did_did_summary.txt
    Compact DiD table (key terms only) in a publication-style layout

- event_study_model_summary_full.txt
    Full statsmodels stacked event-study output (all coefficients + diagnostics)
- event_study_model_summary.txt
    Compact event-study table (host-at-k=0 plus subjective lead/lag increments)

- event_study_subjective.png
    Event-study plot for incremental host effect in subjective sports vs objective baseline

How to run:
$ python H2_analysis_and_visualization.py

Notes:
- Objective sports are treated as the baseline category.
- Standard errors are clustered at the country (NOC) level.
""" 

import os
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from pathlib import Path

# =========================
# Config (edit as needed)
# =========================
FN_MASTER = "master_did.csv"  # produced by Step 1
FN_PANEL = "panel_agg.csv"

# Choose "share_points" (Gold=3, Silver=2, Bronze=1) or "share_medals" (each medal=1)
OUTCOME_COL = "share_points"

# Event-study window in Olympic cycles (k)
K_MIN, K_MAX = -3, 3
REF_K = -1  # reference period for event-study (last pre-host Games)

# Plot style
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False})


# =========================
# Utilities
# =========================

# =========================
# Formatting helpers (compact OLS tables to .txt)
# =========================
from datetime import datetime

def _fmt_num(x, width=None, prec=4):
    try:
        if x is None:
            s = ""
        elif isinstance(x, (int,)):
            s = str(x)
        else:
            s = f"{float(x):.{prec}f}"
    except Exception:
        s = str(x) if x is not None else ""
    return s.rjust(width) if width else s

def _fmt_sci(x, width=None):
    try:
        s = f"{float(x):.2e}"
    except Exception:
        s = str(x)
    return s.rjust(width) if width else s

def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None

def _now_date_time():
    now = datetime.now()
    # Match the style shown in the user's tables
    date_str = now.strftime("%a, %d %b %Y")
    time_str = now.strftime("%H:%M:%S")
    return date_str, time_str

def _line(char='=', n=50):
    return char * n

def _two_col(left, right, width=78):
    # left and right already formatted strings
    # pad left to split
    left = left.rstrip()
    right = right.rstrip()
    if len(left) + len(right) + 1 > width:
        return left + " " + right
    return left + " " * (width - len(left) - len(right)) + right

def format_did_table(model, dep_var_label="Medal_Share"):
    """Create a compact DiD OLS table matching the requested layout."""
    date_str, time_str = _now_date_time()

    # stats
    r2 = getattr(model, 'rsquared', None)
    ar2 = getattr(model, 'rsquared_adj', None)
    fval = getattr(model, 'fvalue', None)
    fpv = getattr(model, 'f_pvalue', None)
    llf = getattr(model, 'llf', None)
    nobs = getattr(model, 'nobs', None)
    aic = getattr(model, 'aic', None)
    bic = getattr(model, 'bic', None)
    df_resid = getattr(model, 'df_resid', None)
    df_model = getattr(model, 'df_model', None)
    cov_type = getattr(model, 'cov_type', None)

    # coefficients
    params = model.params
    bse = model.bse
    pvals = model.pvalues

    def row(term, label=None):
        label = label or term
        coef = _safe_float(params.get(term, None))
        se = _safe_float(bse.get(term, None))
        pv = _safe_float(pvals.get(term, None))
        z = coef / se if (coef is not None and se not in (None, 0)) else None
        return (label, coef, se, z, pv)

    rows = [
        row('Intercept', 'Intercept'),
        row('is_host', 'is_host'),
        row('is_host:subjective', 'is_host:subjective')
    ]

    out = []
    out.append(_line('=', 50))
    out.append('--- DIFFERENCE-IN-DIFFERENCES ANALYSIS (OLS) ---')
    out.append(_line('=', 50))
    out.append('                            OLS Regression Results                            ')
    out.append(_line('=', 78))
    out.append(_two_col(f"Dep. Variable:              {dep_var_label}", f"R-squared:                       {_fmt_num(r2, prec=3).strip()}"))
    out.append(_two_col("Model:                            OLS", f"Adj. R-squared:                  {_fmt_num(ar2, prec=3).strip()}"))
    out.append(_two_col("Method:                 Least Squares", f"F-statistic:                     {_fmt_num(fval, prec=2).strip()}"))
    # p-value: scientific notation
    fpv_str = _fmt_sci(fpv).strip() if fpv is not None else ""
    out.append(_two_col(f"Date:                {date_str}", f"Prob (F-statistic):           {fpv_str}"))
    out.append(_two_col(f"Time:                        {time_str}", f"Log-Likelihood:                 {_fmt_num(llf, prec=2).strip()}"))
    out.append(_two_col(f"No. Observations:                 {int(nobs) if nobs is not None else ''}", f"AIC:                           {(_fmt_num(aic, prec=0).strip() if aic is not None else '')}"))
    out.append(_two_col(f"Df Residuals:                     {int(df_resid) if df_resid is not None else ''}", f"BIC:                           {(_fmt_num(bic, prec=0).strip() if bic is not None else '')}"))
    out.append(_two_col(f"Df Model:                          {int(round(df_model)) if df_model is not None else ''}", ""))
    out.append(_two_col(f"Covariance Type:               {cov_type if cov_type is not None else ''}", ""))
    out.append(_line('=', 78))
    out.append('                                   coef    std err          z      P>|z|     ')
    out.append(_line('-', 78))

    for lab, coef, se, z, pv in rows:
        coef_s = _fmt_num(coef, prec=4)
        se_s = _fmt_num(se, prec=3)
        z_s = _fmt_num(z, prec=3)
        pv_s = _fmt_num(pv, prec=3)
        out.append(f"{lab:<32}{coef_s:>10}  {se_s:>9}  {z_s:>9}  {pv_s:>9}")

    out.append(_line('=', 78))
    out.append('Notes:')
    out.append('[1] Country and year fixed effects included.')
    out.append('[2] Standard errors clustered at the country (NOC) level.')
    out.append('[3] Objective sports are the baseline category.')
    out.append('[4] is_host captures the host advantage in objective sports.')
    out.append('[5] is_host:subjective captures the incremental host advantage')
    out.append('    in subjectively judged sports relative to objective sports.')
    out.append(_line('=', 78))
    return "\n".join(out) + "\n"


def format_event_study_table(model, dep_var_label="Medal_Share", ref_k=-1, k_list=None):
    """Create a compact stacked event-study OLS table matching the requested layout."""
    date_str, time_str = _now_date_time()

    k_list = k_list if k_list is not None else [-3, -2, 0, 1, 2, 3]

    # stats
    r2 = getattr(model, 'rsquared', None)
    ar2 = getattr(model, 'rsquared_adj', None)
    fval = getattr(model, 'fvalue', None)
    fpv = getattr(model, 'f_pvalue', None)
    llf = getattr(model, 'llf', None)
    nobs = getattr(model, 'nobs', None)
    aic = getattr(model, 'aic', None)
    bic = getattr(model, 'bic', None)
    df_resid = getattr(model, 'df_resid', None)
    df_model = getattr(model, 'df_model', None)
    cov_type = getattr(model, 'cov_type', None)

    params = model.params
    bse = model.bse
    pvals = model.pvalues

    def find_term(patterns):
        # patterns: list of substrings that must all appear
        for t in params.index:
            ok = True
            for p in patterns:
                if p not in t:
                    ok = False
                    break
            if ok:
                return t
        return None

    def build_row(term, label):
        if term is None or term not in params.index:
            return (label, None, None, None, None)
        coef = _safe_float(params[term])
        se = _safe_float(bse[term])
        pv = _safe_float(pvals[term])
        z = coef / se if (coef is not None and se not in (None, 0)) else None
        return (label, coef, se, z, pv)

    # Main host-at-k=0 effect for objective baseline
    t_main0 = find_term(["is_host_event", "[T.0]", "C(k"])
    # Ensure it's not the subjective interaction
    if t_main0 and (":subjective" in t_main0 or ":subj" in t_main0):
        # find non-subjective one
        for t in params.index:
            if ("is_host_event" in t) and ("[T.0]" in t) and ("C(k" in t) and (":subjective" not in t):
                t_main0 = t
                break

    rows = []
    rows.append(build_row(t_main0, "is_host_event:C(k)[T.0]"))

    # Subjective incremental effects
    for k in k_list:
        t_sub = find_term(["is_host_event", f"[T.{k}]", "C(k", ":subjective"])
        rows.append(build_row(t_sub, f"is_host_event:C(k)[T.{k}]:subj"))

    out = []
    out.append(_line('=', 50))
    out.append('--- EVENT-STUDY ANALYSIS (STACKED DiD, OLS) ---')
    out.append(_line('=', 50))
    out.append('                            OLS Regression Results                            ')
    out.append(_line('=', 78))
    out.append(_two_col(f"Dep. Variable:              {dep_var_label}", f"R-squared:                       {_fmt_num(r2, prec=3).strip()}"))
    out.append(_two_col("Model:                            OLS", f"Adj. R-squared:                  {_fmt_num(ar2, prec=3).strip()}"))
    out.append(_two_col("Method:                 Least Squares", f"F-statistic:                 {_fmt_sci(fval).strip() if fval is not None else ''}"))
    fpv_str = _fmt_sci(fpv).strip() if fpv is not None else ""
    out.append(_two_col(f"Date:                {date_str}", f"Prob (F-statistic):          {fpv_str}"))
    out.append(_two_col(f"Time:                        {time_str}", f"Log-Likelihood:                {_fmt_num(llf, prec=1).strip()}"))
    # AIC/BIC: statsmodels sometimes uses sci; keep compact
    aic_s = _fmt_num(aic, prec=0).strip() if aic is not None else ""
    bic_s = _fmt_num(bic, prec=0).strip() if bic is not None else ""
    out.append(_two_col(f"No. Observations:                {int(nobs) if nobs is not None else ''}", f"AIC:                        {aic_s}"))
    out.append(_two_col(f"Df Residuals:                    {int(df_resid) if df_resid is not None else ''}", f"BIC:                        {bic_s}"))
    out.append(_two_col(f"Df Model:                          {int(round(df_model)) if df_model is not None else ''}", ""))
    out.append(_two_col(f"Covariance Type:               {cov_type if cov_type is not None else ''}", ""))
    out.append(_line('=', 78))
    out.append('                                   coef    std err          z      P>|z|     ')
    out.append(_line('-', 78))

    # first row then blank line
    for i, (lab, coef, se, z, pv) in enumerate(rows):
        coef_s = _fmt_num(coef, prec=4)
        se_s = _fmt_num(se, prec=3)
        z_s = _fmt_num(z, prec=3)
        pv_s = _fmt_num(pv, prec=3)
        out.append(f"{lab:<32}{coef_s:>10}  {se_s:>9}  {z_s:>9}  {pv_s:>9}")
        if i == 0:
            out.append("")

    out.append(_line('=', 78))
    out.append('Notes:')
    out.append('[1] Event time k measured in Olympic cycles relative to host year.')
    out.append(f'[2] Reference period: k = {ref_k}.')
    out.append('[3] Coefficients with suffix \' :subj\' denote incremental host effects')
    out.append('    in subjectively judged sports relative to objectively scored sports.')
    out.append('[4] Country and year fixed effects included.')
    out.append('[5] Standard errors clustered at the country (NOC) level.')
    out.append(_line('=', 78))
    return "\n".join(out) + "\n"

def read_csv_safely(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        sys.exit(f"[ERROR] File not found: {path}")
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.read_csv(p, encoding="utf-8-sig")


def ensure_required(df: pd.DataFrame, cols: set, name: str):
    missing = cols - set(df.columns)
    if missing:
        sys.exit(f"[ERROR] {name} missing columns: {missing}")


# =========================
# STEP 2: BUILD PANEL & DiD (subjective vs objective)
# =========================
def build_panel_and_run_did(fn_master: str, fn_panel_out: str, outcome_col: str) -> pd.DataFrame:
    print("\n[Step 2] Building panel & running DiD (subjective vs objective)…")

    master = read_csv_safely(fn_master)
    need_master_cols = {"Jahr", "NOC", "Sport", "Event", "category",
                        "is_host", "medal_numeric", "Host_NOC"}
    ensure_required(master, need_master_cols, fn_master)

    # 2.1 Aggregate medals to NOC × Year × Category
    tmp = (
        master
        .assign(
            medal_one=1,
            category=lambda d: d["category"].astype(str).str.lower().str.strip()
        )
        .groupby(["NOC", "Jahr", "category"], as_index=False)
        .agg(
            medals=("medal_one", "sum"),
            points=("medal_numeric", "sum")
        )
    )

    # Totals by Year × Category to compute shares
    totals = (
        tmp.groupby(["Jahr", "category"], as_index=False)
           .agg(total_medals=("medals", "sum"),
                total_points=("points", "sum"))
    )

    panel = tmp.merge(totals, on=["Jahr", "category"], how="left", validate="m:1")

    # Keep only objective and subjective categories
    panel = panel[panel["category"].isin(["objective", "subjective"])].copy()

    panel["share_medals"] = panel["medals"] / panel["total_medals"]
    panel["share_points"] = panel["points"] / panel["total_points"]

    # 2.2 Host mapping: one host NOC per Olympic year (from Step 1 master file)
    host_per_year = (
        master[["Jahr", "Host_NOC"]]
        .drop_duplicates()
        .rename(columns={"Host_NOC": "Host_NOC_year"})
    )
    panel = panel.merge(host_per_year, on="Jahr", how="left", validate="m:1")

    # 2.3 Flags
    panel["is_host"] = (panel["NOC"] == panel["Host_NOC_year"]).astype("int8")

    panel["subjective"] = (panel["category"] == "subjective").astype("int8")

    if outcome_col not in panel.columns:
        sys.exit(f"[ERROR] Outcome column '{outcome_col}' not found in panel.")
    panel["outcome"] = panel[outcome_col].astype(float)

    # 2.4 Save the panel
    panel.sort_values(["Jahr", "NOC", "category"]).to_csv(fn_panel_out, index=False, encoding="utf-8")
    print(f"[OK] Wrote panel: {fn_panel_out}")

    # 2.5 DiD with heterogeneity by judging type
    # Objective is the omitted baseline category.
    # Coefficient interpretation (objective = baseline category):
    # - is_host captures the host advantage in objective sports.
    # - is_host:subjective captures the *incremental* host advantage in subjectively judged sports.
    
    formula = (
        "outcome ~ "
        "is_host + "
        "subjective + "
        "is_host:subjective + "
        "C(NOC) + C(Jahr)"
    )


    model = smf.ols(formula, data=panel).fit(
        cov_type="cluster",
        cov_kwds={"groups": panel["NOC"]}
    )

    # 2.6 Save results
    # Write the full statsmodels summary (all coefficients incl. FE + diagnostics)
    with open("did_did_summary_full.txt", "w", encoding="utf-8") as f:
            f.write(model.summary().as_text())
    # Short, publication-style table
    with open("did_did_summary.txt", "w", encoding="utf-8") as f:
            f.write(format_did_table(model, dep_var_label="Medal_Share"))
    print("[OK] Wrote regression summary: did_did_summary.txt")

    coef_table = (
        model.summary2().tables[1]
        .reset_index()
        .rename(columns={
            "index": "term",
            "Coef.": "coef",
            "Std.Err.": "std_err",
            "P>|t|": "p_value",
            "[0.025": "ci_low",
            "0.975]": "ci_high",
        })
    )

    # coef_table.to_csv("did_did_coeffs.csv", index=False, encoding="utf-8")
    # print("[OK] Wrote tidy coefficients: did_did_coeffs.csv")

    # 2.7 Print key terms
    print("\n=== Key DiD Effects ===")
    key_terms = ["is_host", "is_host:subjective"]
    for term in key_terms:
        row = coef_table[coef_table["term"].str.replace(" ", "", regex=False) == term]
        if not row.empty:
            print(row.to_string(index=False))
        else:
            # fallback fuzzy match
            cand = coef_table[coef_table["term"].str.contains("is_host", regex=False) &
                              coef_table["term"].str.contains(term.split(":")[-1], regex=False)]
            if not cand.empty:
                print(cand.to_string(index=False))
            else:
                print(f"[WARN] Term not found: {term}")

    return panel


# ===================================
# STEP 3: STACKED EVENT-STUDY + PLOTS (subjective vs objective)
# ===================================
def event_study_and_plots(panel: pd.DataFrame, outcome_col: str,
                          k_min: int, k_max: int, ref_k: int) -> None:
    print("\n[Step 3] Building stacked event-study & plots (subjective vs objective)…")

    panel = panel.copy()
    panel["category"] = panel["category"].astype(str).str.lower().str.strip()

    # Ensure we only have objective and subjective
    panel = panel[panel["category"].isin(["objective", "subjective"])].copy()
    panel["subjective"] = (panel["category"] == "subjective").astype("int8")

    if outcome_col not in panel.columns:
        sys.exit(f"[ERROR] Outcome column '{outcome_col}' not found in panel.")
    panel["outcome"] = panel[outcome_col].astype(float)

    # 3.1 Olympic index (0..T) for event time in Olympic cycles
    years_sorted = np.sort(panel["Jahr"].unique())
    year_to_idx = {y: i for i, y in enumerate(years_sorted)}
    panel["olym_idx"] = panel["Jahr"].map(year_to_idx)

    # Identify host events (each host year per host NOC)
    host_events = (
        panel.loc[panel["is_host"] == 1, ["NOC", "Jahr"]]
        .drop_duplicates()
        .rename(columns={"NOC": "host_noc", "Jahr": "host_year"})
    )
    if host_events.empty:
        sys.exit("[ERROR] No host events detected. Check host mapping in Step 1.")

    # 3.2 Build a stacked dataset: replicate the panel once per host event and compute event time k
    stacked_list = []
    for _, row in host_events.iterrows():
        h_noc, h_year = row["host_noc"], row["host_year"]
        h_idx = year_to_idx[h_year]

        tmp = panel.copy()
        tmp["event_host_noc"] = h_noc
        tmp["event_host_year"] = h_year
        tmp["k"] = tmp["olym_idx"] - h_idx
        tmp["is_host_event"] = (tmp["NOC"] == h_noc).astype("int8")

        tmp = tmp[(tmp["k"] >= k_min) & (tmp["k"] <= k_max)]
        stacked_list.append(tmp)

    stacked = pd.concat(stacked_list, ignore_index=True)

    # Ensure the reference period exists; if not, fall back to the closest available pre-host period
    ks = sorted(stacked["k"].unique())
    if ref_k not in ks:
        neg_ks = [x for x in ks if x < 0]
        ref_k = max(neg_ks) if neg_ks else ks[0]
        print(f"[WARN] REF_K not in data; using {ref_k} as reference.")

    stacked["k"] = pd.Categorical(stacked["k"], categories=ks, ordered=True)

    # 3.3 Estimate stacked event-study with two-way fixed effects and clustered SEs
    # Objective is the baseline; ':subjective' terms capture incremental effects in subjective sports
    formula_es = (
        f"outcome ~ is_host_event * C(k, Treatment(reference={ref_k})) * subjective + "
        "C(NOC) + C(Jahr)"
    )

    es_mod = smf.ols(formula_es, data=stacked).fit(
        cov_type="cluster",
        cov_kwds={"groups": stacked["NOC"]}
    )

    # Write the full statsmodels summary (all coefficients incl. FE + diagnostics)
    with open("event_study_model_summary_full.txt", "w", encoding="utf-8") as f:
            f.write(es_mod.summary().as_text())
    # Short, publication-style table
    with open("event_study_model_summary.txt", "w", encoding="utf-8") as f:
            f.write(format_event_study_table(es_mod, dep_var_label="Medal_Share", ref_k=ref_k, k_list=[k for k in range(k_min, k_max+1) if k != ref_k]))
    print("[OK] Wrote model summary: event_study_model_summary.txt")

    # 3.4 Extract tidy profile for plotting
    def extract_profile(model, label_keyword: str, ref_k_value: int) -> pd.DataFrame:
        summ = model.summary2().tables[1].reset_index()
        summ = summ.rename(columns={
            "index": "term",
            "Coef.": "coef",
            "Std.Err.": "std_err",
            "P>|z|": "p_value",
            "[0.025": "ci_low",
            "0.975]": "ci_high",
        })

        mask = (
            summ["term"].str.contains("is_host_event", regex=False)
            & summ["term"].str.contains("C(k", regex=False)
            & summ["term"].str.contains(label_keyword, regex=False)
        )

        prof = summ.loc[mask, ["term", "coef", "std_err", "ci_low", "ci_high", "p_value"]].copy()

        def parse_k(t: str):
            # term looks like: is_host_event:C(k, Treatment(reference=-1))[T.0]:subjective
            if "T." in t:
                after_T = t.split("T.", 1)[1]
                k_str = after_T.split("]", 1)[0]
                try:
                    return int(k_str)
                except Exception:
                    try:
                        return float(k_str)
                    except Exception:
                        return None
            return None

        prof["k"] = prof["term"].apply(parse_k)
        prof = prof.dropna(subset=["k"]).sort_values("k")

        # add normalized reference point
        prof = pd.concat([
            pd.DataFrame({"k": [ref_k_value], "coef": [0.0], "std_err": [np.nan],
                          "ci_low": [np.nan], "ci_high": [np.nan], "p_value": [np.nan]}),
            prof
        ], ignore_index=True).sort_values("k").reset_index(drop=True)

        return prof

    prof_subj = extract_profile(es_mod, "subjective", ref_k)
    #prof_subj.to_csv("event_study_subjective_coeffs.csv", index=False, encoding="utf-8")
    #print("[OK] Wrote event-study CSV: event_study_subjective_coeffs.csv")

    # 3.5 Plot
    def plot_profile(df: pd.DataFrame, title: str, outfile: str):
        plt.figure(figsize=(8.0, 5.0), dpi=140)

        df = df.copy()
        df["k"] = pd.to_numeric(df["k"], errors="coerce")
        df["coef"] = pd.to_numeric(df["coef"], errors="coerce")
        df["ci_low"] = pd.to_numeric(df["ci_low"], errors="coerce")
        df["ci_high"] = pd.to_numeric(df["ci_high"], errors="coerce")

        df = df.dropna(subset=["k"])
        df_ci = df.dropna(subset=["ci_low", "ci_high"])

        if not df_ci.empty:
            plt.fill_between(df_ci["k"], df_ci["ci_low"], df_ci["ci_high"],
                             color="#cfe8ff", alpha=0.85, label="95% CI")

        plt.axhline(0, color="#444", lw=1, ls="--", alpha=0.7)
        if 0 in df["k"].values:
            plt.axvline(0, color="#888", lw=1, ls=":", alpha=0.8)

        plt.plot(df["k"], df["coef"], color="#005bbb", marker="o", lw=2, label="Estimate")

        plt.title(title)
        plt.xlabel("Event time (Olympics relative to host)")
        ylabel = "Effect on medal share (points)" if outcome_col == "share_points" else "Effect on medal share (medals)"
        plt.ylabel(ylabel)

        xticks = sorted(df["k"].unique())
        plt.xticks(xticks, xticks)

        plt.legend(frameon=False)
        plt.tight_layout()
        plt.savefig(outfile)
        plt.close()

    plot_profile(
        prof_subj,
        "Event-study: Incremental host effect in Subjective sports (vs Objective baseline)",
        "event_study_subjective.png"
    )
    print("[OK] Wrote plot: event_study_subjective.png")

    print("\n[Step 3] Done. Check the CSV and PNG for lead/lag patterns and pre-trends.")


# =========================
# Main
# =========================
if __name__ == "__main__":
    panel = build_panel_and_run_did(
        fn_master=FN_MASTER,
        fn_panel_out=FN_PANEL,
        outcome_col=OUTCOME_COL
    )

    event_study_and_plots(
        panel=panel,
        outcome_col=OUTCOME_COL,
        k_min=K_MIN,
        k_max=K_MAX,
        ref_k=REF_K
    )

    print("\n[All done] Outputs saved in the working directory.")
