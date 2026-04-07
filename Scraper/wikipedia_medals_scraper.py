import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

OUTPUT_CSV = "../Data_raw/raw_wikipedia_medals.csv"

def scrape_medal_table_by_year(year):
    # Dynamic URL (f-string)
    url = f"https://en.wikipedia.org/wiki/{year}_Winter_Olympics_medal_table"

    myheaders = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
    }

    print(f"Lade Daten für das Jahr {year}...")
    response = requests.get(url, headers=myheaders, timeout=15)

    if response.status_code != 200:
        print(f" -> Seite für {year} nicht gefunden oder blockiert (Status: {response.status_code}).")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    tables = soup.find_all('table', class_='wikitable')
    target_table = None
    headers = []

    for table in tables:
        header_row = table.find('tr')
        if header_row:
            current_headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
            if 'Gold' in current_headers or 'Total' in current_headers:
                target_table = table
                headers = current_headers
                break

    if not target_table:
        print(f" -> Medaillentabelle für {year} konnte nicht identifiziert werden.")
        return None

    rows = []
    for tr in target_table.find_all('tr')[1:]:
        cols = tr.find_all(['th', 'td'])
        cols_text = [c.text.strip() for c in cols]
        if len(cols_text) > 0:
            rows.append(cols_text)

    try:
        df = pd.DataFrame(rows, columns=headers)
    except ValueError:
        df = pd.DataFrame(rows)

    df['Year'] = year
    return df


def build_year_list():
    return sorted(list(set(list(range(1924, 1996, 4)) + list(range(1994, 2027, 4)))))


def main():
    years = build_year_list()
    all_dfs = []

    for y in years:
        df_year = scrape_medal_table_by_year(y)
        if df_year is not None:
            all_dfs.append(df_year)
        time.sleep(5)

    if all_dfs:
        master_df = pd.concat(all_dfs, ignore_index=True)
        print("\nScraping abgeschlossen! Dimension des Master-DataFrames:", master_df.shape)
        print(master_df.head())

        master_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print(f"\nSaved output to {OUTPUT_CSV}")
    else:
        print("Es konnten keine Daten gesammelt werden.")


if __name__ == "__main__":
    main()
