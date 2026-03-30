import requests
import json

# API endpoint with required fields:
# cca3 = ISO Alpha-3 country code
# borders = list of neighboring country codes
URL = "https://restcountries.com/v3.1/all?fields=cca3,borders"

# Send GET request to the API
response = requests.get(URL)

# Raise an error if the request failed
response.raise_for_status()

# Parse JSON response into Python objects
countries = response.json()

result = []

# Iterate over all countries in the response
for country in countries:
    # Get the country code (CCA3)
    country_code = country.get("cca3")
    
    # Get neighboring countries (may be missing for island nations)
    neighbors = country.get("borders", [])
    
    # Append structured result
    result.append({
        "country": country_code,
        "neighbors": neighbors
    })

# Write the result to a JSON file
with open("../Data_raw/raw_countries_neighbors.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Export completed: raw_countries_neighbors.json")
