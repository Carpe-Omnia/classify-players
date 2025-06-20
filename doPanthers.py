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
import pandas as pd # Import pandas for DataFrame filtering

# --- Function to scrape player image URL and bio data ---
def get_player_image_url(driver, player_url):
    """
    Fetches an ESPN NFL player's profile page using an existing Selenium driver instance
    to handle dynamic content and extracts the URL of their headshot image
    and basic biographical information.
    """
    image_url = None
    bio_data = {
        'HeightWeight': 'N/A',
        'Birthdate': 'N/A',
        'College': 'N/A',
        'DraftInfo': 'N/A',
        'OverallStatus': 'N/A' # General active/inactive status from bio
    }

    try:
        print(f"  [Scraper] Navigating browser to {player_url}...")
        driver.get(player_url)
        time.sleep(3) # Give some time for dynamic content to load

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # --- Scrape Player Headshot Image URL ---
        player_header_image_div = soup.find('div', class_='PlayerHeader__Image')
        if player_header_image_div:
            headshot_figure = player_header_image_div.find('figure', class_='PlayerHeader__HeadShot')
            if headshot_figure:
                img_tag = headshot_figure.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    temp_image_url = img_tag['src']
                    if temp_image_url.startswith('http') and not temp_image_url.startswith('data:image/gif'):
                        image_url = temp_image_url
                        print(f"  [Scraper] Found player headshot URL: {image_url}")
            if not image_url:
                print(f"  [Scraper] Error: No valid HTTP image URL found within PlayerHeader__HeadShot figure for {player_url}.")
        else:
            print(f"  [Scraper] Error: div with class 'PlayerHeader__Image' not found on the page for {player_url}.")

        # --- Scrape Player Bio Information ---
        bio_list_ul = soup.find('ul', class_='PlayerHeader__Bio_List')
        if bio_list_ul:
            for li in bio_list_ul.find_all('li'):
                label_div = li.find('div', class_='ttu')
                value_div = li.find('div', class_='fw-medium')
                
                if label_div and value_div:
                    label = label_div.text.strip()
                    value = value_div.text.strip() # Default to direct text

                    # Specific handling for 'College' (to get name from link if present)
                    if label == 'College':
                        college_link = value_div.find('a', class_='AnchorLink')
                        if college_link:
                            value = college_link.text.strip()
                    # Specific handling for 'Status' (to get text from span if present)
                    elif label == 'Status':
                        status_span = value_div.find('span', class_='TextStatus')
                        if status_span:
                            value = status_span.text.strip()
                    
                    # Map scraped labels to desired dictionary keys
                    if label == 'HT/WT':
                        bio_data['HeightWeight'] = value
                    elif label == 'Birthdate':
                        bio_data['Birthdate'] = value
                    elif label == 'College':
                        bio_data['College'] = value
                    elif label == 'Draft Info':
                        bio_data['DraftInfo'] = value
                    elif label == 'Status': # This is the overall player status, not injury
                        bio_data['OverallStatus'] = value
            print(f"  [Scraper] Scraped bio data: {bio_data}")
        else:
            print(f"  [Scraper] Warning: PlayerHeader__Bio_List not found for {player_url}.")
        
    except TimeoutException:
        print(f"  [Scraper] Page load timed out for {player_url}. Skipping image/bio scrape.")
        return None, None
    except Exception as e: # Catch any other general exceptions during navigation/parsing
        print(f"  [Scraper] An unexpected error occurred during scraping {player_url}: {e}. Skipping image/bio scrape.")
        return None, None

    return image_url, bio_data


