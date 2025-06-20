import pandas as pd
import os
import base64
import requests
from io import BytesIO
from PIL import Image # For image processing (resizing, format conversion)
import matplotlib.pyplot as plt # For plotting
import random # For selecting random players

# Selenium imports for web scraping
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup
import time
from webdriver_manager.chrome import ChromeDriverManager

def get_player_image_base64(driver, player_url, target_size=(200, 200)):
    """
    Fetches an ESPN NFL player's profile page using Selenium, extracts their headshot,
    resizes it, and returns it as a Base64 encoded string.
    Returns (None, None) if image cannot be retrieved or processed.
    """
    image_data_base64 = None
    mime_type = None

    try:
        # Navigate to the player URL using the provided driver
        driver.get(player_url)
        time.sleep(2) # Give some time for dynamic content to load

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        player_header_image_div = soup.find('div', class_='PlayerHeader__Image')
        if player_header_image_div:
            headshot_figure = player_header_image_div.find('figure', class_='PlayerHeader__HeadShot')
            if headshot_figure:
                img_tag = headshot_figure.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    image_link = img_tag['src']
                    if image_link.startswith('http') and not image_link.startswith('data:image/gif'):
                        try:
                            # Download the image content
                            response = requests.get(image_link, timeout=10)
                            response.raise_for_status() # Raise an HTTPError for bad responses
                            
                            # Open image with PIL
                            img_pil = Image.open(BytesIO(response.content))
                            
                            # Resize image, maintaining aspect ratio
                            img_pil.thumbnail(target_size, Image.Resampling.LANCZOS)
                            
                            # Convert to BytesIO to get Base64
                            buffered = BytesIO()
                            # Use img_pil.format or default to 'PNG'
                            output_format = img_pil.format if img_pil.format in ['JPEG', 'PNG', 'GIF'] else 'PNG'
                            img_pil.save(buffered, format=output_format)
                            
                            image_data_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                            mime_type = f"image/{output_format.lower()}"
                            # print(f"  Successfully retrieved and encoded image for {player_url}")
                        except requests.exceptions.RequestException as e:
                            print(f"  Error downloading or processing image from {image_link}: {e}")
                        except Exception as e:
                            print(f"  Error with PIL processing image from {image_link}: {e}")
                    else:
                        print(f"  No valid HTTP image URL found for {player_url} or it's a GIF placeholder.")
                else:
                    print(f"  <img> tag or 'src' attribute not found within PlayerHeader__HeadShot figure for {player_url}.")
            else:
                print(f"  <figure class='PlayerHeader__HeadShot'> not found within PlayerHeader__Image div for {player_url}.")
        else:
            print(f"  div with class 'PlayerHeader__Image' not found on the page for {player_url}.")
        
    except TimeoutException:
        print(f"  Page load timed out for {player_url}. Skipping image scrape.")
    except Exception as e:
        print(f"  An unexpected error occurred during image scraping for {player_url}: {e}")

    return image_data_base64, mime_type

def generate_emotion_chart_base64(df):
    """
    Generates a bar chart of emotion counts and returns it as a Base64 encoded PNG image.
    """
    # Filter for valid emotions (assuming these are the only ones DeepFace infers)
    valid_emotions_order = ['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']
    emotion_counts = df[df['InferredEmotion'].isin(valid_emotions_order)]['InferredEmotion'].value_counts()
    
    if emotion_counts.empty:
        print("No valid emotion data found for the summary chart.")
        return None

    # Reindex to ensure all valid emotions are present, even if count is 0
    emotion_counts = emotion_counts.reindex(valid_emotions_order, fill_value=0)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(emotion_counts.index, emotion_counts.values, color='skyblue')
    
    ax.set_title('Distribution of Inferred Player Emotions', fontsize=16, pad=15)
    ax.set_xlabel('Emotion', fontsize=12)
    ax.set_ylabel('Number of Players', fontsize=12)
    ax.tick_params(axis='x', rotation=45) # Rotate x-axis labels for better readability
    
    # Add value labels on top of bars
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom', fontsize=10)

    ax.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    # Save the plot to a BytesIO object
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig) # Close the figure to free up memory
    buffer.seek(0)
    
    # Encode to Base64
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{image_base64}"


