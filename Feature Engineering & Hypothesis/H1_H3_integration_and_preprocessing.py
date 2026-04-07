"""
H1 + H3 Integration and Preprocessing
======================================

This script merges the legacy medal cleaning logic with host-country / neighbour
feature engineering to produce the final analysis-ready dataset used by H1 and H3.

Outputs:
  - Data_clean/clean_wikipedia_medals.csv
  - Data_clean/clean_wikipedia_hosts.csv
  - Data_clean/clean_wikipedia_medals_features.csv

Usage:
  python "Feature Engineering & Hypothesis/H1_H3_integration_and_preprocessing.py"
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pycountry


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT_DIR / "Data_raw"
DATA_CLEAN = ROOT_DIR / "Data_clean"
DATA_CLEAN.mkdir(parents=True, exist_ok=True)

RAW_WIKIPEDIA_MEDALS = DATA_RAW / "raw_wikipedia_medals.csv"
RAW_WIKIPEDIA_HOSTS = DATA_RAW / "raw_wikipedia_hosts.csv"
RAW_NEIGHBORS = DATA_RAW / "raw_restcountries_api.json"

OUTPUT_CLEAN_MEDALS = DATA_CLEAN / "clean_wikipedia_medals.csv"
OUTPUT_HOSTS_CLEAN = DATA_CLEAN / "clean_wikipedia_hosts.csv"
OUTPUT_ANALYSIS_READY = DATA_CLEAN / "clean_wikipedia_medals_features.csv"
REPORT_PATH = DATA_CLEAN / "winter_olympics_cleaning_report.txt"


def find_existing_path(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"None of the expected files were found: {paths}")


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)


def clean_name(name: str) -> str:
    clean = re.sub(r"[\*‡†]", "", name)
    clean = re.sub(r"\[[^\]]*\]", "", clean)
    return clean.strip()


def is_digit_str(s: str) -> bool:
    return str(s).isdigit()


def parse_row(row) -> dict | None:
    rank_raw = str(row.get("Rank", "")).strip()
    noc = str(row.get("NOC", "")).strip()
    nation = str(row.get("Nation", "")).strip()

    rank_is_int = rank_raw.lstrip("–-").isdigit()
    noc_is_digit = is_digit_str(noc)

    if not rank_is_int and noc_is_digit and not nation:
        country = clean_name(rank_raw)
        gold = int(noc)
        silver = int(row.get("Gold", 0)) if pd.notna(row.get("Gold")) else None
        bronze = int(row.get("Silver", 0)) if pd.notna(row.get("Silver")) else None
        rank = None
    elif noc and not noc_is_digit and not nation:
        country = clean_name(noc)
        gold = int(row.get("Gold", 0)) if pd.notna(row.get("Gold")) else None
        silver = int(row.get("Silver", 0)) if pd.notna(row.get("Silver")) else None
        bronze = int(row.get("Bronze", 0)) if pd.notna(row.get("Bronze")) else None
        rank = rank_raw
    elif not noc and nation and rank_is_int:
        country = clean_name(nation)
        gold = int(row.get("Gold", 0)) if pd.notna(row.get("Gold")) else None
        silver = int(row.get("Silver", 0)) if pd.notna(row.get("Silver")) else None
        bronze = int(row.get("Bronze", 0)) if pd.notna(row.get("Bronze")) else None
        rank = rank_raw
    elif not noc and nation and not rank_is_int:
        country = clean_name(rank_raw)
        gold = int(row.get("Gold", 0)) if pd.notna(row.get("Gold")) else None
        silver = int(row.get("Silver", 0)) if pd.notna(row.get("Silver")) else None
        bronze = int(row.get("Bronze", 0)) if pd.notna(row.get("Bronze")) else None
        rank = nation
    elif noc and nation:
        country = clean_name(nation)
        gold = int(row.get("Gold", 0)) if pd.notna(row.get("Gold")) else None
        silver = int(row.get("Silver", 0)) if pd.notna(row.get("Silver")) else None
        bronze = int(row.get("Bronze", 0)) if pd.notna(row.get("Bronze")) else None
        rank = rank_raw
    else:
        return None

    if not country:
        return None

    return {
        "Rank": rank,
        "Country": country,
        "Gold": gold,
        "Silver": silver,
        "Bronze": bronze,
    }


def clean_medals_dataset(input_path: Path) -> pd.DataFrame:
    df = read_csv(input_path, dtype=str)
    print(f"Loaded raw medals data from {input_path.name} ({len(df)} rows)")

    def is_junk_row(row) -> bool:
        for val in row:
            s = str(val) if pd.notna(val) else ""
            if s.startswith("Totals"):
                return True
        if str(row.get("Rank", "")).lower() == "mixed team":
            return True
        if "neutral" in str(row.get("NOC", "")).lower():
            return True
        return False

    before = len(df)
    df = df[~df.apply(is_junk_row, axis=1)].reset_index(drop=True)
    print(f"Dropped {before - len(df)} garbage rows, {len(df)} rows remain")

    parsed = df.apply(parse_row, axis=1)
    parsed = parsed[parsed.notna()]
    df = df.loc[parsed.index].copy()

    df["Country"] = parsed.apply(lambda x: x["Country"])
    df["Rank"] = parsed.apply(lambda x: x["Rank"])
    df["Gold"] = parsed.apply(lambda x: x["Gold"])
    df["Silver"] = parsed.apply(lambda x: x["Silver"])
    df["Bronze"] = parsed.apply(lambda x: x["Bronze"])

    for col in ["Gold", "Silver", "Bronze", "Year"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["Rank"] = pd.to_numeric(df["Rank"], errors="coerce").astype("Int64")
    df["Total"] = (df["Gold"] + df["Silver"] + df["Bronze"]).astype("Int64")

    df = df[["Year", "Rank", "Country", "Gold", "Silver", "Bronze", "Total"]]
    df = df.sort_values(["Year", "Rank"], na_position="last").reset_index(drop=True)
    return df


def get_iso3_code(country_name: str) -> str | None:
    if not isinstance(country_name, str):
        return None
    clean_name_str = country_name.strip()
    custom_mapping = {
        "South Korea": "KOR",
        "North Korea": "PRK",
        "Great Britain": "GBR",
        "Soviet Union": "RUS",
        "ROC": "RUS",
        "OAR": "RUS",
        "Russia": "RUS",
        "West Germany": "DEU",
        "East Germany": "DEU",
        "Germany": "DEU",
        "United Team of Germany": "DEU",
        "Yugoslavia": "SRB",
        "Czechoslovakia": "CZE",
        "Japan": "JPN",
        "United States": "USA",
        "United States of America": "USA",
        "Great Britain and Northern Ireland": "GBR",
    }
    if clean_name_str in custom_mapping:
        return custom_mapping[clean_name_str]
    try:
        country = pycountry.countries.lookup(clean_name_str)
        return country.alpha_3
    except LookupError:
        return None


def standardize_hosts(input_path: Path) -> pd.DataFrame:
    df = read_csv(input_path)
    if not {"Year_Clean", "Host_Country"}.issubset(df.columns):
        raise ValueError(f"Host file {input_path} is missing required columns")

    df_hosts = df[["Year_Clean", "Host_Country"]].copy()
    df_hosts["Host_ISO3"] = df_hosts["Host_Country"].apply(get_iso3_code)
    df_hosts["Host_ISO3"] = df_hosts["Host_ISO3"].astype(object)
    unmapped = df_hosts[df_hosts["Host_ISO3"].isna()]
    if not unmapped.empty:
        print("WARNING: Some host countries could not be mapped to ISO-3:")
        print(unmapped[["Year_Clean", "Host_Country"]].to_string(index=False))

    return df_hosts


def build_final_dataset(clean_medals: pd.DataFrame, hosts: pd.DataFrame, neighbors_path: Path) -> pd.DataFrame:
    with open(neighbors_path, "r", encoding="utf-8") as fh:
        neighbors_data = json.load(fh)
    neighbors_dict = {item["country"]: item["neighbors"] for item in neighbors_data}

    df_medals = clean_medals.copy()
    df_medals["Country_ISO3"] = df_medals["Country"].apply(get_iso3_code)
    df_medals["Country_ISO3"] = df_medals["Country_ISO3"].astype(object)

    df_hosts = hosts.rename(columns={"Year_Clean": "Year"}).copy()
    df_hosts["Host_ISO3"] = df_hosts["Host_ISO3"].astype(object)

    merged = pd.merge(df_medals, df_hosts, on="Year", how="left", validate="m:1")

    def host_neighbour_flag(row):
        if pd.isna(row["Host_ISO3"]) or pd.isna(row["Country_ISO3"]):
            return False
        if row["Country_ISO3"] == row["Host_ISO3"]:
            return False
        return row["Country_ISO3"] in neighbors_dict.get(row["Host_ISO3"], [])

    merged["Is_Host"] = merged["Country_ISO3"] == merged["Host_ISO3"]
    merged["Is_Host_Neighbour"] = merged.apply(host_neighbour_flag, axis=1)
    merged["Is_Host"] = merged["Is_Host"].astype("int8")
    merged["Is_Host_Neighbour"] = merged["Is_Host_Neighbour"].astype("int8")

    return merged


def main() -> None:
    medals_input = RAW_WIKIPEDIA_MEDALS
    hosts_input = RAW_WIKIPEDIA_HOSTS

    clean_medals = clean_medals_dataset(medals_input)
    clean_medals.to_csv(OUTPUT_CLEAN_MEDALS, index=False, encoding="utf-8")
    print(f"Saved cleaned medals to {OUTPUT_CLEAN_MEDALS}")

    hosts = standardize_hosts(hosts_input)
    hosts.to_csv(OUTPUT_HOSTS_CLEAN, index=False)
    print(f"Saved host mapping to {OUTPUT_HOSTS_CLEAN}")

    final = build_final_dataset(clean_medals, hosts, RAW_NEIGHBORS)
    final.to_csv(OUTPUT_ANALYSIS_READY, index=False)
    print(f"Saved analysis-ready dataset to {OUTPUT_ANALYSIS_READY}")

    print("\n--- Summary ---")
    print(f"Total rows in final dataset: {len(final)}")
    print(f"Host rows: {final['Is_Host'].sum()}")
    print(f"Host neighbour rows: {final['Is_Host_Neighbour'].sum()}")


if __name__ == "__main__":
    main()
