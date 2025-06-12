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
from deepface import DeepFace

# --- Function to scrape player image URL (modified to accept a shared driver) ---
def get_player_image_url(driver, player_url):
    """
    Fetches an ESPN NFL player's profile page using an existing Selenium driver instance
    to handle dynamic content and extracts the URL of their headshot image.
    Specifically targets the <img> tag within the <figure class="PlayerHeader__HeadShot"> element.
    """
    try:
        print(f"  [Scraper] Navigating browser to {player_url}...")
        driver.get(player_url)
        time.sleep(3) # Give some time for dynamic content to load

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        player_header_image_div = soup.find('div', class_='PlayerHeader__Image')
        
        if player_header_image_div:
            headshot_figure = player_header_image_div.find('figure', class_='PlayerHeader__HeadShot')

            if headshot_figure:
                img_tag = headshot_figure.find('img')
                
                if img_tag and 'src' in img_tag.attrs:
                    image_url = img_tag['src']
                    if image_url.startswith('http') and not image_url.startswith('data:image/gif'):
                        return image_url
            print(f"  [Scraper] Error: No valid HTTP image URL found within PlayerHeader__HeadShot figure for {player_url}.")
            return None # Fallback if specific image not found
        print(f"  [Scraper] Error: div with class 'PlayerHeader__Image' not found on the page for {player_url}.")
        return None # Fallback if main div not found
        
    except TimeoutException:
        print(f"  [Scraper] Page load timed out for {player_url}. Skipping image scrape.")
        return None
    except Exception as e: # Catch any other general exceptions during navigation/parsing
        print(f"  [Scraper] An unexpected error occurred during scraping {player_url}: {e}. Skipping image scrape.")
        return None


