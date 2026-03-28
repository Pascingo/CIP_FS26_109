
"""
DiD / DDD analysis pipeline (Steps 2 & 3)

Inputs expected (from Step 1):
- master_did.csv  (built from olympedia_medals_all.csv, sport_pairs_categorized.csv,
                   and winter_olympics_hosts_integrated.csv)

Outputs created:
- panel_agg.csv                         (NOC × Year × Category panel with shares)
- did_ddd_summary.txt                   (DDD regression text summary)
- did_ddd_coeffs.csv                    (tidy coefficient table with SEs & p-values)
- event_study_subjective_coeffs.csv     (lead/lag table for subjective)
- event_study_mixed_coeffs.csv          (lead/lag table for mixed)
- event_study_subjective.png            (plot for subjective)
- event_study_mixed.png                 (plot for mixed)
- event_study_model_summary.txt         (stacked event-study model summary)

How to run:
$ python did_analysis.py
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
FN_MASTER = "master_did.csv"   # produced by Step 1
FN_PANEL  = "panel_agg.csv"

# Main outcome for analysis (matches Step 2/3 code)
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
# STEP 2: BUILD PANEL & DDD
# =========================
def build_panel_and_run_ddd(fn_master: str, fn_panel_out: str, outcome_col: str):
    print("\n[Step 2] Building panel & running DDD…")

    master = read_csv_safely(fn_master)
    need_master_cols = {"Jahr", "NOC", "Sport", "Event", "category",
                        "is_host", "medal_numeric", "Host_NOC"}
    ensure_required(master, need_master_cols, "master_did.csv")

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
    panel["share_medals"] = panel["medals"] / panel["total_medals"]
    panel["share_points"] = panel["points"] / panel["total_points"]

    # 2.2 Bring in host NOC per year directly from master
    host_per_year = (
        master[["Jahr", "Host_NOC"]]
        .drop_duplicates()
        .rename(columns={"Host_NOC": "Host_NOC_year"})
    )
    panel = panel.merge(host_per_year, on="Jahr", how="left", validate="m:1")

    # 2.3 Flags and outcome
    panel["is_host"] = (panel["NOC"] == panel["Host_NOC_year"]).astype("int8")
    # "post" is 1 in host year for everyone (the host shock year),
    # we will rely on Year FE to absorb common shocks. For standard 2×2 DiD,
    # post-by-is_host captures the increment in the host year.
    panel["post"] = (panel["Host_NOC_year"].notna()).astype("int8")

    panel["category"] = panel["category"].str.lower().str.strip()
    panel["subjective"] = (panel["category"] == "subjective").astype("int8")
    panel["mixed"]      = (panel["category"] == "mixed").astype("int8")
    panel["objective"]  = (panel["category"] == "objective").astype("int8")

    if outcome_col not in panel.columns:
        sys.exit(f"[ERROR] Outcome column '{outcome_col}' not found in panel.")
    panel["outcome"] = panel[outcome_col].astype(float)

    # 2.4 Save the panel (for transparency & review)
    panel.sort_values(["Jahr", "NOC", "category"]).to_csv(fn_panel_out, index=False, encoding="utf-8")
    print(f"[OK] Wrote panel: {fn_panel_out}")

    # 2.5 Run DDD with NOC and Year FE; Objective is the omitted baseline
    # Model: outcome ~ is_host*post*subjective + is_host*post*mixed + C(NOC) + C(Jahr)
    formula = (
        "outcome ~ "
        "is_host * post * subjective + "
        "is_host * post * mixed + "
        "C(NOC) + C(Jahr)"
    )
    model = smf.ols(formula, data=panel).fit(cov_type="cluster", cov_kwds={"groups": panel["NOC"]})

    # 2.6 Save results
    with open("did_ddd_summary.txt", "w", encoding="utf-8") as f:
        f.write(model.summary().as_text())
    print("[OK] Wrote regression summary: did_ddd_summary.txt")

    coef_table = (
        model.summary2().tables[1]
        .reset_index()
        .rename(columns={"index": "term", "Coef.": "coef", "Std.Err.": "std_err",
                         "P>|t|": "p_value", "[0.025": "ci_low", "0.975]": "ci_high"})
    )
    coef_table.to_csv("did_ddd_coeffs.csv", index=False, encoding="utf-8")
    print("[OK] Wrote tidy coefficients: did_ddd_coeffs.csv")

    # 2.7 Print key triple interactions for quick glance
    print("\n=== Key DDD Effects (host × post × category) ===")
    for term in ["is_host:post:subjective", "is_host:post:mixed"]:
        row = coef_table[coef_table["term"].str.replace(" ", "") == term.replace(" ", "")]
        if not row.empty:
            print(row.to_string(index=False))
        else:
            candidates = coef_table[coef_table["term"].str.contains("is_host") &
                                    coef_table["term"].str.contains("post") &
                                    coef_table["term"].str.contains(term.split(":")[-1])]
            if not candidates.empty:
                print(candidates.to_string(index=False))
            else:
                print(f"[WARN] Term not found: {term}")

    return panel


# ===================================
# STEP 3: STACKED EVENT-STUDY + PLOTS
# ===================================
def event_study_and_plots(panel: pd.DataFrame, outcome_col: str,
                          k_min: int, k_max: int, ref_k: int):
    print("\n[Step 3] Building stacked event-study & plots…")

    # Normalize
    panel = panel.copy()
    panel["category"] = panel["category"].str.lower().str.strip()
    panel["subjective"] = (panel["category"] == "subjective").astype("int8")
    panel["mixed"]      = (panel["category"] == "mixed").astype("int8")
    panel["objective"]  = (panel["category"] == "objective").astype("int8")

    if outcome_col not in panel.columns:
        sys.exit(f"[ERROR] Outcome column '{outcome_col}' not found in panel.")
    panel["outcome"] = panel[outcome_col].astype(float)

    # 3.1 Olympic index (0..T) to define event time in Olympic cycles
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

    # 3.2 Build stacked dataset across all host events
    stacked_list = []
    for _, row in host_events.iterrows():
        h_noc, h_year = row["host_noc"], row["host_year"]
        h_idx = year_to_idx[h_year]

        tmp = panel.copy()
        tmp["event_host_noc"]  = h_noc
        tmp["event_host_year"] = h_year
        tmp["k"] = tmp["olym_idx"] - h_idx
        tmp["is_host_event"] = (tmp["NOC"] == h_noc).astype("int8")

        tmp = tmp[(tmp["k"] >= k_min) & (tmp["k"] <= k_max)]
        stacked_list.append(tmp)

    stacked = pd.concat(stacked_list, ignore_index=True)

    # Ensure reference period exists; if not, fall back to closest pre
    ks = sorted(stacked["k"].unique())
    if ref_k not in ks:
        neg_ks = [x for x in ks if x < 0]
        ref_k = max(neg_ks) if neg_ks else ks[0]
        print(f"[WARN] REF_K not in data; using {ref_k} as reference.")

    stacked["k"] = pd.Categorical(stacked["k"], categories=ks, ordered=True)

    # 3.3 Estimate stacked event-study with FE and clustered SEs
    # Objective baseline; interactions for subjective and mixed
    formula_es = (
        f"outcome ~ is_host_event * C(k, Treatment(reference={ref_k})) * subjective + "
        f"is_host_event * C(k, Treatment(reference={ref_k})) * mixed + "
        "C(NOC) + C(Jahr)"
    )
    es_mod = smf.ols(formula_es, data=stacked).fit(
        cov_type="cluster", cov_kwds={"groups": stacked["NOC"]}
    )

    # Save summary
    with open("event_study_model_summary.txt", "w", encoding="utf-8") as f:
        f.write(es_mod.summary().as_text())
    print("[OK] Wrote model summary: event_study_model_summary.txt")

    # 3.4 Extract tidy profiles for plotting
    def extract_profile(model, label_keyword, ref_k_value):
        summ = model.summary2().tables[1].reset_index()
        summ = summ.rename(columns={
            "index":"term",
            "Coef.":"coef",
            "Std.Err.":"std_err",
            "P>|z|":"p_value",
            "[0.025":"ci_low",
            "0.975]":"ci_high"
        })

        # SAFE string matching (regex=False)
        mask = (
            summ["term"].str.contains("is_host_event", regex=False)
            & summ["term"].str.contains("C(k", regex=False)
            & summ["term"].str.contains(label_keyword, regex=False)
        )

        prof = summ.loc[mask, ["term","coef","std_err","ci_low","ci_high","p_value"]].copy()

        def parse_k(t):
            if "T." in t:
                after_T = t.split("T.", 1)[1]
                k_str = after_T.split("]", 1)[0]
                try:
                    return int(k_str)
                except:
                    try:
                        return float(k_str)
                    except:
                        return None
            return None

        prof["k"] = prof["term"].apply(parse_k)
        prof = prof.dropna(subset=["k"]).sort_values("k")

        # add the normalized reference
        prof = pd.concat([
            pd.DataFrame({"k":[ref_k_value], "coef":[0.0], "std_err":[None],
                        "ci_low":[None], "ci_high":[None], "p_value":[None]}),
            prof
        ], ignore_index=True).sort_values("k").reset_index(drop=True)

        return prof

    prof_subj = extract_profile(es_mod, "subjective", ref_k)
    prof_mix  = extract_profile(es_mod, "mixed",      ref_k)

    prof_subj.to_csv("event_study_subjective_coeffs.csv", index=False, encoding="utf-8")
    prof_mix.to_csv("event_study_mixed_coeffs.csv", index=False, encoding="utf-8")
    print("[OK] Wrote event-study CSVs: event_study_subjective_coeffs.csv, event_study_mixed_coeffs.csv")

    # 3.5 Plots
    def plot_profile(df: pd.DataFrame, title: str, outfile: str):
        plt.figure(figsize=(8.0, 5.0), dpi=140)

        # Ensure numeric types
        df = df.copy()
        df["k"] = pd.to_numeric(df["k"], errors="coerce")
        df["coef"] = pd.to_numeric(df["coef"], errors="coerce")
        df["ci_low"] = pd.to_numeric(df["ci_low"], errors="coerce")
        df["ci_high"] = pd.to_numeric(df["ci_high"], errors="coerce")

        # Drop rows where k is NaN, because plotting requires numeric
        df = df.dropna(subset=["k"])

        # Confidence band
        df_ci = df.dropna(subset=["ci_low", "ci_high"])
        if not df_ci.empty:
            plt.fill_between(
                df_ci["k"],
                df_ci["ci_low"],
                df_ci["ci_high"],
                color="#cfe8ff",
                alpha=0.85,
                label="95% CI"
            )

        # Zero line + event marker
        plt.axhline(0, color="#444", lw=1, ls="--", alpha=0.7)
        if 0 in df["k"].values:
            plt.axvline(0, color="#888", lw=1, ls=":", alpha=0.8)

        # Main line
        plt.plot(df["k"], df["coef"], color="#005bbb", marker="o", lw=2, label="Estimate")

        plt.title(title)
        plt.xlabel("Event time (Olympics relative to host)")
        plt.ylabel("Effect on medal share (points)")

        xticks = sorted(df["k"].unique())
        plt.xticks(xticks, xticks)

        plt.legend(frameon=False)
        plt.tight_layout()
        plt.savefig(outfile)
        plt.close()

    plot_profile(prof_subj,
                 "Event-study: Host effect in Subjective sports (vs Objective baseline)",
                 "event_study_subjective.png")
    plot_profile(prof_mix,
                 "Event-study: Host effect in Mixed-judged sports (vs Objective baseline)",
                 "event_study_mixed.png")
    print("[OK] Wrote plots: event_study_subjective.png, event_study_mixed.png")

    # Console hint
    print("\n[Step 3] Done. Check the CSVs and PNGs for lead/lag patterns and pre-trends.")


# =========================
# Main
# =========================
if __name__ == "__main__":
    # Step 2: Build panel + DDD
    panel = build_panel_and_run_ddd(
        fn_master=FN_MASTER,
        fn_panel_out=FN_PANEL,
        outcome_col=OUTCOME_COL
    )

    # Step 3: Stacked event-study + plots
    event_study_and_plots(
        panel=panel,
        outcome_col=OUTCOME_COL,
        k_min=K_MIN,
        k_max=K_MAX,
        ref_k=REF_K
    )

    print("\n[All done] Outputs saved in the working directory.")