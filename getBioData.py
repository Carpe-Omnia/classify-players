import os
import csv
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
import time
from webdriver_manager.chrome import ChromeDriverManager

# --- Function to scrape player bio data ---
def get_player_info(driver, player_url):
    """
    Fetches an ESPN NFL player's profile page using an existing Selenium driver instance
    to handle dynamic content and extracts basic biographical information.
    """
    # Updated keys to match the 'Player' prefixed fieldnames
    bio_data = {
        'PlayerHeightWeight': 'N/A',
        'PlayerBirthdate': 'N/A',
        'PlayerCollege': 'N/A',
        'PlayerDraftInfo': 'N/A',
        'PlayerOverallStatus': 'N/A' 
    }

    try:
        print(f"  [Scraper] Navigating browser to {player_url} for bio data...")
        driver.get(player_url)
        time.sleep(3) # Give some time for dynamic content to load

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # --- Scrape Player Bio Information ---
        bio_list_ul = soup.find('ul', class_='PlayerHeader__Bio_List')
        if bio_list_ul:
            for li in bio_list_ul.find_all('li'):
                label_div = li.find('div', class_='ttu')
                value_div = li.find('div', class_='fw-medium')
                
                if label_div and value_div:
                    label = label_div.text.strip()
                    value = value_div.text.strip() # Default to direct text

                    if label == 'College':
                        college_link = value_div.find('a', class_='AnchorLink')
                        if college_link:
                            value = college_link.text.strip()
                    elif label == 'Status':
                        status_span = value_div.find('span', class_='TextStatus')
                        if status_span:
                            value = status_span.text.strip()
                    
                    # Map scraped labels to desired dictionary keys (now using 'Player' prefix)
                    if label == 'HT/WT':
                        bio_data['PlayerHeightWeight'] = value
                    elif label == 'Birthdate':
                        bio_data['PlayerBirthdate'] = value
                    elif label == 'College':
                        bio_data['PlayerCollege'] = value
                    elif label == 'Draft Info':
                        bio_data['PlayerDraftInfo'] = value
                    elif label == 'Status': 
                        bio_data['PlayerOverallStatus'] = value
            print(f"  [Scraper] Scraped bio data: {bio_data}")
        else:
            print(f"  [Scraper] Warning: PlayerHeader__Bio_List not found for {player_url}.")
        
    except TimeoutException:
        print(f"  [Scraper] Page load timed out for {player_url}. Skipping bio scrape.")
        return None
    except Exception as e: 
        print(f"  [Scraper] An unexpected error occurred during bio scraping {player_url}: {e}. Skipping bio scrape.")
        return None

    return bio_data


