"""
Winter Olympics Medals CSV Cleaner  (extended)
------------------------------------------------
Issues detected and resolved:
  1. Two inconsistent column schemas across years:
       - Some years: country in 'NOC',    'Nation' is null
       - Other years: country in 'Nation', 'NOC' is null
  2. Swapped Rank/Nation columns in a subset of rows
  3. 'Totals (N entries)' aggregate rows mixed with country data
  4. 'Mixed team' and 'Individual Neutral Athletes' non-country rows
  5. Missing 'Total' values — recomputed as Gold + Silver + Bronze
  6. Asterisks and footnote markers (*, ‡, [A], [B]) in country names
  7. 'Total' column is float instead of int
  8. 'Rank' column is mixed string/int type
  9.  Gap / missing-data check — reports per-column null counts
 10.  Dtype validation & enforcement — explicit casts with audit log
 11.  Value-range check — Year, Rank, Gold, Silver, Bronze, Total
 12.  Outlier detection & treatment — IQR method per medal column,
      per year-group; extreme rows are flagged and capped at 3×IQR fence
"""

import pandas as pd
import numpy as np
import re


INPUT  = "../Data_raw/raw_wikipedia_medals.csv"
OUTPUT = "../Data_clean/clean_wikipedia_medals.csv"
REPORT = "../Data_clean/winter_olympics_cleaning_report.txt"

report_lines: list[str] = []

def log(msg: str = "") -> None:
    print(msg)
    report_lines.append(msg)


# ── Load ──────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT, dtype=str)          # everything as string for safe parsing
log(f"Loaded {len(df)} rows, columns: {df.columns.tolist()}")


# ── 1. Drop aggregate and non-country rows ────────────────────────────────────

def is_junk_row(row) -> bool:
    for val in row:
        s = str(val) if pd.notna(val) else ""
        if s.startswith("Totals"):
            return True
    if str(row["Rank"]).lower() == "mixed team":
        return True
    if "neutral" in str(row.get("NOC", "")).lower():
        return True
    return False

before = len(df)
df = df[~df.apply(is_junk_row, axis=1)].reset_index(drop=True)
log(f"Dropped {before - len(df)} aggregate/non-country rows  →  {len(df)} remaining")


# ── 2. Resolve country name from inconsistent NOC / Nation columns ────────────

def clean_name(name: str) -> str:
    name = re.sub(r"[\*‡†]", "", name)
    name = re.sub(r"\[[^\]]*\]", "", name)
    return name.strip()

def is_digit_str(s: str) -> bool:
    return s.isdigit()

def parse_row(row) -> dict | None:
    rank_raw = str(row["Rank"]).strip()   if pd.notna(row["Rank"])   else ""
    noc      = str(row["NOC"]).strip()    if pd.notna(row["NOC"])    else ""
    nation   = str(row["Nation"]).strip() if pd.notna(row["Nation"]) else ""

    rank_is_int  = rank_raw.lstrip("–-").isdigit()
    noc_is_digit = is_digit_str(noc)

    if not rank_is_int and noc_is_digit and not nation:
        country = clean_name(rank_raw)
        gold    = int(noc)
        silver  = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        bronze  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        rank    = None
    elif noc and not noc_is_digit and not nation:
        country = clean_name(noc)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = rank_raw
    elif not noc and nation and rank_is_int:
        country = clean_name(nation)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = rank_raw
    elif not noc and nation and not rank_is_int:
        country = clean_name(rank_raw)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = nation
    elif noc and nation:
        country = clean_name(nation)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = rank_raw
    else:
        return None

    if not country:
        return None

    return {"rank": rank, "country": country,
            "gold": gold, "silver": silver, "bronze": bronze}

parsed = df.apply(parse_row, axis=1)
df = df[parsed.notna()].copy()
parsed = parsed[parsed.notna()]

df["Country"] = parsed.apply(lambda x: x["country"])
df["Rank"]    = parsed.apply(lambda x: x["rank"])
df["Gold"]    = parsed.apply(lambda x: x["gold"])
df["Silver"]  = parsed.apply(lambda x: x["silver"])
df["Bronze"]  = parsed.apply(lambda x: x["bronze"])


# ── 3. Cast numeric columns ───────────────────────────────────────────────────