# --- Main Script Execution ---
if __name__ == "__main__":
    input_csv_path = os.path.join("combined_depth_charts", "master_nfl_depth_chart.csv")
    output_results_csv = os.path.join(os.path.dirname(input_csv_path), "player_race_analysis_results.csv")
    image_download_dir = "temp_player_images" # Directory to temporarily store downloaded images
    
    os.makedirs(image_download_dir, exist_ok=True) # Create temp directory

    print(f"Starting player face analysis from: {input_csv_path}")
    print(f"Results will be saved to: {output_results_csv}")
    print(f"Temporary images will be stored in: {image_download_dir}")

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
                # Define statuses that indicate incomplete/failed processing
                # This set ensures we re-process players who had errors or incomplete data
                failed_statuses = {
                    'N/A (No URL)', 'N/A (Scrape Failed)', 'N/A (Empty Download)', 
                    'N/A (No Probabilities)', 'N/A (No Face Detected)'
                }
                for row in reader:
                    if 'PlayerUID' in row and 'InferredRace' in row:
                        inferred_race_status = row['InferredRace']
                        # Only add to processed_uids if the processing was truly successful/complete
                        if not inferred_race_status.startswith('N/A (') and \
                           not inferred_race_status.startswith('Error:') and \
                           inferred_race_status not in failed_statuses:
                            processed_uids.add(row['PlayerUID'])
            print(f"[Resume] Loaded {len(processed_uids)} previously *successfully* processed players. Will resume from where we left off.")
        except Exception as e:
            print(f"[Resume] Error reading existing results file ({e}), starting fresh. Old results will be overwritten if in 'w' mode.")
            processed_uids = set() # Reset if there's an error reading it

    try:
        # --- Initialize a single headless browser instance ---
        print("\n[Browser Setup] Initializing a single headless Chrome browser...")
        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30) # Set a timeout for page load
        print("[Browser Setup] Headless browser initialized successfully.")

        # --- Open output CSV file (append mode if exists and resuming, write mode + header if new) ---
        file_mode = 'a' if os.path.exists(output_results_csv) and len(processed_uids) > 0 else 'w'
        output_file = open(output_results_csv, file_mode, encoding='utf-8', newline='')
        fieldnames = ['PlayerName', 'PlayerUID', 'InferredRace', 'RaceConfidence', 'PlayerURL']
        csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        
        if file_mode == 'w': # Only write header if starting a new file
            csv_writer.writeheader()
            print(f"Output CSV '{output_results_csv}' opened and header written.")
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

                # Initialize player_analysis_data with defaults for *this* player loop iteration
                player_analysis_data = {
                    'PlayerName': player_name,
                    'PlayerUID': player_uid,
                    'PlayerURL': player_url,
                    'InferredRace': 'N/A (Skipped/Default)', # Default status
                    'RaceConfidence': '0.00%'
                }

                # --- NEW: Place entire player processing in a try-except block ---
                try:
                    if player_uid in processed_uids:
                        print(f"--- Skipping Player {i + 1}: {player_name} (UID: {player_uid}) - Already successfully processed ---")
                        processed_players_count += 1 
                        continue # Skip to the next player

                    if not player_url or player_url == 'Empty Slot':
                        print(f"\nSkipping player {player_name} (UID: {player_uid}) - No valid PlayerURL found.")
                        player_analysis_data['InferredRace'] = 'N/A (No URL)'
                        # No need to write/flush here, the general catch-all will handle it
                        
                    elif player_url: # Only proceed if there's a valid URL to attempt
                        print(f"\n--- Processing Player {i + 1}: {player_name} (UID: {player_uid}) ---")
                        # --- Step 1 & 2: Scrape Image URL & Download Image (pass the shared driver) ---
                        image_link = get_player_image_url(driver, player_url) 
                        
                        if image_link:
                            image_filename = f"{player_uid}.png" 
                            image_filepath = os.path.join(image_download_dir, image_filename)
                            
                            try:
                                print(f"  [Downloader] Attempting to download image from: {image_link}")
                                image_data = requests.get(image_link, timeout=10).content
                                
                                data_size = len(image_data)
                                print(f"  [Downloader] Downloaded image data size: {data_size} bytes")

                                if data_size > 0:
                                    with open(image_filepath, "wb") as f:
                                        f.write(image_data)
                                    print(f"  [Downloader] Image downloaded and saved to {image_filepath}")
                                    
                                    # --- Step 3: Analyze Face with DeepFace ---
                                    print(f"  [DeepFace] Analyzing face for {player_name}...")
                                    try:
                                        demography = DeepFace.analyze(
                                            img_path=image_filepath,
                                            actions=['race'],
                                            detector_backend='opencv',
                                            enforce_detection=False 
                                        )

                                        if demography:
                                            race_probabilities = demography[0].get('race', {})
                                            
                                            if race_probabilities:
                                                most_likely_race = max(race_probabilities, key=race_probabilities.get)
                                                confidence = race_probabilities[most_likely_race] * 100
                                                
                                                print(f"  [DeepFace] Inferred Race for {player_name}: {most_likely_race.title()} (Confidence: {confidence:.2f}%)")
                                                player_analysis_data['InferredRace'] = most_likely_race.title()
                                                player_analysis_data['RaceConfidence'] = f"{confidence:.2f}%"
                                            else:
                                                print(f"  [DeepFace] Race inference not available for {player_name} (no race probabilities).")
                                                player_analysis_data['InferredRace'] = 'N/A (No Probabilities)'
                                                player_analysis_data['RaceConfidence'] = 'N/A'
                                        else:
                                            print(f"  [DeepFace] No faces detected in image for {player_name}. Skipping analysis.")
                                            player_analysis_data['InferredRace'] = 'N/A (No Face Detected)'
                                            player_analysis_data['RaceConfidence'] = 'N/A'

                                    except Exception as e:
                                        print(f"  [DeepFace] Error during DeepFace analysis for {player_name}: {e}")
                                        player_analysis_data['InferredRace'] = f'Error: {str(e)[:50]}...' 
                                        player_analysis_data['RaceConfidence'] = 'N/A'
                                    
                                    # --- Step 4: Delete the image ---
                                    try:
                                        os.remove(image_filepath)
                                        print(f"  [Cleanup] Deleted temporary image: {image_filename}")
                                    except OSError as e:
                                        print(f"  [Cleanup] Error deleting image {image_filename}: {e}")
                                else:
                                    print(f"  [Downloader] Downloaded image data is empty for {player_name}. Skipping DeepFace analysis and cleanup.")
                                    player_analysis_data['InferredRace'] = 'N/A (Empty Download)'
                                    player_analysis_data['RaceConfidence'] = '0.00%'

                            except Exception as e:
                                print(f"  [Downloader] Failed to download or save image for {player_name}: {e}. Skipping DeepFace analysis and cleanup.")
                                player_analysis_data['InferredRace'] = f'N/A (Download Error: {str(e)[:50]}...)'
                                player_analysis_data['RaceConfidence'] = '0.00%'
                        else:
                            print(f"  [Scraper] No valid image URL retrieved for {player_name}. Skipping DeepFace analysis.")
                            player_analysis_data['InferredRace'] = 'N/A (Scrape Failed)' # Already default, but explicit
                            player_analysis_data['RaceConfidence'] = '0.00%'
                
                except Exception as e: # Catch any unexpected errors for this specific player
                    print(f"\n!!! CRITICAL ERROR processing player {player_name} (UID: {player_uid}): {e} !!!")
                    player_analysis_data['InferredRace'] = f'CRITICAL ERROR: {str(e)[:50]}...'
                    player_analysis_data['RaceConfidence'] = 'N/A'
                    
                # --- Write result to CSV immediately (outside inner try-except for robust write) ---
                if csv_writer:
                    csv_writer.writerow(player_analysis_data)
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


    print("\n--- Analysis Summary ---")
    print(f"Total players processed: {processed_players_count}")
    print("\n--- Detailed Results ---")
    # This section will now just confirm where the results are saved, as they're written row by row
    print(f"All results are written to: {output_results_csv}")
    print("\nScript finished.")
