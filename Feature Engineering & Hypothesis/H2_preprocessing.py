"""
Step 1: Build master dataset for DiD / DDD analysis.

Reads:
  - olympedia_medals_all.csv             (medal-level results)
  - sport_pairs_categorized.csv          (Sport/Event -> category: subjective|objective|mixed)
  - winter_olympics_hosts_integrated.csv (authoritative Year -> Host mapping, ISO3)

Writes:
  - Data_clean/winter_olympics_medals_did_clean.csv
  - Data_clean/unmatched_sport_event_pairs.csv   (ONLY if some Sport–Event pairs are missing in the categorization)

How to run:
$ python H2_preprocessing.py
"""

import sys
import pandas as pd
from pathlib import Path

# --------------------------
# Repository root and data paths
# --------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "Data_clean"
RAW_DIR = ROOT_DIR / "Data_raw"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------
# Config
# --------------------------
FN_MEDALS = RAW_DIR / "olympedia_medals_all.csv"             # medal-level data  
FN_PAIRS  = RAW_DIR / "sport_pairs_categorized.csv"          # Sport/Event -> category  
FN_HOSTS  = RAW_DIR / "winter_olympics_hosts_integrated.csv" # Year -> Host mapping     
FN_OUT    = DATA_DIR / "winter_olympics_medals_did_clean.csv"

# Medal points map (for "points"-weighted shares in later steps)
MEDAL_MAP = {"Gold": 3, "Silver": 2, "Bronze": 1}

# ISO3 -> IOC (NOC) normalization for host mapping
ISO3_TO_IOC = {
    # Same in IOC and ISO3 (kept for completeness):
    "USA": "USA", "CAN": "CAN", "ITA": "ITA", "AUT": "AUT", "NOR": "NOR",
    "JPN": "JPN", "FRA": "FRA", "RUS": "RUS", "KOR": "KOR", "CHN": "CHN",
    # Differences:
    "CHE": "SUI",   # Switzerland
    "DEU": "GER",   # Germany (unified NOC)
    # Sarajevo 1984: file uses SRB; host NOC at the time was Yugoslavia (YUG)
    "SRB": "YUG",
}

# --------------------------
# Helpers
# --------------------------
def read_csv_safely(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        sys.exit(f"[ERROR] File not found: {path}")
    try:
        return pd.read_csv(p)
    except Exception:
        try:
            return pd.read_csv(p, encoding="utf-8-sig")
        except Exception:
            # last resort: semicolon + utf-8-sig (seen in some exports)
            return pd.read_csv(p, sep=";", encoding="utf-8-sig")


def ensure_required(df: pd.DataFrame, cols: set, name: str):
    missing = cols - set(df.columns)
    if missing:
        sys.exit(f"[ERROR] {name} missing columns: {missing}")


def normalize_str_col(df: pd.DataFrame, col: str):
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()


# --------------------------
# 1) Load the three inputs
# --------------------------
medals = read_csv_safely(FN_MEDALS)    # expected columns: Edition_ID, Jahr, Host_City, Sport, Event, Rang, Name, Land
pairs  = read_csv_safely(FN_PAIRS)     # expected columns: Sport, Event, category
hosts  = read_csv_safely(FN_HOSTS)     # expected columns: Year_Clean, Host_Country, Host_ISO3

# Guard columns (soft check for medals—old exports can vary slightly)
need_medals_cols = {"Jahr", "Host_City", "Sport", "Event", "Rang", "Land"}
ensure_required(medals, need_medals_cols, FN_MEDALS)

need_pairs_cols = {"Sport", "Event", "category"}
ensure_required(pairs, need_pairs_cols, FN_PAIRS)

need_hosts_cols = {"Year_Clean", "Host_ISO3"}
ensure_required(hosts, need_hosts_cols, FN_HOSTS)

# --------------------------
# 2) Normalize keys and basic cleaning
# --------------------------
for col in ["Sport", "Event"]:
    normalize_str_col(medals, col)
    normalize_str_col(pairs, col)

# Standardize category values to lower-case (subjective|objective|mixed)
pairs["category"] = pairs["category"].astype(str).str.strip().str.lower()

# Deduplicate Sport-Event in the pair mapping (take first occurrence)
pairs = pairs.drop_duplicates(subset=["Sport", "Event"], keep="first")

# --------------------------
# 3) Join medals with Sport-Event category
# --------------------------
master = medals.merge(
    pairs, on=["Sport", "Event"], how="left", validate="m:1"
)

# Report Sport-Event pairs that were not matched (if any)
unmatched = (
    master.loc[master["category"].isna(), ["Sport", "Event"]]
          .drop_duplicates()
          .sort_values(["Sport", "Event"])
)
if len(unmatched) > 0:
    unmatched_file = DATA_DIR / "unmatched_sport_event_pairs.csv"
    unmatched.to_csv(unmatched_file, index=False)
    print(f"[WARN] {len(unmatched)} Sport–Event pairs not categorized. See -> {unmatched_file}")

# --------------------------
# 4) Medal text and numeric points
# --------------------------
master["medal_text"] = master["Rang"].astype(str).str.strip()
master["medal_numeric"] = master["medal_text"].map(MEDAL_MAP)

# Rename Land -> NOC for clarity downstream
master = master.rename(columns={"Land": "NOC"})

# --------------------------
# 5) Host mapping by year (authoritative)
# --------------------------
# Filter hosts to years present in medals and that carry a valid ISO3 code
years_in_data = set(master["Jahr"].dropna().unique())
hosts_clean = (
    hosts.rename(columns={"Year_Clean": "Jahr"})
         .query("Host_ISO3.notna() and Host_ISO3.str.len() == 3")
         .copy()
)
hosts_clean = hosts_clean[hosts_clean["Jahr"].isin(years_in_data)]

# ISO3 -> IOC/NOC normalization
hosts_clean["Host_NOC"] = hosts_clean["Host_ISO3"].str.upper().map(lambda x: ISO3_TO_IOC.get(x, x))

# Ensure at most one host row per year
dupes = hosts_clean.groupby("Jahr").size()
if (dupes > 1).any():
    dup_years = dupes[dupes > 1].index.tolist()
    sys.exit(f"[ERROR] Multiple host rows in {FN_HOSTS} for years: {dup_years}. Please fix and rerun.")

# Merge Host_NOC to master
master = master.merge(
    hosts_clean[["Jahr", "Host_NOC"]],
    on="Jahr",
    how="left",
    validate="m:1"
)

# is_host flag (medalist’s NOC equals host NOC for that year)
master["is_host"] = (master["NOC"] == master["Host_NOC"]).astype("int8")

# --------------------------
# 6) One-hot dummies for category (useful in model formulas)
# --------------------------
master["category"] = master["category"].astype(str).str.lower().str.strip()
for cat in ["subjective", "objective", "mixed"]:
    master[f"cat_{cat}"] = (master["category"] == cat).astype("int8")

# --------------------------
# 7) Final column order and write output
# --------------------------
cols_first = [
    "Edition_ID", "Jahr", "Host_City",
    "NOC", "Sport", "Event", "Rang",
    "category", "is_host", "medal_numeric", "Host_NOC"
]
cols_first_existing = [c for c in cols_first if c in master.columns]
ordered = master[cols_first_existing + [c for c in master.columns if c not in cols_first_existing]]

ordered.to_csv(FN_OUT, index=False, encoding="utf-8")
print(f"[OK] Master dataset written to: {FN_OUT}")
