"""
Module for scraping Winter Olympic Games host countries from Wikipedia.

This script extracts the host cities and countries for the Winter Olympics
and performs initial data cleaning (e.g., removing footnotes, handling missing values)
to prepare the dataset for further integration with the medals dataset.
"""

import re
import requests
import pandas as pd
from bs4 import BeautifulSoup


def scrape_winter_olympic_hosts(url: str = "https://en.wikipedia.org/wiki/Winter_Olympic_Games") -> pd.DataFrame:
    """
    Scrapes the Winter Olympic Games host table from Wikipedia.

    Args:
        url (str): The URL of the Wikipedia page to scrape.

    Returns:
        pd.DataFrame: A cleaned DataFrame containing the host cities and years,
                      or an empty DataFrame if the table could not be found/fetched.
    """
    # Define headers with a User-Agent to comply with standard web scraping etiquette.
    # Wikipedia requests that automated scripts identify themselves.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CIP-Research-Project-Bot"
    }

    print(f"Fetching data from {url}...")
    try:
        # Add a timeout to prevent the script from hanging indefinitely
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return pd.DataFrame()

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract all table elements from the parsed HTML into a list of DataFrames
    tables = pd.read_html(str(soup))

    host_table = None

    # Iterate through the extracted tables to identify the correct one based on column headers
    for tbl in tables:
        # Wikipedia tables often feature MultiIndex columns (nested headers).
        # Flatten them to a single string level for easier querying.
        if isinstance(tbl.columns, pd.MultiIndex):
            tbl.columns = ['_'.join(str(c) for c in col).strip() for col in tbl.columns.values]

        # Create a single string containing all column names to check for keywords
        col_names = " ".join([str(c) for c in tbl.columns])

        if 'Year' in col_names and 'Host' in col_names:
            host_table = tbl
            break

    if host_table is None:
        print("Error: Could not locate the host table in the document.")
        return pd.DataFrame()

    print("Target table located. Starting preprocessing...")

    # Dynamically find the exact name of the 'Year' column
    year_col = next((c for c in host_table.columns if 'Year' in c), None)

    if not year_col:
        print("Error: Could not find the 'Year' column.")
        return pd.DataFrame()

    # Data Cleaning: Remove Wikipedia footnotes (e.g., "2026[a]" becomes "2026")
    # We use a regular expression to substitute anything inside square brackets with an empty string.
    host_table[year_col] = host_table[year_col].astype(str).apply(
        lambda x: re.sub(r'\[.*?\]', '', x)
    )

    # Convert the cleaned year strings to numeric values.
    # 'coerce' turns invalid parsing (like text rows) into NaN (Not a Number).
    host_table['Year_Clean'] = pd.to_numeric(host_table[year_col], errors='coerce')

    # Drop rows where the year is NaN (these are typically summary rows or invalid data)
    df_clean = host_table.dropna(subset=['Year_Clean']).copy()

    # Cast the year to an integer for cleaner merging later
    df_clean['Year_Clean'] = df_clean['Year_Clean'].astype(int)

    return df_clean


if __name__ == "__main__":
    # Execute the scraping function
    df_hosts = scrape_winter_olympic_hosts()

    if not df_hosts.empty:
        output_file = "winter_olympics_hosts_raw.csv"

        # Export the cleaned DataFrame to a CSV file
        df_hosts.to_csv(output_file, index=False)
        print(f"\nSuccessfully saved {len(df_hosts)} records to '{output_file}'.")

        # Display the first few rows to verify the output
        print(df_hosts.head())
    else:
        print("\nScraping failed or returned no data.")