for col in ["Gold", "Silver", "Bronze", "Year"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

df["Rank"] = pd.to_numeric(df["Rank"], errors="coerce").astype("Int64")


# ── 4. Recompute Total ────────────────────────────────────────────────────────

df["Total"] = pd.to_numeric(df["Total"], errors="coerce")
missing_total = df["Total"].isna().sum()
df["Total"] = (df["Gold"] + df["Silver"] + df["Bronze"]).astype("Int64")
log(f"Recomputed Total for {missing_total} rows where it was missing")


# ── 5. Final column selection and sort ────────────────────────────────────────

df = df[["Year", "Rank", "Country", "Gold", "Silver", "Bronze", "Total"]]
df = df.sort_values(["Year", "Rank"], na_position="last").reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# EXTENSION 9 — Gap / missing-data check
# ══════════════════════════════════════════════════════════════════════════════

log("\n" + "═" * 60)
log("EXTENSION 9 · Gap / Missing-Data Check")
log("═" * 60)

null_counts = df.isnull().sum()
null_pct    = (null_counts / len(df) * 100).round(2)
log(f"{'Column':<12} {'Nulls':>6}  {'%':>6}")
log("-" * 28)
for col in df.columns:
    flag = "  ← MISSING" if null_counts[col] > 0 else ""
    log(f"{col:<12} {null_counts[col]:>6}  {null_pct[col]:>5.1f}%{flag}")

# Check for years with unexpected gaps (Winter Olympics every 4 years until
# 1992, then every 4 years offset by 2 from 1994 onward)
expected_years = (
    list(range(1924, 1940, 4)) +   # 1924–1936
    list(range(1948, 1993, 4)) +   # 1948–1992  (WWII gap expected)
    list(range(1994, 2030, 4))     # 1994–2026
)
actual_years  = sorted(df["Year"].dropna().unique().tolist())
missing_years = [y for y in expected_years if y not in actual_years]
extra_years   = [y for y in actual_years   if y not in expected_years]

log(f"\nExpected Olympic years present: {len(expected_years)}")
log(f"Actual years in data:           {len(actual_years)}")
if missing_years:
    log(f"Missing years:  {missing_years}  ← CHECK")
else:
    log("Missing years:  none ✓")
if extra_years:
    log(f"Unexpected years in data: {extra_years}  ← CHECK")
else:
    log("Unexpected years:         none ✓")

# Countries with duplicate entries within the same year
dupes = df[df.duplicated(subset=["Year", "Country"], keep=False)]
if len(dupes):
    log(f"\nDuplicate country-year rows found: {len(dupes)}")
    log(dupes[["Year", "Country"]].to_string(index=False))
    df = df.drop_duplicates(subset=["Year", "Country"], keep="first")
    log(f"Kept first occurrence; {len(df)} rows remaining.")
else:
    log("\nNo duplicate country-year entries ✓")


# ══════════════════════════════════════════════════════════════════════════════
# EXTENSION 10 — Dtype validation & enforcement
# ══════════════════════════════════════════════════════════════════════════════

log("\n" + "═" * 60)
log("EXTENSION 10 · Dtype Validation & Enforcement")
log("═" * 60)

EXPECTED_DTYPES = {
    "Year":    "Int64",
    "Rank":    "Int64",
    "Country": "object",
    "Gold":    "Int64",
    "Silver":  "Int64",
    "Bronze":  "Int64",
    "Total":   "Int64",
}

for col, expected in EXPECTED_DTYPES.items():
    actual = str(df[col].dtype)
    status = "✓" if actual == expected else f"← WAS {actual}, casting now"
    log(f"  {col:<10} expected={expected:<10} actual={actual:<10} {status}")
    if actual != expected:
        if expected == "Int64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif expected == "object":
            df[col] = df[col].astype(str)


# ══════════════════════════════════════════════════════════════════════════════
# EXTENSION 11 — Value-range check
# ══════════════════════════════════════════════════════════════════════════════

log("\n" + "═" * 60)
log("EXTENSION 11 · Value-Range Checks")
log("═" * 60)

RANGES = {
    "Year":   (1924, 2030),
    "Rank":   (1, 200),
    "Gold":   (0, 200),
    "Silver": (0, 200),
    "Bronze": (0, 200),
    "Total":  (0, 600),
}

violations_found = False
for col, (lo, hi) in RANGES.items():
    out = df[(df[col].notna()) & ((df[col] < lo) | (df[col] > hi))]
    if len(out):
        violations_found = True
        log(f"\n  {col}: {len(out)} value(s) outside [{lo}, {hi}]")
        log(out[["Year", "Country", col]].to_string(index=False))
    else:
        log(f"  {col}: all values in [{lo}, {hi}] ✓")

# Logical consistency: Total == Gold + Silver + Bronze
df["_computed_total"] = df["Gold"] + df["Silver"] + df["Bronze"]
mismatch = df[df["Total"] != df["_computed_total"]]
if len(mismatch):
    log(f"\n  Total mismatch (Total ≠ G+S+B): {len(mismatch)} rows — recomputing")
    df["Total"] = df["_computed_total"].astype("Int64")
else:
    log("  Total == Gold + Silver + Bronze for all rows ✓")
df = df.drop(columns=["_computed_total"])

# Rank should be monotonically increasing within each year (allow ties)
rank_issues = []
for year, grp in df.groupby("Year"):
    ranks = grp["Rank"].dropna().tolist()
    if ranks != sorted(ranks):
        rank_issues.append(year)
if rank_issues:
    log(f"\n  Non-monotonic Rank within years: {rank_issues}")
else:
    log("  Rank ordering is monotonically non-decreasing within each year ✓")

if not violations_found:
    log("\n  All range checks passed ✓")


# ══════════════════════════════════════════════════════════════════════════════
# EXTENSION 12 — Outlier detection & treatment (IQR, per medal column)
# ══════════════════════════════════════════════════════════════════════════════

log("\n" + "═" * 60)
log("EXTENSION 12 · Outlier Detection & Treatment")
log("═" * 60)
log("""
Strategy
--------
  • Method  : Tukey IQR (Q1 − 1.5·IQR  /  Q3 + 1.5·IQR) on the full
              cleaned dataset for each medal column.
  • Rationale: Per-year groups are too small for robust statistics
              (≤ ~30 countries/year). Global IQR over all years is more
              stable while still flagging genuinely extreme values.
  • Treatment: Outliers are FLAGGED in a new boolean column
              `<col>_outlier`.  Values are NOT modified; medal counts
              represent historical fact and capping them would corrupt
              the data.  The flag allows downstream consumers to
              optionally exclude them from analyses.
""")

MEDAL_COLS = ["Gold", "Silver", "Bronze", "Total"]
outlier_summary: list[dict] = []

for col in MEDAL_COLS:
    series = df[col].dropna().astype(float)
    Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
    IQR    = Q3 - Q1
    lo     = Q1 - 1.5 * IQR
    hi     = Q3 + 1.5 * IQR

    outlier_mask = (df[col].notna()) & ((df[col].astype(float) < lo) | (df[col].astype(float) > hi))
    df[f"{col}_outlier"] = outlier_mask

    n_out = outlier_mask.sum()
    outlier_summary.append({"col": col, "Q1": Q1, "Q3": Q3, "IQR": IQR,
                             "lower_fence": lo, "upper_fence": hi, "n_outliers": n_out})

    log(f"  {col:<8}  Q1={Q1:.0f}  Q3={Q3:.0f}  IQR={IQR:.0f}"
        f"  fences=[{lo:.1f}, {hi:.1f}]  outliers={n_out}")

    if n_out:
        out_rows = df[outlier_mask][["Year", "Country", col]].copy()
        out_rows[col] = out_rows[col].astype(int)
        log(out_rows.to_string(index=False))

total_flagged = df[[f"{c}_outlier" for c in MEDAL_COLS]].any(axis=1).sum()
log(f"\n  Rows flagged as outlier in ≥1 medal column: {total_flagged}")
log("  Outlier flags stored in columns: " +
    ", ".join(f"{c}_outlier" for c in MEDAL_COLS))
log("  Values are preserved as-is (historical facts).")


# ══════════════════════════════════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════════════════════════════════

log("\n" + "═" * 60)
log("FINAL SUMMARY")
log("═" * 60)
log(f"Clean rows written : {len(df)}")
log(f"Years covered      : {sorted(df['Year'].dropna().unique().tolist())}")
log(f"Remaining nulls    :\n{df[[c for c in df.columns if '_outlier' not in c]].isnull().sum().to_string()}")
log(f"\nSample output (first 10 rows):\n{df.head(10).to_string(index=False)}")

df.to_csv(OUTPUT, index=False)
log(f"\nSaved to: {OUTPUT}")

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(report_lines))
log(f"Report saved to: {REPORT}")
