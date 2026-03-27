import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

CSV_PATH = "../Data_raw/olympedia_winter_games_numbering.csv"
OUTPUT_PATH = "../Data_raw/olympedia_medals_all.csv"

games = pd.read_csv(CSV_PATH)


def extract_names_countries(name_cell, country_cell):
    countries = [a.get_text(strip=True) for a in country_cell.find_all("a")]
    names = [a.get_text(strip=True) for a in name_cell.find_all("a")]

    if not names:
        for br in name_cell.find_all("br"):
            br.replace_with("|")
        parts = [p.strip() for p in name_cell.get_text().split("|") if p.strip()]
        names = parts if parts else ["—"]

    if not countries:
        countries = ["—"] * len(names)
    elif len(countries) < len(names):
        countries += [countries[-1]] * (len(names) - len(countries))

    return list(zip(names, countries))


def scrape_edition(edition_id, year, host_city, max_retries=5):
    url = f"https://www.olympedia.org/editions/{edition_id}/medal"

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)

            # 429: warten und nochmals versuchen
            if response.status_code == 429:
                wait = 2 ** attempt + random.uniform(1, 3)  # 3s, 5s, 9s, 17s, 33s ...
                print(f"\n  ⚠ 429 – warte {wait:.0f}s (Versuch {attempt}/{max_retries})", end=" ", flush=True)
                time.sleep(wait)
                continue

            response.raise_for_status()

        except requests.RequestException as e:
            print(f"\n  ✗ Fehler bei {year} {host_city}: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if not table:
            print(f"\n  ✗ Keine Tabelle für {year} {host_city}")
            return []

        rows = table.find_all("tr")
        results = []
        current_sport = None

        for row in rows:
            all_cells = row.find_all(["th", "td"])
            if len(all_cells) == 1 and all_cells[0].get("colspan"):
                current_sport = all_cells[0].get_text(strip=True)
                continue
            if all(c.name == "th" for c in all_cells):
                continue
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            event = cells[0].get_text(strip=True)
            if not event:
                continue

            medal_data = {
                "Gold": extract_names_countries(cells[1], cells[2]),
                "Silver": extract_names_countries(cells[3], cells[4]),
                "Bronze": extract_names_countries(cells[5], cells[6]) if len(cells) > 6 else [("—", "—")],
            }
            for rank, entries in medal_data.items():
                for name, country in entries:
                    if name and name != "—":
                        results.append({
                            "Edition_ID": edition_id,
                            "Jahr": year,
                            "Host_City": host_city,
                            "Sport": current_sport,
                            "Event": event,
                            "Rang": rank,
                            "Name": name,
                            "Land": country,
                        })
        return results

    print(f"\n  ✗ Aufgegeben nach {max_retries} Versuchen ({year} {host_city})")
    return []


# ── Haupt-Loop ────────────────────────────────────────────────────────────────
all_results = []

for _, row in games.iterrows():
    edition_id = row["edition_id"]
    year = row["year"]
    host_city = row["host_city"]

    print(f"[{year}] {host_city} (ID: {edition_id}) ...", end=" ", flush=True)
    records = scrape_edition(edition_id, year, host_city)
    all_results.extend(records)
    print(f"✓ {len(records)} Einträge")

    # Zufälliger Delay zwischen 3–7 Sekunden
    time.sleep(random.uniform(3, 7))

# ── Speichern ────────────────────────────────────────────────────────────────
df = pd.DataFrame(all_results)
df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print(f"\n✓ Gesamt: {len(df)} Einträge aus {len(games)} Olympiaden → {OUTPUT_PATH}")