# --- Main Script Execution ---
if __name__ == "__main__":
    input_csv_path = os.path.join("combined_depth_charts", "master_nfl_depth_chart.csv")
    output_results_csv = os.path.join(os.path.dirname(input_csv_path), "player_bio_stats_results.csv")
    
    print(f"Starting player bio data scraping from: {input_csv_path}")
    print(f"Results will be saved to: {output_results_csv}")

    processed_players_count = 0
    
    driver = None # Initialize driver outside try block
    output_file = None # Initialize output file handle
    csv_writer = None # Initialize CSV writer

    # --- Resume Logic: Load already processed UIDs ---
    processed_uids = set()
    if os.path.exists(output_results_csv):
        print(f"\n[Resume] Found existing results file: {output_results_csv}")
        try:
            with open(output_results_csv, 'r', encoding='utf-8', newline='') as existing_outfile:
                reader = csv.DictReader(existing_outfile)
                # Define statuses that indicate incomplete/failed processing for bio fields
                failed_bio_statuses = {
                    'N/A', 'N/A (No URL)', 'N/A (Bio Scrape Failed)'
                }
                for row in reader:
                    player_uid = row.get('PlayerUID')
                    if player_uid: 
                        player_htwt_status = row.get('PlayerHeightWeight', 'N/A')
                        # A simple check for HeightWeight can indicate if bio was successfully scraped
                        is_bio_successful = (player_htwt_status not in failed_bio_statuses and
                                             not player_htwt_status.startswith('Error:'))
                        
                        if is_bio_successful:
                            processed_uids.add(player_uid)

            print(f"[Resume] Loaded {len(processed_uids)} previously *successfully scraped* players. Will resume from where we left off.")
        except Exception as e:
            print(f"[Resume] Error reading existing results file ({e}), starting fresh (or appending if file exists).")
            processed_uids = set() # Reset if there's an error reading it

    try:
        # --- Initialize a single headless browser instance ---
        print("\n[Browser Setup] Initializing a single headless Chrome browser...")
        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev_shm_usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30) # Set a timeout for page load
        print("[Browser Setup] Headless browser initialized successfully.")

        # --- Open output CSV file (append mode if exists and resuming, write mode + header if new) ---
        file_mode = 'a' if os.path.exists(output_results_csv) and len(processed_uids) > 0 else 'w'
        output_file = open(output_results_csv, file_mode, encoding='utf-8', newline='')
        
        # Define fieldnames for the new CSV, including bio stats
        fieldnames = ['PlayerName', 'PlayerUID', 'PlayerURL', 
                      'PlayerHeightWeight', 'PlayerBirthdate', 'PlayerCollege', 
                      'PlayerDraftInfo', 'PlayerOverallStatus']
        csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        
        if file_mode == 'w': # Only write header if starting a new file
            csv_writer.writeheader()
            print(f"Output CSV '{output_results_csv}' opened and header written.")
        else:
            # Safeguard: If file exists but header is missing/incomplete, rewrite it.
            with open(output_results_csv, 'r', encoding='utf-8', newline='') as f:
                first_line = f.readline().strip()
                if not first_line or not all(col in first_line.split(',') for col in fieldnames):
                    output_file.close() 
                    output_file = open(output_results_csv, 'w', encoding='utf-8', newline='') 
                    csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                    csv_writer.writeheader()
                    print(f"Output CSV '{output_results_csv}' reopened in write mode and header re-written due to missing/incomplete header.")
                else:
                    print(f"Output CSV '{output_results_csv}' opened in append mode.")


        with open(input_csv_path, 'r', encoding='utf-8', newline='') as infile:
            reader = csv.DictReader(infile)
            
            # Validate essential columns
            essential_columns = ['PlayerURL', 'PlayerName', 'PlayerUID']
            for col in essential_columns:
                if col not in reader.fieldnames:
                    print(f"Error: '{col}' column not found in {input_csv_path}. Please ensure the CSV header is correct.")
                    exit()

            for i, row in enumerate(reader):
                player_name = row['PlayerName']
                player_url = row['PlayerURL']
                player_uid = row['PlayerUID'] 

                # Initialize player_data with defaults
                player_data = {
                    'PlayerName': player_name,
                    'PlayerUID': player_uid,
                    'PlayerURL': player_url,
                    'PlayerHeightWeight': 'N/A',
                    'PlayerBirthdate': 'N/A',
                    'PlayerCollege': 'N/A',
                    'PlayerDraftInfo': 'N/A',
                    'PlayerOverallStatus': 'N/A'
                }

                try:
                    if player_uid in processed_uids:
                        print(f"--- Skipping Player {i + 1}: {player_name} (UID: {player_uid}) - Bio data already scraped ---")
                        processed_players_count += 1 
                        continue 

                    if not player_url or player_url == 'Empty Slot':
                        print(f"\nSkipping player {player_name} (UID: {player_uid}) - No valid PlayerURL found.")
                        player_data.update({
                            'PlayerHeightWeight': 'N/A (No URL)',
                            'PlayerBirthdate': 'N/A (No URL)',
                            'PlayerCollege': 'N/A (No URL)',
                            'PlayerDraftInfo': 'N/A (No URL)',
                            'PlayerOverallStatus': 'N/A (No URL)'
                        })
                        
                    elif player_url: 
                        print(f"\n--- Processing Player {i + 1}: {player_name} (UID: {player_uid}) ---")
                        
                        # --- Scrape Bio Data ---
                        bio_details = get_player_info(driver, player_url) 
                        
                        if bio_details:
                            player_data.update(bio_details) # This will now correctly update with 'Player...' keys
                        else:
                            print(f"  [Scraper] Failed to retrieve bio details for {player_name}.")
                            player_data.update({
                                'PlayerHeightWeight': 'N/A (Scrape Failed)',
                                'PlayerBirthdate': 'N/A (Scrape Failed)',
                                'PlayerCollege': 'N/A (Scrape Failed)',
                                'PlayerDraftInfo': 'N/A (Scrape Failed)',
                                'PlayerOverallStatus': 'N/A (Scrape Failed)'
                            })
                
                except Exception as e: # Catch any unexpected errors for this specific player
                    print(f"\n!!! CRITICAL ERROR processing player {player_name} (UID: {player_uid}): {e} !!!")
                    player_data.update({
                        'PlayerHeightWeight': f'CRITICAL ERROR: {str(e)[:50]}...',
                        'PlayerBirthdate': f'CRITICAL ERROR: {str(e)[:50]}...',
                        'PlayerCollege': f'CRITICAL ERROR: {str(e)[:50]}...',
                        'PlayerDraftInfo': f'CRITICAL ERROR: {str(e)[:50]}...',
                        'PlayerOverallStatus': f'CRITICAL ERROR: {str(e)[:50]}...'
                    })
                    
                # --- Write result to CSV immediately ---
                if csv_writer:
                    csv_writer.writerow(player_data)
                    output_file.flush() # Ensure data is written to disk immediately
                    print(f"  [CSV] Result written for {player_name}.")
                
                processed_players_count += 1

    except FileNotFoundError:
        print(f"Error: The input CSV file '{input_csv_path}' was not found. Please check the path.")
    except WebDriverException as e:
        print(f"Initial WebDriver setup error: {e}")
        print("Please ensure ChromeDriver is installed and its path is correctly configured, or webdriver_manager can find it.")
    except Exception as e:
        print(f"An unexpected error occurred in the main script: {e}")
    finally:
        if driver:
            driver.quit() # Close the browser only once at the end
            print("\n[Browser Cleanup] Headless browser closed.")
        if output_file:
            output_file.close() # Close the output CSV file
            print(f"[CSV] Output CSV '{output_results_csv}' closed.")


    print("\n--- Scraping Summary ---")
    print(f"Total players processed: {processed_players_count}")
    print(f"All results are written to: {output_results_csv}")
    print("\nScript finished.")
