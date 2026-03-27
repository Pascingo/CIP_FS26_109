"""
Winter Olympics Medals CSV Cleaner
------------------------------------
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
"""

import pandas as pd
import re


INPUT  = "winter_olympics_medals_master.csv"
OUTPUT = "winter_olympics_medals_clean.csv"


# ── Load ──────────────────────────────────────────────────────────────────────

df = pd.read_csv(INPUT, dtype=str)  # read everything as string for safe parsing
print(f"Loaded {len(df)} rows, columns: {df.columns.tolist()}")


# ── 1. Drop aggregate and non-country rows ────────────────────────────────────

def is_junk_row(row) -> bool:
    for val in row:
        s = str(val) if pd.notna(val) else ""
        if s.startswith("Totals"):
            return True
    if str(row["Rank"]).lower() == "mixed team":
        return True
    # Individual Neutral Athletes row (2026)
    if "neutral" in str(row.get("NOC", "")).lower():
        return True
    return False

before = len(df)
df = df[~df.apply(is_junk_row, axis=1)].reset_index(drop=True)
print(f"Dropped {before - len(df)} aggregate/non-country rows  →  {len(df)} remaining")


# ── 2. Resolve country name from inconsistent NOC / Nation columns ────────────

def clean_name(name: str) -> str:
    name = re.sub(r"[\*‡†]", "", name)       # asterisks, daggers
    name = re.sub(r"\[[^\]]*\]", "", name)   # [A], [B], etc.
    return name.strip()


def is_digit_str(s: str) -> bool:
    """True when s looks like a small integer (e.g. '0', '1', '11')."""
    return s.isdigit()


def parse_row(row) -> dict | None:
    """
    Resolve country, rank, and medal counts from a raw row.

    Three schemas appear in the source data:

      A) Standard:  Rank=int,     NOC=country, Gold/Silver/Bronze in their columns
      B) Alternate: Rank=int,     NOC=null,    Nation=country
      C) Shifted:   Rank=country, NOC=Gold,    Gold=Silver, Silver=Bronze,
                    Bronze=Total  (rank number is simply missing / unrecoverable)
    """
    rank_raw = str(row["Rank"]).strip()  if pd.notna(row["Rank"])   else ""
    noc      = str(row["NOC"]).strip()   if pd.notna(row["NOC"])    else ""
    nation   = str(row["Nation"]).strip() if pd.notna(row["Nation"]) else ""

    rank_is_int   = rank_raw.lstrip("–-").isdigit()
    noc_is_digit  = is_digit_str(noc)

    # ── Schema C: country name in Rank, Gold value shifted into NOC ──────
    if not rank_is_int and noc_is_digit and not nation:
        country = clean_name(rank_raw)
        gold    = int(noc)
        silver  = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        bronze  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        rank    = None               # rank number was lost in the source

    # ── Schema A: country in NOC ──────────────────────────────────────────
    elif noc and not noc_is_digit and not nation:
        country = clean_name(noc)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = rank_raw

    # ── Schema B (i): country in Nation, numeric rank ─────────────────────
    elif not noc and nation and rank_is_int:
        country = clean_name(nation)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = rank_raw

    # ── Schema B (ii): country in Rank, rank in Nation (earlier swapped) ─
    elif not noc and nation and not rank_is_int:
        country = clean_name(rank_raw)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = nation

    # ── Both NOC and Nation present ───────────────────────────────────────
    elif noc and nation:
        country = clean_name(nation)
        gold    = int(row["Gold"])   if pd.notna(row["Gold"])   else None
        silver  = int(row["Silver"]) if pd.notna(row["Silver"]) else None
        bronze  = int(row["Bronze"]) if pd.notna(row["Bronze"]) else None
        rank    = rank_raw

    else:
        return None  # unresolvable

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
print(f"Recomputed Total for {missing_total} rows where it was missing")


# ── 5. Final column selection and sort ────────────────────────────────────────

df = df[["Year", "Rank", "Country", "Gold", "Silver", "Bronze", "Total"]]
df = df.sort_values(["Year", "Rank"], na_position="last").reset_index(drop=True)


# ── 6. Summary ────────────────────────────────────────────────────────────────

print(f"\nClean rows written: {len(df)}")
print(f"Years covered:      {sorted(df['Year'].dropna().unique().tolist())}")
print(f"Remaining nulls:\n{df.isnull().sum().to_string()}")
print(f"\nSample output:\n{df.head(10).to_string(index=False)}")

df.to_csv(OUTPUT, index=False)
print(f"\nSaved to: {OUTPUT}")
