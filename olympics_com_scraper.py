import time
import pandas as pd
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver():
    """
    Sets up the Selenium Chrome WebDriver with options to reduce bot-detection.
    """
    options = Options()
    options.add_argument("--start-maximized")

    # Anti-bot measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Automatically download and set up the correct ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    return driver


def scrape_olympics_medals(url):
    """
    Navigates to the olympics.com URL, handles the cookie banner,
    scrolls through the virtual scroller to expand all sports/disciplines,
    and extracts the medal data AS WE SCROLL into a pandas DataFrame.
    """
    driver = setup_driver()
    print(f"Opening URL: {url}")

    try:
        driver.get(url)

        # 1. Handle primary Cookie Banner (Accept All)
        try:
            print("Looking for the main cookie banner ('Accept all')...")
            cookie_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_button.click()
            print("Main cookie banner accepted.")
            time.sleep(2)
        except Exception:
            print("No 'Accept all' banner found.")

        # 1b. Handle secondary Cookie Banner (Confirm Choices)
        try:
            print("Checking for a secondary preference banner...")
            second_cookie_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-cy='onetrust-confirm-choice-button']"))
            )
            second_cookie_button.click()
            print("Secondary cookie banner ('Confirm Choices') successfully accepted.")
            time.sleep(2)
        except Exception:
            print("No secondary cookie banner found. The path is clear.")

        # 2. Expand rows and extract data AS WE SCROLL
        print("Expanding sports and extracting data simultaneously. This might take a few minutes...")

        extracted_data = []

        while True:
            # 2a: Aufklappen
            expand_buttons = driver.find_elements(By.XPATH,
                                                  "//button[@aria-expanded='false' and contains(@title, 'open the row')]")

            for btn in expand_buttons:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.3)
                except Exception:
                    continue

            # --- 2b: We scrape Data inclusive sport and discipline ---
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # We look for all Elements with role='row'
            all_rows = soup.find_all(['button', 'div'], role='row')

            # temporary memory for scraper
            current_sport = "Unknown"
            current_discipline = "Unknown"

            for row in all_rows:
                # 1. Case: We see a "Plus Button" (Header)
                if row.name == 'button' and 'title' in row.attrs:
                    title_text = row['title']  # z.B. "Alpine Skiing - Women's Downhill: open the row..."

                    # Extract text
                    if ':' in title_text:
                        event_name = title_text.split(':')[0].strip()

                        # If Separator in there
                        if '-' in event_name:
                            parts = event_name.split('-', 1)
                            current_sport = parts[0].strip()
                            current_discipline = parts[1].strip()
                        else:
                            current_sport = event_name
                            current_discipline = "Overall"


                    continue

                # 2. Case: Data-Row (Div)
                if row.name == 'div':
                    medal_div = row.find('div', title=lambda t: t and 'medal' in t.lower())
                    if not medal_div:
                        continue

                    medal_type = medal_div['title']
                    img_tag = row.find('img')
                    country_full = img_tag['title'] if img_tag and 'title' in img_tag.attrs else "Unknown"

                    p_tags = row.find_all('p', attrs={'translate': 'no'})
                    noc_code = "Unknown"
                    athlete_name = "Team Event / Unknown"

                    if len(p_tags) >= 2:
                        noc_code = p_tags[0].text.strip()
                        athlete_name = p_tags[1].text.strip()
                    elif len(p_tags) == 1:
                        noc_code = p_tags[0].text.strip()

                    # We add the sport and discipline to the file
                    extracted_data.append({
                        'Sport': current_sport,
                        'Discipline': current_discipline,
                        'Medal': medal_type,
                        'NOC': noc_code,
                        'Country': country_full,
                        'Athlete': athlete_name
                    })

            # 2c: Scroll
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2)

            new_height = driver.execute_script("return document.body.scrollHeight")
            current_position = driver.execute_script("return window.pageYOffset + window.innerHeight")

            if current_position >= (new_height - 50):
                print("Reached the end of the list.")
                break

        # 3. Create DataFrame and CLEAN DUPLICATES
        print(f"Total raw records extracted (including duplicates): {len(extracted_data)}")
        df = pd.DataFrame(extracted_data)

        if not df.empty:
            df.drop_duplicates(inplace=True)
            print(f"Total unique records after cleaning: {len(df)}")

        return df

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        print("Closing browser...")
        driver.quit()


# --- Main Execution Block ---
if __name__ == "__main__":
    target_url = "https://www.olympics.com/en/milano-cortina-2026/medals/medals-by-sport"

    # Run the scraper
    df_results = scrape_olympics_medals(target_url)

    # Save results to CSV
    if df_results is not None and not df_results.empty:
        # Extrahiert "milano-cortina-2026" für einen sauberen Dateinamen
        game_slug = target_url.split('/')[4]
        csv_filename = f"olympics_medals_raw_{game_slug}.csv"

        df_results.to_csv(csv_filename, index=False, encoding='utf-8')

        print(f"\nData successfully saved to '{csv_filename}'.")
        print("\nPreview of the first 5 rows:")
        print(df_results.head())
    else:
        print("Failed to extract data or DataFrame is empty. CSV was not created.")