def generate_player_emotions_report(input_csv_path="combined_depth_charts/processed_player_data.csv",
                                   master_depth_chart_path="combined_depth_charts/master_nfl_depth_chart.csv", # Added master depth chart path
                                   output_html_path="nfl_player_emotions_report.html"):
    """
    Generates an HTML report showcasing NFL players' inferred emotions,
    including a summary chart and featured players for each emotion.
    """
    print(f"Starting NFL player emotions report generation from: {input_csv_path}")

    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV file not found at '{input_csv_path}'. Exiting.")
        return
    if not os.path.exists(master_depth_chart_path):
        print(f"Error: Master depth chart file not found at '{master_depth_chart_path}'. Exiting.")
        return

    try:
        df_processed = pd.read_csv(input_csv_path)
        df_master = pd.read_csv(master_depth_chart_path)

        # Ensure PlayerUID columns are of the same type for merging
        df_processed['PlayerUID'] = df_processed['PlayerUID'].astype(str)
        df_master['PlayerUID'] = df_master['PlayerUID'].astype(str)

        # Merge dataframes to get TeamName and PrimaryPosition
        # Prioritize master_depth_chart's TeamName and PrimaryPosition for each player UID
        df_merged = pd.merge(
            df_processed, 
            df_master[['PlayerUID', 'TeamName', 'PrimaryPosition']].drop_duplicates(subset=['PlayerUID']), # Drop duplicates in master for clean merge
            on='PlayerUID', 
            how='left'
        )
        
        # Filter for valid emotion data rows only
        df_valid_emotions = df_merged[
            df_merged['InferredEmotion'].notna() & 
            df_merged['InferredEmotion'].isin(['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust'])
        ].copy()

        if df_valid_emotions.empty:
            print("No valid player emotion data found in the dataset. Report will be mostly empty.")
            return

        # --- Generate Emotion Summary Chart ---
        emotion_chart_src = generate_emotion_chart_base64(df_valid_emotions)
        
        # --- Select Featured Players for each Emotion (aim for diversity) ---
        featured_players_by_emotion = {}
        all_inferred_emotions = ['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']
        
        for emotion in all_inferred_emotions:
            players_for_emotion = df_valid_emotions[df_valid_emotions['InferredEmotion'] == emotion].copy()
            
            if players_for_emotion.empty:
                featured_players_by_emotion[emotion] = []
                print(f"No players found for emotion: {emotion}")
                continue
            
            selected_players = []
            
            # Try to pick one Black, one White, and one other race player
            races_to_pick = ['Black', 'White', 'Asian', 'Middle Eastern', 'Latino_Hispanic', 'Indian']
            picked_uids = set() # To prevent duplicate players if a player has multiple race entries (unlikely but good practice)
            
            # Prioritize picking one of each diverse race if available
            for race in races_to_pick:
                eligible_players = players_for_emotion[
                    (players_for_emotion['InferredRace'] == race) & 
                    (~players_for_emotion['PlayerUID'].isin(picked_uids))
                ]
                if not eligible_players.empty:
                    # Pick a random player from this race
                    player_to_add = eligible_players.sample(1).iloc[0]
                    selected_players.append(player_to_add)
                    picked_uids.add(player_to_add['PlayerUID'])
                    if len(selected_players) >= 3: # Limit to 3 featured players per emotion
                        break
            
            # If less than 3 players selected, fill with random unique players from the remaining pool
            while len(selected_players) < 3 and len(selected_players) < len(players_for_emotion):
                remaining_eligible = players_for_emotion[
                    ~players_for_emotion['PlayerUID'].isin(picked_uids)
                ]
                if remaining_eligible.empty:
                    break # No more unique players to add
                player_to_add = remaining_eligible.sample(1).iloc[0]
                selected_players.append(player_to_add)
                picked_uids.add(player_to_add['PlayerUID'])
            
            featured_players_by_emotion[emotion] = selected_players
            print(f"Featured {len(selected_players)} players for '{emotion}' emotion.")


        # --- Selenium Setup (initialized once) ---
        print("\n[Browser Setup] Initializing headless Chrome browser for image scraping...")
        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev_shm_usage")
        chrome_options.add_argument("--window-size=1920,1080") # Set a consistent window size

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(20) # Shorter timeout for individual image fetches
        print("[Browser Setup] Headless browser initialized.")

        report_content = []
        
        # HTML Header
        report_content.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Player Emotions Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #e2e8f0; /* Light gray-blue */
            color: #374151; /* Dark gray */
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 1rem;
        }
        .header-section {
            background-color: #1a202c; /* Dark navy */
            color: white;
            padding: 3rem 1rem;
            border-radius: 0.75rem;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .section-card {
            background-color: white;
            border-radius: 0.75rem; /* rounded-xl */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); /* shadow-md */
            padding: 2rem;
            margin-bottom: 2rem;
        }
        .player-card {
            background-color: #f8fafc; /* Lighter white for cards */
            border-radius: 0.75rem; /* rounded-xl */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.05); /* shadow-md */
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            border: 1px solid #e2e8f0; /* Subtle border */
        }
        .player-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .player-image {
            width: 100%;
            height: 200px; /* Fixed height for consistency */
            object-fit: cover; /* Cover the area, cropping if necessary */
            border-top-left-radius: 0.75rem;
            border-top-right-radius: 0.75rem;
        }
        .chart-image {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 0 auto;
            border-radius: 0.5rem;
        }
        .emotion-disgust { color: #dc2626; } /* red-600 */
        .emotion-happy { color: #10b981; } /* emerald-500 */
        .emotion-neutral { color: #4b5563; } /* gray-700 */
        .emotion-sad { color: #6366f1; } /* indigo-500 */
        .emotion-angry { color: #f59e0b; } /* amber-500 */
        .emotion-surprise { color: #06b6d4; } /* cyan-500 */
        .emotion-fear { color: #7c3aed; } /* violet-600 */
        .emotion-text { font-weight: 600; } /* semibold */
    </style>
</head>
<body class="p-4 sm:p-8">
    <div class="container mx-auto">
        <div class="header-section">
            <h1 class="text-4xl sm:text-5xl font-bold mb-4">NFL Player Emotions Report</h1>
            <p class="text-lg sm:text-xl text-gray-300">
                A visual exploration of inferred emotions among professional football players.
            </p>
        </div>
        """)

        # Add the emotion summary chart section
        if emotion_chart_src:
            report_content.append(f"""
        <div class="section-card">
            <h2 class="text-3xl font-bold text-center text-gray-800 mb-6">Overall Emotion Distribution Across Playerbase</h2>
            <img src="{emotion_chart_src}" alt="Overall Emotion Distribution Chart" class="chart-image">
            <p class="text-center text-gray-600 text-sm mt-4">This chart provides a summary of the most prevalent inferred emotions across all analyzed players, showcasing the distribution of different emotional states within the league.</p>
        </div>
            """)
        
        # Iterate through each emotion to create a section for featured players
        for emotion in all_inferred_emotions:
            featured_players = featured_players_by_emotion.get(emotion, [])
            if not featured_players:
                print(f"No featured players to display for '{emotion}' emotion.")
                continue

            report_content.append(f"""
            <div class="section-card">
                <h2 class="text-3xl font-bold text-center text-gray-800 mb-6 mt-12">Featured Players Exhibiting '{emotion.title()}' Emotion</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            """)

            for player_data in featured_players:
                player_name = player_data.get('PlayerName', 'N/A')
                player_position = player_data.get('PrimaryPosition', 'N/A') 
                player_team = player_data.get('TeamName', 'N/A') 

                player_url = player_data.get('PlayerURL', '')
                inferred_emotion = player_data.get('InferredEmotion', 'N/A')
                emotion_confidence = player_data.get('EmotionConfidence', 'N/A')
                
                # Use player_birthdate instead of inferred_age
                player_birthdate = player_data.get('PlayerBirthdate', 'N/A') 

                player_height_inches = player_data.get('PlayerHeightInches', 'N/A')
                player_weight_lbs = player_data.get('PlayerWeightLBS', 'N/A')
                player_college = player_data.get('PlayerCollege', 'N/A')
                draft_year = player_data.get('DraftYear', 'N/A')
                draft_position = player_data.get('DraftPosition', 'N/A')
                draft_organization = player_data.get('DraftOrganization', 'N/A')
                player_overall_status = player_data.get('PlayerOverallStatus', 'N/A')

                print(f"  Scraping image for featured player: {player_name} (Emotion: {inferred_emotion})...")
                image_base64, image_mime_type = None, None
                if player_url and player_url != 'N/A (No URL)':
                    image_base64, image_mime_type = get_player_image_base64(driver, player_url)

                img_src = f"data:{image_mime_type};base64,{image_base64}" if image_base64 and image_mime_type else "https://placehold.co/200x200/cccccc/ffffff?text=Image+N/A"
                
                # Dynamic class for emotion color
                emotion_class = f"emotion-{inferred_emotion.lower()}"

                report_content.append(f"""
                <div class="player-card p-6 flex flex-col items-center text-center">
                    <img src="{img_src}" alt="{player_name}" class="player-image mb-4 rounded-md">
                    <h3 class="text-xl font-semibold text-gray-900 mb-0">{player_name}</h3>
                    <p class="text-md text-gray-600 mb-2">{player_position}</p> 
                    <p class="text-sm text-gray-500 mb-4 font-medium">Team: {player_team}</p> 
                    <div class="text-left w-full space-y-2 text-base">
                        <p><strong>Emotion:</strong> <span class="{emotion_class} emotion-text">{inferred_emotion}</span> (Confidence: {emotion_confidence})</p>
                        <p><strong>Birthdate:</strong> {player_birthdate}</p>
                        <p><strong>Height:</strong> {player_height_inches} inches</p>
                        <p><strong>Weight:</strong> {player_weight_lbs} lbs</p>
                        <p><strong>College:</strong> {player_college}</p>
                        <p><strong>Draft Info:</strong> {draft_year} {draft_position} ({draft_organization})</p>
                        <p><strong>Status:</strong> {player_overall_status}</p>
                        <p class="text-xs text-gray-400 mt-4"><a href="{player_url}" target="_blank" class="hover:underline text-blue-500">View ESPN Profile</a></p>
                    </div>
                </div>
                """)
            
            report_content.append("""
                </div>
            </div>
            """)

        # HTML Footer
        report_content.append("""
        <p class="text-center text-gray-500 mt-12 text-sm pb-8">Report generated on """ + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </div>
</body>
</html>
        """)

        # Write the report to an HTML file
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write("".join(report_content))
        
        print(f"\nReport saved successfully to: {output_html_path}")

    except FileNotFoundError:
        print(f"Error: A required CSV file was not found. Please check paths: '{input_csv_path}' and '{master_depth_chart_path}'.")
    except Exception as e:
        print(f"An unexpected error occurred during report generation: {e}")
    finally:
        if 'driver' in locals() and driver: # Ensure driver exists before quitting
            driver.quit() # Close the browser
            print("[Browser Cleanup] Headless browser closed.")

# --- Main execution ---
if __name__ == "__main__":
    generate_player_emotions_report()
