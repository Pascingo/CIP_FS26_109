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
from selenium.common.exceptions import (
    StaleElementReferenceException,
    ElementClickInterceptedException,
    TimeoutException
)


EXPAND_XPATH = "//button[@aria-expanded='false' and contains(@title, 'open the row')]"


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



def expand_until_stable(driver, max_passes=25):
    """
    Click all currently present collapsed expanders.
    Repeat passes because expanding parents can inject new nested expanders
    *without scrolling*.
    Returns number of successful expansions performed across all passes.
    """
    total_clicked = 0

    for _ in range(max_passes):
        buttons = driver.find_elements(By.XPATH, EXPAND_XPATH)
        if not buttons:
            break

        clicked_this_pass = 0
        for btn in buttons:
            try:
                    # Still collapsed?
                if btn.get_attribute("aria-expanded") != "false":
                    continue

                # Prefer native click; fallback to JS click if Selenium thinks it's not interactable
                try:
                    btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn)

                # Give React/JS time to update aria-expanded and mount nested rows
                WebDriverWait(driver, 2).until(lambda d: btn.get_attribute("aria-expanded") == "true")

                clicked_this_pass += 1
                total_clicked += 1
                time.sleep(0.4)

            except (StaleElementReferenceException, ElementClickInterceptedException, TimeoutException):
                # DOM re-rendered or overlay intercepted; next pass usually catches it
                continue
            except Exception:
                continue

        # If nothing changed in this pass, we’re stable for the current DOM slice
        if clicked_this_pass == 0:
            break

    return total_clicked


def scroll_down_only_if_needed(driver, step=900):
    """
    Scroll window down by 'step' pixels.
    Returns True if the scroll position changed (i.e., we actually moved).
    """
    before = driver.execute_script("return window.pageYOffset;")
    driver.execute_script(f"window.scrollBy(0, {step});")
    time.sleep(0.7)
    after = driver.execute_script("return window.pageYOffset;")
    return after > before


def expand_entire_site(driver, step=900, max_cycles=300):
    """
    Iteratively expand everything:
      - Expand until stable (no new expanders clicked)
      - Only then scroll
    Stops when we can’t scroll further AND no new expanders are present.
    """
    grand_total = 0
    cycles = 0

    while cycles < max_cycles:
        cycles += 1

        # 1) Expand everything currently available in the DOM (including newly injected nested stuff)
        clicked = expand_until_stable(driver)
        grand_total += clicked
        if clicked > 0:
            # Important: do NOT scroll yet — expanding often reveals more nested expanders immediately
            continue

        # 2) If stable (no clicks), THEN scroll to load next virtual slice
        moved = scroll_down_only_if_needed(driver, step=step)

        # 3) If we didn't move, we might be at the end. Confirm no expanders exist.
        if not moved:
            remaining = driver.find_elements(By.XPATH, EXPAND_XPATH)
            if not remaining:
                break
            # If remaining exists but no movement, try a small nudge + one more expand pass
            driver.execute_script("window.scrollBy(0, 250);")
            time.sleep(0.6)

    return grand_total


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

        # 2. Expand EVERYTHING first (scroll only when no new expandable sections exist)
        print("Phase A: Expanding all rows (scrolling only when stable)...")
        total_expanded = expand_entire_site(driver, step=900)
        #total_expanded += expand_entire_site(driver, step=900)
        print(f"Expansion complete. Total expanded clicks: {total_expanded}")

        # 3. Scroll back to top and scrape top->bottom (virtualized DOM => must scroll while scraping)
        print("Phase B: Scrolling back to top and scraping...")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        extracted_data = []
        seen = set()

        current_sport = "Unknown"
        current_discipline = "Unknown"

        while True:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            all_rows = soup.find_all(['button', 'div'], role='row')

            for row in all_rows:
                # Header button row: update current sport/discipline context
                if row.name == 'button' and 'title' in row.attrs:
                    title_text = row['title']
                    if ':' in title_text:
                        event_name = title_text.split(':')[0].strip()
                        if '-' in event_name:
                            parts = event_name.split('-', 1)
                            current_sport = parts[0].strip()
                            current_discipline = parts[1].strip()
                        else:
                            current_sport = event_name
                            current_discipline = "Overall"
                    continue

                # Data row
                if row.name == 'div':
                    medal_div = row.find('div', title=lambda t: t and 'medal' in t.lower())
                    if not medal_div:
                        continue

                    medal_type = medal_div.get('title', 'Unknown')

                    img_tag = row.find('img')
                    country_full = img_tag.get('title', 'Unknown') if img_tag else "Unknown"

                    p_tags = row.find_all('p', attrs={'translate': 'no'})
                    noc_code = "Unknown"
                    athlete_name = "Team Event / Unknown"
                    if len(p_tags) >= 2:
                        noc_code = p_tags[0].text.strip()
                        athlete_name = p_tags[1].text.strip()
                    elif len(p_tags) == 1:
                        noc_code = p_tags[0].text.strip()

                    key = (current_sport, current_discipline, medal_type, noc_code, country_full, athlete_name)
                    if key in seen:
                        continue
                    seen.add(key)

                    extracted_data.append({
                        'Sport': current_sport,
                        'Discipline': current_discipline,
                        'Medal': medal_type,
                        'NOC': noc_code,
                        'Country': country_full,
                        'Athlete': athlete_name
                    })

            # scroll down for next virtual slice; stop when no movement
            if not scroll_down_only_if_needed(driver, step=900):
                break        

        # 4. Create DataFrame and CLEAN DUPLICATES
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
        print("Failed to extract data or DataFrame is empty. CSV was not created!")