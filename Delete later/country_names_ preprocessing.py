"""
CIP Project - Data Integration & Preprocessing
Standardize Country Names to ISO-3 Codes (CCA3)
"""

import pandas as pd
import pycountry


def get_iso3_code(country_name: str) -> str:
    """
    Converts an English country name to its ISO-3 (Alpha-3) code.
    Uses a custom mapping for historical or non-standard names,
    and falls back to the 'pycountry' library for standard names.

    Args:
        country_name (str): The name of the country in English.

    Returns:
        str: The 3-letter ISO code, or None if the country cannot be mapped.
    """
    if not isinstance(country_name, str):
        return None

    # Strip whitespace and handle potential data artifacts
    clean_name = country_name.strip()

    # 1. Custom Mapping for Olympic-specific or historical entities
    # Note: You may need to expand this list based on your specific dataset needs.
    custom_mapping = {
        "South Korea": "KOR",
        "North Korea": "PRK",
        "Great Britain": "GBR",
        "Soviet Union": "RUS",  # Assigning to modern Russia for geographic proximity, adjust if needed
        "ROC": "RUS",  # Russian Olympic Committee
        "OAR": "RUS",  # Olympic Athletes from Russia
        "Russia": "RUS", # Manual Mapping as there was an Error somewhere
        "West Germany": "DEU",
        "East Germany": "DEU",
        "United Team of Germany": "DEU",
        "Yugoslavia": "SRB",  # Simplification for spatial analysis
        "Czechoslovakia": "CZE"  # Simplification for spatial analysis
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
    print(f"Loading raw host data from '{input_csv}'...")
    df = pd.read_csv(input_csv)

    # Validate that required columns exist
    if not {'Year_Clean', 'Host_Country'}.issubset(df.columns):
        print("Error: Required columns ('Year_Clean', 'Host_Country') are missing.")
        return

    # Filter down to the exact columns we need
    df_hosts = df[['Year_Clean', 'Host_Country']].copy()

    print("Applying ISO-3 standardization to Host Countries...")
    # Apply the mapping function to create a new standardized column
    df_hosts['Host_ISO3'] = df_hosts['Host_Country'].apply(get_iso3_code)

    # Check for missing values (unmapped countries)
    unmapped = df_hosts[df_hosts['Host_ISO3'].isna()]
    if not unmapped.empty:
        print("\nWARNING: The following countries could not be mapped to an ISO-3 code:")
        print(unmapped['Host_Country'].unique())
        print("Please add them to the 'custom_mapping' dictionary in the script.\n")

    # Export the final integrated table
    df_hosts.to_csv(output_csv, index=False)
    print(f"Successfully processed {len(df_hosts)} records. Saved to '{output_csv}'.")
    print(df_hosts.head())


if __name__ == "__main__":
    # Define file paths
    RAW_FILE = "../Data_raw/raw_wikipedia_hosts.csv"
    CLEAN_FILE = "../Data_clean/clean_wikipedia_hosts.csv"

    process_host_countries(RAW_FILE, CLEAN_FILE)