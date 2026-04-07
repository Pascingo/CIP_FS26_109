import requests
import json

URL = "https://restcountries.com/v3.1/all?fields=cca3,borders"
OUTPUT_JSON = "../Data_raw/raw_restcountries_api.json"


def fetch_country_neighbors():
    response = requests.get(URL, timeout=15)
    response.raise_for_status()
    countries = response.json()

    result = []
    for country in countries:
        country_code = country.get("cca3")
        neighbors = country.get("borders", [])
        result.append({
            "country": country_code,
            "neighbors": neighbors,
        })

    return result


def main():
    result = fetch_country_neighbors()

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Export completed: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
