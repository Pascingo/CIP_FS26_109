"""
CIP Project - Feature Engineering & Data Integration
Merges cleaned medals data with host countries and geographic proximity (neighbors).
"""

import pandas as pd
import json
import pycountry


def get_iso3_code(country_name: str) -> str:
    """
    Converts English country names to ISO-3 codes.
    (Reused from the host standardization step).
    """
    if not isinstance(country_name, str):
        return None

    clean_name = country_name.strip()

    # Custom mapping for historical or specific Olympic entities
    custom_mapping = {
        "South Korea": "KOR",
        "North Korea": "PRK",
        "Great Britain": "GBR",
        "Soviet Union": "RUS",
        "ROC": "RUS",
        "Russia": "RUS",
        "OAR": "RUS",
        "West Germany": "DEU",
        "East Germany": "DEU",
        "United Team of Germany": "DEU",
        "Yugoslavia": "SRB",
        "Czechoslovakia": "CZE"
    }

    if clean_name in custom_mapping:
        return custom_mapping[clean_name]

    try:
        country = pycountry.countries.lookup(clean_name)
        return country.alpha_3
    except LookupError:
        return None


def build_analysis_dataset():
    # 1. Load datasets
    print("Loading datasets...")
    # Use the CLEANED medals data!
    df_medals = pd.read_csv("winter_olympics_medals_clean.csv")
    df_hosts = pd.read_csv("winter_olympics_hosts_integrated.csv")

    with open("countries_neighbors.json", "r", encoding="utf-8") as f:
        neighbors_json = json.load(f)

    # 2. Transform the JSON list into a fast lookup dictionary
    # Format: {'CHE': ['AUT', 'DEU', 'FRA', 'ITA', 'LIE'], ...}
    neighbors_dict = {item['country']: item['neighbors'] for item in neighbors_json}

    # 3. Standardize country names in the medals dataset
    print("Standardizing country names in medals dataset...")
    df_medals['Country_ISO3'] = df_medals['Country'].apply(get_iso3_code)

    # 4. Merge Medals with Host Information
    # We join on the 'Year' column. df_hosts needs to have 'Year_Clean' renamed to 'Year' if necessary.
    # Assuming df_hosts has ['Year_Clean', 'Host_ISO3']
    print("Merging host data...")
    df_hosts = df_hosts.rename(columns={'Year_Clean': 'Year'})
    df_merged = pd.merge(df_medals, df_hosts, on='Year', how='left')

    # 5. Feature Engineering: Calculate "Is_Host" and "Is_Host_Neighbour"
    print("Calculating geographic proximity variables...")

    def check_if_neighbour(row):
        # If we don't know the host or the country, we can't determine it
        if pd.isna(row['Host_ISO3']) or pd.isna(row['Country_ISO3']):
            return False

        # A host is not its own neighbour in this context
        if row['Country_ISO3'] == row['Host_ISO3']:
            return False

        # Get the neighbors of the host for this specific year
        host_neighbors = neighbors_dict.get(row['Host_ISO3'], [])

        # Check if the competing country is in the host's neighbor list
        return row['Country_ISO3'] in host_neighbors

    # Create the boolean columns
    df_merged['Is_Host_Neighbour'] = df_merged.apply(check_if_neighbour, axis=1)
    df_merged['Is_Host'] = df_merged['Country_ISO3'] == df_merged['Host_ISO3']

    # 6. Export the final dataset
    output_file = "winter_olympics_analysis_ready.csv"
    df_merged.to_csv(output_file, index=False)

    print(f"\nSuccess! Final dataset with {len(df_merged)} rows saved to '{output_file}'.")

    # Print a quick validation summary
    print("\nQuick Validation (True values count):")
    print(f"Total rows: {len(df_merged)}")
    print(f"Is_Host == True: {df_merged['Is_Host'].sum()}")
    print(f"Is_Host_Neighbour == True: {df_merged['Is_Host_Neighbour'].sum()}")


if __name__ == "__main__":
    build_analysis_dataset()