# --- Main Script Execution ---
if __name__ == "__main__":
    input_master_csv_path = os.path.join("combined_depth_charts", "master_nfl_depth_chart.csv")
    output_results_csv = os.path.join(os.path.dirname(input_master_csv_path), "player_race_analysis_results.csv")
    image_download_dir = "temp_player_images" # Directory to temporarily store downloaded images
    
    os.makedirs(image_download_dir, exist_ok=True) # Create temp directory

    print(f"Starting player face analysis for Carolina Panthers from: {input_master_csv_path}")
    print(f"Results will be saved to: {output_results_csv}")
    print(f"Temporary images will be stored in: {image_download_dir}")

    processed_players_count = 0
    
    driver = None # Initialize driver outside try block
    output_file = None # Initialize output file handle
    csv_writer = None # Initialize CSV writer

    # --- Load all players and filter for Carolina Panthers ---
    try:
        df_master = pd.read_csv(input_master_csv_path)
        # Ensure PlayerUID column is string type for consistent filtering and resume logic
        df_master['PlayerUID'] = df_master['PlayerUID'].astype(str) 

        # Filter for Carolina Panthers players only
        panthers_df = df_master[df_master['TeamName'] == 'Carolina Panthers'].copy()
        
        if panthers_df.empty:
            print("No Carolina Panthers players found in the master depth chart. Exiting.")
            exit()
        
        print(f"Found {len(panthers_df)} Carolina Panthers players to process.")
        
    except FileNotFoundError:
        print(f"Error: Master depth chart CSV file not found at '{input_master_csv_path}'. Exiting.")
        exit()
    except Exception as e:
        print(f"Error loading or filtering master depth chart: {e}. Exiting.")
        exit()


    # --- Resume Logic: Load already processed UIDs ---
    processed_uids = set()
    if os.path.exists(output_results_csv):
        print(f"\n[Resume] Found existing results file: {output_results_csv}")
        try:
            with open(output_results_csv, 'r', encoding='utf-8', newline='') as existing_outfile:
                reader = csv.DictReader(existing_outfile)
                # Define statuses that indicate incomplete/failed processing for any field
                failed_statuses = {
                    'N/A', 'N/A (No URL)', 'N/A (Scrape Failed)', 'N/A (Empty Download)', 
                    'N/A (No Probabilities)', 'N/A (No Face Detected)', 'N/A (Bio Scrape Failed)'
                }
                for row in reader:
                    player_uid = row.get('PlayerUID')
                    if player_uid: # Ensure PlayerUID exists
                        inferred_race_status = row.get('InferredRace', 'N/A')
                        inferred_age_status = str(row.get('InferredAge', 'N/A')) # Convert to string for consistent comparison
                        inferred_emotion_status = row.get('InferredEmotion', 'N/A')
                        player_htwt_status = row.get('PlayerHeightWeight', 'N/A')
                        player_birthdate_status = row.get('PlayerBirthdate', 'N/A')
                        player_college_status = row.get('PlayerCollege', 'N/A')
                        player_draftinfo_status = row.get('PlayerDraftInfo', 'N/A')
                        player_overall_status = row.get('PlayerOverallStatus', 'N/A')


                        # Check if ALL three relevant analysis fields AND bio fields indicate successful processing
                        is_race_successful = not inferred_race_status.startswith('N/A (') and \
                                             not inferred_race_status.startswith('Error:') and \
                                             inferred_race_status not in failed_statuses

                        is_age_successful = (inferred_age_status != 'N/A' and 
                                             not inferred_age_status.startswith('Error:') and
                                             inferred_age_status not in failed_statuses)
                        
                        is_emotion_successful = not inferred_emotion_status.startswith('N/A (') and \
                                                not inferred_emotion_status.startswith('Error:') and \
                                                inferred_emotion_status not in failed_statuses
                        
                        is_bio_successful = (player_htwt_status not in failed_statuses and
                                             player_birthdate_status not in failed_statuses and
                                             player_college_status not in failed_statuses and
                                             player_draftinfo_status not in failed_statuses and
                                             player_overall_status not in failed_statuses and
                                             not player_htwt_status.startswith('Error:') and
                                             not player_birthdate_status.startswith('Error:') and
                                             not player_college_status.startswith('Error:') and
                                             not player_draftinfo_status.startswith('Error:') and
                                             not player_overall_status.startswith('Error:'))
                        
                        # Only add to processed_uids if ALL requested analysis types AND bio scraping are successful
                        if is_race_successful and is_age_successful and is_emotion_successful and is_bio_successful:
                            processed_uids.add(player_uid)

            print(f"[Resume] Loaded {len(processed_uids)} previously *fully successful* processed players. Will resume from where we left off.")
        except Exception as e:
            print(f"[Resume] Error reading existing results file ({e}), starting fresh. Old results will be overwritten if in 'w' mode.")
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
        
        # Updated fieldnames to include new columns for bio data
        fieldnames = ['PlayerName', 'PlayerUID', 'InferredRace', 'RaceConfidence', 
                      'InferredAge', 'InferredEmotion', 'EmotionConfidence', 
                      'PlayerHeightWeight', 'PlayerBirthdate', 'PlayerCollege', 
                      'PlayerDraftInfo', 'PlayerOverallStatus', 'PlayerURL']
        csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        
        if file_mode == 'w': # Only write header if starting a new file
            csv_writer.writeheader()
            print(f"Output CSV '{output_results_csv}' opened and header written.")
        else:
            # Check if header is already present, if not, write it. This is a safeguard
            # if the file exists but was empty or corrupt.
            with open(output_results_csv, 'r', encoding='utf-8', newline='') as f:
                first_line = f.readline().strip()
                # A robust check for header presence
                if not first_line or not all(col in first_line.split(',') for col in fieldnames):
                    output_file.close() # Close in append mode
                    output_file = open(output_results_csv, 'w', encoding='utf-8', newline='') # Reopen in write mode
                    csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                    csv_writer.writeheader()
                    print(f"Output CSV '{output_results_csv}' reopened in write mode and header re-written due to missing/incomplete header.")
                else:
                    print(f"Output CSV '{output_results_csv}' opened in append mode.")


        # Iterate over the filtered Carolina Panthers DataFrame
        for i, row in enumerate(panthers_df.itertuples(index=False)): # Use itertuples for faster iteration
            player_name = getattr(row, 'PlayerName', 'N/A')
            player_url = getattr(row, 'PlayerURL', '')
            player_uid = getattr(row, 'PlayerUID', 'N/A')

            # Initialize player_analysis_data with defaults for *this* player loop iteration
            player_analysis_data = {
                'PlayerName': player_name,
                'PlayerUID': player_uid,
                'PlayerURL': player_url,
                'InferredRace': 'N/A (Skipped/Default)', 
                'RaceConfidence': '0.00%',
                'InferredAge': 'N/A',
                'InferredEmotion': 'N/A',
                'EmotionConfidence': '0.00%',
                'PlayerHeightWeight': 'N/A',
                'PlayerBirthdate': 'N/A',
                'PlayerCollege': 'N/A',
                'PlayerDraftInfo': 'N/A',
                'PlayerOverallStatus': 'N/A'
            }

            # --- NEW: Place entire player processing in a try-except block ---
            try:
                if player_uid in processed_uids:
                    print(f"--- Skipping Player {i + 1}: {player_name} (UID: {player_uid}) - Already successfully processed ---")
                    processed_players_count += 1 
                    continue # Skip to the next player

                if not player_url or player_url == 'Empty Slot':
                    print(f"\nSkipping player {player_name} (UID: {player_uid}) - No valid PlayerURL found.")
                    # Mark all analysis and bio fields as N/A if no URL
                    player_analysis_data.update({
                        'InferredRace': 'N/A (No URL)',
                        'RaceConfidence': '0.00%',
                        'InferredAge': 'N/A (No URL)',
                        'InferredEmotion': 'N/A (No URL)',
                        'EmotionConfidence': '0.00%',
                        'PlayerHeightWeight': 'N/A (No URL)',
                        'PlayerBirthdate': 'N/A (No URL)',
                        'PlayerCollege': 'N/A (No URL)',
                        'PlayerDraftInfo': 'N/A (No URL)',
                        'PlayerOverallStatus': 'N/A (No URL)'
                    })
                    
                elif player_url: # Only proceed if there's a valid URL to attempt
                    print(f"\n--- Processing Player {i + 1}: {player_name} (UID: {player_uid}) ---")
                    # --- Step 1 & 2: Scrape Image URL & Download Image/Bio (pass the shared driver) ---
                    image_link, bio_details = get_player_image_url(driver, player_url) 
                    
                    # Populate bio data from scraper
                    if bio_details:
                        player_analysis_data['PlayerHeightWeight'] = bio_details['HeightWeight']
                        player_analysis_data['PlayerBirthdate'] = bio_details['Birthdate']
                        player_analysis_data['PlayerCollege'] = bio_details['College']
                        player_analysis_data['PlayerDraftInfo'] = bio_details['DraftInfo']
                        player_analysis_data['PlayerOverallStatus'] = bio_details['OverallStatus']
                    else:
                        # Mark bio fields as failed if bio_details are not retrieved
                        player_analysis_data.update({
                            'PlayerHeightWeight': 'N/A (Bio Scrape Failed)',
                            'PlayerBirthdate': 'N/A (Bio Scrape Failed)',
                            'PlayerCollege': 'N/A (Bio Scrape Failed)',
                            'PlayerDraftInfo': 'N/A (Bio Scrape Failed)',
                            'PlayerOverallStatus': 'N/A (Bio Scrape Failed)'
                        })


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
                                    # Actions to include 'age', 'emotion', and 'race'
                                    demography = DeepFace.analyze(
                                        img_path=image_filepath,
                                        actions=['age', 'emotion', 'race'], 
                                        detector_backend='opencv',
                                        enforce_detection=False 
                                    )

                                    if demography:
                                        # Age Analysis
                                        inferred_age = demography[0].get('age')
                                        if inferred_age is not None:
                                            player_analysis_data['InferredAge'] = inferred_age
                                        else:
                                            player_analysis_data['InferredAge'] = 'N/A'

                                        # Emotion Analysis
                                        emotion_probabilities = demography[0].get('emotion', {})
                                        if emotion_probabilities:
                                            most_likely_emotion = max(emotion_probabilities, key=emotion_probabilities.get)
                                            emotion_confidence = emotion_probabilities[most_likely_emotion] * 100
                                            player_analysis_data['InferredEmotion'] = most_likely_emotion.title()
                                            player_analysis_data['EmotionConfidence'] = f"{emotion_confidence:.2f}%"
                                        else:
                                            player_analysis_data['InferredEmotion'] = 'N/A'
                                            player_analysis_data['EmotionConfidence'] = 'N/A'

                                        # Race Analysis (Existing logic)
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
                                        # Mark all analysis fields as N/A if no face detected
                                        player_analysis_data.update({
                                            'InferredRace': 'N/A (No Face Detected)',
                                            'RaceConfidence': 'N/A',
                                            'InferredAge': 'N/A (No Face Detected)',
                                            'InferredEmotion': 'N/A (No Face Detected)',
                                            'EmotionConfidence': 'N/A'
                                        })

                                except Exception as e:
                                    print(f"  [DeepFace] Error during DeepFace analysis for {player_name}: {e}")
                                    # Mark all analysis fields as error
                                    player_analysis_data.update({
                                        'InferredRace': f'Error: {str(e)[:50]}...', 
                                        'RaceConfidence': 'N/A',
                                        'InferredAge': f'Error: {str(e)[:50]}...',
                                        'InferredEmotion': f'Error: {str(e)[:50]}...',
                                        'EmotionConfidence': 'N/A'
                                    })
                                
                                # --- Step 4: Delete the image ---
                                try:
                                    os.remove(image_filepath)
                                    print(f"  [Cleanup] Deleted temporary image: {image_filename}")
                                except OSError as e:
                                    print(f"  [Cleanup] Error deleting image {image_filename}: {e}")
                            else:
                                print(f"  [Downloader] Downloaded image data is empty for {player_name}. Skipping DeepFace analysis and cleanup.")
                                # Mark all analysis fields as empty download error
                                player_analysis_data.update({
                                    'InferredRace': 'N/A (Empty Download)',
                                    'RaceConfidence': '0.00%',
                                    'InferredAge': 'N/A (Empty Download)',
                                    'InferredEmotion': 'N/A (Empty Download)',
                                    'EmotionConfidence': '0.00%'
                                })

                        except Exception as e:
                            print(f"  [Downloader] Failed to download or save image for {player_name}: {e}. Skipping DeepFace analysis and cleanup.")
                            # Mark all analysis fields as download error
                            player_analysis_data.update({
                                'InferredRace': f'N/A (Download Error: {str(e)[:50]}...)',
                                'RaceConfidence': '0.00%',
                                'InferredAge': f'N/A (Download Error: {str(e)[:50]}...)',
                                'InferredEmotion': f'N/A (Download Error: {str(e)[:50]}...)',
                                'EmotionConfidence': '0.00%'
                            })
                    else:
                        print(f"  [Scraper] No valid image URL retrieved for {player_name}. Skipping DeepFace analysis.")
                        # Mark all analysis fields as scrape failed
                        player_analysis_data.update({
                            'InferredRace': 'N/A (Scrape Failed)', 
                            'RaceConfidence': '0.00%',
                            'InferredAge': 'N/A (Scrape Failed)',
                            'InferredEmotion': 'N/A (Scrape Failed)',
                            'EmotionConfidence': '0.00%'
                        })
            
            except Exception as e: # Catch any unexpected errors for this specific player
                print(f"\n!!! CRITICAL ERROR processing player {player_name} (UID: {player_uid}): {e} !!!")
                # Mark all fields as critical error if a general exception occurs
                player_analysis_data.update({
                    'InferredRace': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'RaceConfidence': 'N/A',
                    'InferredAge': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'InferredEmotion': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'EmotionConfidence': 'N/A',
                    'PlayerHeightWeight': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'PlayerBirthdate': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'PlayerCollege': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'PlayerDraftInfo': f'CRITICAL ERROR: {str(e)[:50]}...',
                    'PlayerOverallStatus': f'CRITICAL ERROR: {str(e)[:50]}...'
                })
                
            # --- Write result to CSV immediately (outside inner try-except for robust write) ---
            if csv_writer:
                csv_writer.writerow(player_analysis_data)
                output_file.flush() # Ensure data is written to disk immediately
                print(f"  [CSV] Result written for {player_name}.")
            
            processed_players_count += 1

    except FileNotFoundError:
        print(f"Error: The input CSV file '{input_master_csv_path}' was not found. Please check the path.")
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
    print(f"All results are written to: {output_results_csv}")
    print("\nScript finished.")
