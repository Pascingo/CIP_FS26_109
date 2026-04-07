"""
CIP Project - Data Integration, Preprocessing & Feature Engineering
Standardizes Country Names to ISO-3 Codes (CCA3) and merges medals data
with host countries and geographic proximity (neighbors).
"""

import pandas as pd
import json
import pycountry


def get_iso3_code(country_name: str) -> str:
    """
    Converts an English country name to its ISO-3 (Alpha-3) code.
    Uses a custom mapping for historical or non-standard names,
    and falls back to the 'pycountry' library for standard names.
    """
    if not isinstance(country_name, str):
        return None

    # Strip whitespace and handle potential data artifacts
    clean_name = country_name.strip()

    # 1. Custom Mapping for Olympic-specific or historical entities
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
        "Germany" : "DEU",
        "United Team of Germany": "DEU",
        "Yugoslavia": "SRB",
        "Czechoslovakia": "CZE",
        "Japan": "JPN"
    }

    if clean_name in custom_mapping:
        return custom_mapping[clean_name]

    # 2. Standard ISO mapping via pycountry
    try:
        # Perform a fuzzy or exact lookup
        country = pycountry.countries.lookup(clean_name)
        return country.alpha_3
    except LookupError:
        # Return None if not found, allowing us to inspect unmapped entities later
        return None


def process_host_countries(input_csv: str, output_csv: str) -> None:
    """
    Reads the raw host data, filters columns, standardizes country names,
    and exports the cleaned dataset.
    """
    print(f"--- STEP 1: Loading raw host data from '{input_csv}' ---")
    df = pd.read_csv(input_csv)

    # Validate that required columns exist
    if not {'Year_Clean', 'Host_Country'}.issubset(df.columns):
        print("Error: Required columns ('Year_Clean', 'Host_Country') are missing.")
        return

    # Filter down to the exact columns we need
    df_hosts = df[['Year_Clean', 'Host_Country']].copy()

    print("Applying ISO-3 standardization to Host Countries...")
    df_hosts['Host_ISO3'] = df_hosts['Host_Country'].apply(get_iso3_code)

    # Check for missing values (unmapped countries)
    unmapped = df_hosts[df_hosts['Host_ISO3'].isna()]
    if not unmapped.empty:
        print("\nWARNING: The following countries could not be mapped to an ISO-3 code:")
        print(unmapped['Host_Country'].unique())
        print("Please add them to the 'custom_mapping' dictionary in the script.\n")

    # Export the final integrated table
    df_hosts.to_csv(output_csv, index=False)
    print(f"Successfully processed {len(df_hosts)} host records. Saved to '{output_csv}'.\n")


def build_analysis_dataset(hosts_csv: str, medals_csv: str, neighbors_json: str, output_csv: str) -> None:
    """
    Merges cleaned medals data with host countries and calculates geographic proximity.
    """
    print("--- STEP 2: Building Analysis Dataset ---")
    print("Loading datasets...")

    df_medals = pd.read_csv(medals_csv)
    df_hosts = pd.read_csv(hosts_csv)

    with open(neighbors_json, "r", encoding="utf-8") as f:
        neighbors_data = json.load(f)

    # Transform the JSON list into a fast lookup dictionary
    # Format: {'CHE': ['AUT', 'DEU', 'FRA', 'ITA', 'LIE'], ...}
    neighbors_dict = {item['country']: item['neighbors'] for item in neighbors_data}

    print("Standardizing country names in medals dataset...")
    df_medals['Country_ISO3'] = df_medals['Country'].apply(get_iso3_code)

    # Merge Medals with Host Information
    print("Merging host data...")
    df_hosts = df_hosts.rename(columns={'Year_Clean': 'Year'})
    df_merged = pd.merge(df_medals, df_hosts, on='Year', how='left')

    # Feature Engineering: Calculate "Is_Host" and "Is_Host_Neighbour"
    print("Calculating geographic proximity variables...")

    def check_if_neighbour(row):
        if pd.isna(row['Host_ISO3']) or pd.isna(row['Country_ISO3']):
            return False
        if row['Country_ISO3'] == row['Host_ISO3']:
            return False

        host_neighbors = neighbors_dict.get(row['Host_ISO3'], [])
        return row['Country_ISO3'] in host_neighbors

    df_merged['Is_Host_Neighbour'] = df_merged.apply(check_if_neighbour, axis=1)
    df_merged['Is_Host'] = df_merged['Country_ISO3'] == df_merged['Host_ISO3']

    # Export the final dataset
    df_merged.to_csv(output_csv, index=False)

    print(f"\nSuccess! Final dataset with {len(df_merged)} rows saved to '{output_csv}'.")

    # Validation summary
    print("\n--- Quick Validation ---")
    print(f"Total rows: {len(df_merged)}")
    print(f"Is_Host == True: {df_merged['Is_Host'].sum()}")
    print(f"Is_Host_Neighbour == True: {df_merged['Is_Host_Neighbour'].sum()}")


if __name__ == "__main__":
    # ---------------------------------------------------------
    # Configuration / File Paths
    # ---------------------------------------------------------
    RAW_HOSTS_FILE = "../Data_raw/raw_wikipedia_hosts.csv"
    INTEGRATED_HOSTS_FILE = "../Data_clean/clean_wikipedia_hosts.csv"
    CLEAN_MEDALS_FILE = "../Data_clean/clean_wikipedia_medals.csv"
    NEIGHBORS_JSON_FILE = "../Data_raw/raw_restcountries_api.json"
    FINAL_ANALYSIS_FILE = "../Data_clean/clean_wikipedia_medals_features.csv"

    # ---------------------------------------------------------
    # Execution Pipeline
    # ---------------------------------------------------------
    # Step 1: Process and standardize host countries
    process_host_countries(
        input_csv=RAW_HOSTS_FILE,
        output_csv=INTEGRATED_HOSTS_FILE
    )

    # Step 2: Build final dataset with features
    build_analysis_dataset(
        hosts_csv=INTEGRATED_HOSTS_FILE,
        medals_csv=CLEAN_MEDALS_FILE,
        neighbors_json=NEIGHBORS_JSON_FILE,
        output_csv=FINAL_ANALYSIS_FILE
    )