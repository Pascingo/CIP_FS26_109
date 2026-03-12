import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_2026_medal_table():
    url = "https://en.wikipedia.org/wiki/2026_Winter_Olympics_medal_table"
    
    myheaders = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
    }
    
    print(f"Load Data: {url}")
    response = requests.get(url, headers=myheaders)
    
    if response.status_code != 200:
        print(f"Fehler beim Abruf. HTTP Statuscode: {response.status_code}")
        return None
        
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # 1. Alle wikitables finden
    tables = soup.find_all('table', class_='wikitable')
    target_table = None
    headers = []
    
    for table in tables:
        header_row = table.find('tr')
        if header_row:
            current_headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
            # Prüfen, ob es die Medaillentabelle ist
            if 'Gold' in current_headers or 'Total' in current_headers:
                target_table = table
                headers = current_headers
                break
                
    if not target_table:
        print("Medaillentabelle konnte nicht gefunden werden.")
        return None
        
    # 3. Tabellenzeilen (Data) extrahieren
    rows = []
    # Überspringe die Header-Zeile [1:]
    for tr in target_table.find_all('tr')[1:]:
        # Bei Wikipedia ist die Nation oft ein <th> und die Medaillen sind <td>
        cols = tr.find_all(['th', 'td'])
        
        # Den Text extrahieren und bereinigen
        cols_text = [c.text.strip() for c in cols]
        
        if len(cols_text) > 0:
            rows.append(cols_text)
            
    # 4. In Pandas DataFrame überführen [cite: 791]
    # Manchmal gibt es leichte Abweichungen in der Spaltenanzahl bei Wikipedia
    try:
        df = pd.DataFrame(rows, columns=headers)
    except ValueError:
        print("Warnung: Spaltenanzahl weicht ab. Generiere DataFrame ohne Header-Zuweisung.")
        df = pd.DataFrame(rows)
        
    return df

# Scraper ausführen
df_medals_2026 = scrape_2026_medal_table()

if df_medals_2026 is not None:
    print("\nErste Zeilen des DataFrames:")
    print(df_medals_2026.head())
