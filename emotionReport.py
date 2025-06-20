import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
import numpy as np
import math
from collections import defaultdict 
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont # Ensure ImageDraw and ImageFont are imported from PIL
import random # For selecting random players
import base64 # Ensure base64 is imported globally here and in functions that need it

# Selenium imports for web scraping
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup
import time
from webdriver_manager.chrome import ChromeDriverManager

# --- Global Mapping for Team Logos ---
TEAM_LOGO_MAP = {
    'Arizona Cardinals': 'ari',
    'Atlanta Falcons': 'atl',
    'Baltimore Ravens': 'bal',
    'Buffalo Bills': 'buf',
    'Carolina Panthers': 'car',
    'Chicago Bears': 'chi',
    'Cincinnati Bengals': 'cin',
    'Cleveland Browns': 'cle',
    'Dallas Cowboys': 'dal',
    'Denver Broncos': 'den',
    'Detroit Lions': 'det',
    'Green Bay Packers': 'gb',
    'Houston Texans': 'hou',
    'Indianapolis Colts': 'ind',
    'Jacksonville Jaguars': 'jac',
    'Kansas City Chiefs': 'kc',
    'Las Vegas Raiders': 'lv',
    'Los Angeles Chargers': 'lac',
    'Los Angeles Rams': 'lar',
    'Miami Dolphins': 'mia',
    'Minnesota Vikings': 'min',
    'New England Patriots': 'ne',
    'New Orleans Saints': 'no',
    'New York Giants': 'nyg',
    'New York Jets': 'nyj',
    'Philadelphia Eagles': 'phi',
    'Pittsburgh Steelers': 'pit',
    'San Francisco 49Ers': 'sf', # Changed 'San Francisco 49ers' to 'San Francisco 49Ers'
    'Seattle Seahawks': 'sea',
    'Tampa Bay Buccaneers': 'tb',
    'Tennessee Titans': 'ten',
    'Washington Commanders': 'wsh' 
}

ESPN_LOGO_BASE_URL = "https://a.espncdn.com/i/teamlogos/nfl/500/"

def get_player_image_base64(driver, player_url, target_size=(200, 200)):
    """
    Fetches an ESPN NFL player's profile page using Selenium, extracts their headshot,
    resizes it, and returns it as a Base64 encoded string.
    Returns (None, None) if image cannot be retrieved or processed.
    """
    # Ensure base64 is available in this function's scope
    import base64 

    image_data_base64 = None
    mime_type = None
    img_buffer = None

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
                            img_buffer = BytesIO() 
                            response = requests.get(image_link, timeout=10)
                            response.raise_for_status() # Raise an HTTPError for bad responses
                            
                            img_pil = Image.open(BytesIO(response.content))
                            img_pil.thumbnail(target_size, Image.Resampling.LANCZOS)
                            
                            output_format = img_pil.format if img_pil.format in ['JPEG', 'PNG', 'GIF'] else 'PNG'
                            img_pil.save(img_buffer, format=output_format) # Save to img_buffer
                            
                            if img_buffer is not None:
                                image_data_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8') # Use img_buffer
                                mime_type = f"image/{output_format.lower()}"
                            else:
                                image_data_base64 = None
                                mime_type = None

                        except requests.exceptions.RequestException as e:
                            print(f"  [ERROR] Request error downloading or processing image from {image_link}: {e}")
                        except Exception as e:
                            print(f"  [ERROR] Generic exception with PIL processing image from {image_link}: {e}")
                
    except TimeoutException:
        print(f"  [ERROR] Page load timed out for {player_url}. Skipping image scrape.")
    except Exception as e:
        print(f"  [ERROR] An unexpected error occurred during image scraping for {player_url}: {e}")

    return image_data_base64, mime_type

def get_team_logo_image(team_name, logo_cache_dir="team_logo_cache", fixed_size=(50, 50)):
    """
    Downloads and caches team logos, resizes them to a fixed_size, and returns the image data.
    """
    if team_name not in TEAM_LOGO_MAP:
        print(f"Warning: Logo abbreviation not found for team '{team_name}'. Skipping logo for this team.")
        return None

    team_abbr = TEAM_LOGO_MAP[team_name]
    local_logo_path = os.path.join(logo_cache_dir, f"{team_abbr}.png")

    if not os.path.exists(local_logo_path):
        if team_name == 'Carolina Panthers': # Specific debug for Panthers
            print(f"  [DEBUG-Panthers] Local logo not found for Carolina Panthers at {local_logo_path}.")
        return None

    try:
        img_pil = Image.open(local_logo_path)
        img_resized = img_pil.resize(fixed_size, Image.Resampling.LANCZOS)
        if team_name == 'Carolina Panthers': # Specific debug for Panthers
            print(f"  [DEBUG-Panthers] Successfully loaded and resized logo for Carolina Panthers from {local_logo_path}.")
        return img_resized
    except Exception as e:
        if team_name == 'Carolina Panthers': # Specific debug for Panthers
            print(f"  [ERROR-Panthers] Error processing cached logo for Carolina Panthers from {local_logo_path}: {e}.")
        return None

def adjust_labels_for_overlap(positions, images_data, max_iterations=500, repulsion_strength=0.1):
    """
    Adjusts the positions of images to prevent overlap using a simple repulsion algorithm.
    
    Args:
        positions (list of tuples): Initial (x, y) coordinates for each image.
        images_data (list of dicts): List containing 'image_obj' (OffsetImage), 'width', 'height' for each logo.
        max_iterations (int): Maximum iterations for the repulsion algorithm.
        repulsion_strength (float): How strongly images repel each other.
    
    Returns:
        list of tuples: Adjusted (x, y) coordinates.
    """
    adjusted_positions = list(positions)
    num_images = len(positions)
    
    if not images_data:
        return positions

    nominal_image_radius_x = 1.0 
    nominal_image_radius_y = 1.0 
    repulsion_strength = 0.1 

    for _ in range(max_iterations):
        moved = False
        for i in range(num_images):
            xi, yi = adjusted_positions[i]
            
            force_x, force_y = 0, 0
            
            for j in range(num_images):
                if i == j:
                    continue
                
                xj, yj = adjusted_positions[j]
                
                dx = xi - xj
                dy = yi - yj
                
                distance = math.sqrt(dx**2 + dy**2)
                
                overlap_threshold_x = (nominal_image_radius_x * 2) * 1.2
                overlap_threshold_y = (nominal_image_radius_y * 2) * 1.2

                if abs(dx) < overlap_threshold_x and abs(dy) < overlap_threshold_y and distance > 0:
                    repulsion_force_magnitude = repulsion_strength / (distance**1.5) 
                    
                    norm_dx = dx / distance
                    norm_dy = dy / distance
                        
                    force_x += norm_dx * repulsion_force_magnitude
                    force_y += norm_dy * repulsion_force_magnitude
            
            new_xi = xi + force_x
            new_yi = yi + force_y
            
            movement_x = (new_xi - xi) * 0.5 
            movement_y = (new_yi - yi) * 0.5 

            if abs(movement_x) > 1e-4 or abs(movement_y) > 1e-4:
                adjusted_positions[i] = (xi + movement_x, yi + movement_y)
                moved = True
        
        if not moved:
            break 

    return adjusted_positions

def generate_emotion_chart_base64(df):
    """
    Generates a bar chart of emotion counts and returns it as a Base64 encoded PNG image.
    """
    import base64 # Explicitly import base64 here

    valid_emotions_order = ['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']
    emotion_counts = df[df['InferredEmotion'].isin(valid_emotions_order)]['InferredEmotion'].value_counts()
    
    if emotion_counts.empty:
        return None

    emotion_counts = emotion_counts.reindex(valid_emotions_order, fill_value=0)

    try:
        fig, ax = plt.subplots(figsize=(10, 6))
    except Exception as e:
        print(f"  [ERROR-Chart1] Failed to create matplotlib figure: {e}")
        return None
    
    bars = ax.bar(emotion_counts.index, emotion_counts.values, color='#FFD700') # Changed bar color to Gold/Yellow
    
    ax.set_title('Distribution of Inferred Player Emotions', fontsize=16, pad=15, color='#F0F8FF') 
    ax.set_xlabel('Emotion', fontsize=12, color='#F0F8FF')
    ax.set_ylabel('Number of Players', fontsize=12, color='#F0F8FF')
    ax.tick_params(axis='x', rotation=45, colors='#F0F8FF') 
    ax.tick_params(axis='y', colors='#F0F8FF') 

    ax.set_facecolor('#20452E') 
    fig.patch.set_facecolor('#20452E') 

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom', fontsize=10, color='#F0F8FF')

    ax.grid(axis='y', linestyle='--', alpha=0.7, color='#66BB6A') 
    plt.tight_layout()

    try:
        buffer = BytesIO() 
        plt.savefig(buffer, format='png', bbox_inches='tight')
    except Exception as e:
        print(f"  [ERROR-Chart1] Failed to save plot to buffer: {e}")
        return None
    finally:
        plt.close(fig) # Always close the figure
    
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8') 
    return f"data:image/png;base64,{image_base64}"

def generate_team_happiness_chart_base64(df_combined_data, logos_dir):
    """
    Generates a scatter plot showing team happiness (Happy vs. Other Emotions)
    using team logos, and returns it as a Base64 encoded PNG image.
    """
    import base64 # Explicitly import base64 here

    try:
        df_combined_data['InferredEmotion'] = df_combined_data['InferredEmotion'].astype(str)

        df_filtered = df_combined_data[
            df_combined_data['InferredEmotion'].notna() & 
            df_combined_data['InferredEmotion'].isin(['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']) &
            df_combined_data['TeamName'].notna() 
        ].copy() 

        # --- Specific Debug for Carolina Panthers ---
        panthers_filtered_data = df_filtered[df_filtered['TeamName'] == 'Carolina Panthers']
        if not panthers_filtered_data.empty:
            print("\n  [DEBUG-Panthers] Carolina Panthers data in df_filtered (before groupby):")
            print(panthers_filtered_data[['PlayerName', 'InferredEmotion', 'TeamName']].head())
            print(f"  [DEBUG-Panthers] Carolina Panthers 'Happy' count in filtered: {(panthers_filtered_data['InferredEmotion'] == 'Happy').sum()}")
            print(f"  [DEBUG-Panthers] Carolina Panthers 'Other_Emotions' count in filtered: {(panthers_filtered_data['InferredEmotion'] != 'Happy').sum()}")
        else:
            print("\n  [DEBUG-Panthers] No Carolina Panthers data found in df_filtered.")


        if df_filtered.empty:
            return None

        team_emotion_counts = df_filtered.groupby('TeamName')['InferredEmotion'].apply(
            lambda x: pd.Series({
                'Happy': (x == 'Happy').sum(),
                'Other_Emotions': x[x != 'Happy'].count() 
            })
        ).unstack(fill_value=0)
        
        team_emotion_counts['Happy'] = team_emotion_counts['Happy'].clip(lower=0)
        team_emotion_counts['Other_Emotions'] = team_emotion_counts['Other_Emotions'].clip(lower=0)

        # --- Specific Debug for Carolina Panthers after calculations ---
        if 'Carolina Panthers' in team_emotion_counts.index:
            panthers_counts = team_emotion_counts.loc['Carolina Panthers']
            print(f"\n  [DEBUG-Panthers] Carolina Panthers emotion counts (after groupby):")
            print(f"    Happy: {panthers_counts.get('Happy', 0)}")
            print(f"    Other_Emotions: {panthers_counts.get('Other_Emotions', 0)}")
        else:
            print("\n  [DEBUG-Panthers] Carolina Panthers not found in team_emotion_counts index.")


        if team_emotion_counts.empty:
            return None

        x_coords = team_emotion_counts['Happy'].values
        y_coords = team_emotion_counts['Other_Emotions'].values
        team_names_for_plot = team_emotion_counts.index.tolist()
        
        initial_positions = [(x, y) for x, y in zip(x_coords, y_coords)]

        images_data = []
        team_logo_objects = {} 
        fixed_logo_size = (50, 50) 

        for team_name in team_names_for_plot:
            logo_pil_img = get_team_logo_image(team_name, logos_dir, fixed_size=fixed_logo_size) 
            if logo_pil_img is not None:
                image_np_array = np.asarray(logo_pil_img)
                image_obj = OffsetImage(image_np_array, zoom=1.0) 
                
                images_data.append({'image_obj': image_obj, 'team_name': team_name, 
                                    'width': fixed_logo_size[0], 'height': fixed_logo_size[1]})
                team_logo_objects[team_name] = image_obj
            

        # --- Specific Debug for Carolina Panthers before adding to plot ---
        if 'Carolina Panthers' in team_names_for_plot:
            print(f"\n  [DEBUG-Panthers] Carolina Panthers is in team_names_for_plot.")
            if 'Carolina Panthers' in team_logo_objects:
                print(f"  [DEBUG-Panthers] Carolina Panthers logo object IS available.")
            else:
                print(f"  [DEBUG-Panthers] Carolina Panthers logo object IS NOT available.")
            idx = team_names_for_plot.index('Carolina Panthers')
            print(f"  [DEBUG-Panthers] Carolina Panthers initial position: {initial_positions[idx]}")
        else:
            print("\n  [DEBUG-Panthers] Carolina Panthers is NOT in team_names_for_plot.")


        try:
            fig, ax = plt.subplots(figsize=(20, 16)) 
        except Exception as e:
            print(f"  [ERROR-Chart2] Failed to create matplotlib figure: {e}")
            return None

        if len(initial_positions) > 1 and images_data:
            adjusted_positions = adjust_labels_for_overlap(initial_positions, images_data)
        else:
            adjusted_positions = initial_positions 
        
        for i, (x_adj, y_adj) in enumerate(adjusted_positions):
            team_name = team_names_for_plot[i]
            if team_name in team_logo_objects: 
                image_obj = team_logo_objects[team_name] 
                ab = AnnotationBbox(image_obj, (x_adj, y_adj), frameon=False, pad=0.0)
                ax.add_artist(ab)
                if team_name == 'Carolina Panthers': # Specific debug for Panthers
                    print(f"  [DEBUG-Panthers] Added logo for Carolina Panthers at ({x_adj:.2f}, {y_adj:.2f}).")
        
        ax.set_xlabel("Number of Players with 'Happy' Emotion", color='#F0F8FF', fontsize=12)
        ax.set_ylabel("Number of Players with 'Other Emotions'", color='#F0F8FF', fontsize=12)
        ax.set_title("NFL Teams: Distribution of Player Emotions (Happy vs. Other)", fontsize=16, pad=15, color='#FFD700')
        
        ax.tick_params(axis='x', colors='#F0F8FF')
        ax.tick_params(axis='y', colors='#F0F8FF')

        ax.set_facecolor('#20452E') 
        fig.patch.set_facecolor('#20452E') 
        
        # FIXED AXIS RANGES AS REQUESTED
        ax.set_xlim(20, 65)
        ax.set_ylim(20, 65)

        ax.grid(True, linestyle='--', alpha=0.7, color='#66BB6A')
        plt.tight_layout()

        try:
            buffer = BytesIO()
            plt.savefig(buffer, format='png') 
        except Exception as e:
            print(f"  [ERROR-Chart2] Failed to save plot to buffer: {e}")
            return None
        finally:
            plt.close(fig) # Always close the figure
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{image_base64}"

    except Exception as e:
        print(f"An unexpected error occurred during team happiness plotting: {e}")
        return None

def generate_player_emotions_report(input_csv_path="combined_depth_charts/master_nfl_depth_chart_with_race.csv", # Changed input file
                                   output_html_path="nfl_player_emotions_report.html",
                                   team_logos_dir="team_logo_cache"): # Removed master_depth_chart_path as it's no longer needed
    """
    Generates an HTML report showcasing NFL players' inferred emotions,
    including a summary chart, featured players for each emotion,
    and a team happiness scatter plot.
    """
    print(f"Starting NFL player emotions report generation from: {input_csv_path}")

    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV file not found at '{input_csv_path}'. Exiting.")
        return

    try:
        df_merged = pd.read_csv(input_csv_path) # Now directly load the merged CSV

        # Ensure PlayerUID columns are of the same type for consistency
        df_merged['PlayerUID'] = df_merged['PlayerUID'].astype(str)

        # --- NEW DEBUGGING FOR CAROLINA PANTHERS (still useful after file change) ---
        print("\n--- DEBUGGING CAROLINA PANTHERS DATA LOADING ---")
        if 'Carolina Panthers' in df_merged['TeamName'].unique():
            print("  'Carolina Panthers' found in df_merged['TeamName'].")
            panthers_data_initial = df_merged[df_merged['TeamName'] == 'Carolina Panthers']
            print("\n  First 5 rows of Carolina Panthers data in df_merged (before filtering for valid emotions):")
            print(panthers_data_initial[['PlayerName', 'TeamName', 'InferredEmotion']].head())
            print("\n  Value counts of InferredEmotion for Carolina Panthers in df_merged (including NaNs):")
            print(panthers_data_initial['InferredEmotion'].value_counts(dropna=False))
        else:
            print("  'Carolina Panthers' NOT found in df_merged['TeamName']. Check input CSVs for team name consistency.")
        print("--- END DEBUGGING CAROLINA PANTHERS DATA LOADING ---\n")

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
        
        # --- Generate Team Happiness Chart ---
        team_happiness_chart_src = generate_team_happiness_chart_base64(df_valid_emotions, team_logos_dir)

        # --- Select Featured Players for each Emotion (aim for diversity) ---
        featured_players_by_emotion = {}
        all_inferred_emotions = ['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']
        
        for emotion in all_inferred_emotions:
            players_for_emotion = df_valid_emotions[df_valid_emotions['InferredEmotion'] == emotion].copy()
            
            if players_for_emotion.empty:
                featured_players_by_emotion[emotion] = []
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
                # Ensure remaining_eligible is initialized correctly at the start of each iteration
                remaining_eligible = players_for_emotion[
                    ~players_for_emotion['PlayerUID'].isin(picked_uids)
                ]
                if remaining_eligible.empty:
                    break # No more unique players to add
                player_to_add = remaining_eligible.sample(1).iloc[0]
                selected_players.append(player_to_add)
                picked_uids.add(player_to_add['PlayerUID'])
            
            featured_players_by_emotion[emotion] = selected_players


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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Player Emotions Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #2D6B5F; /* Dark Green (Field Color) */
            color: #F0F8FF; /* Off-white for general text */
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 1rem;
        }
        .header-section {
            background-color: #013220; /* Very Dark Green */
            color: #FFD700; /* Gold/Yellow for accents */
            padding: 3rem 1rem;
            border-radius: 0.75rem;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2), 0 4px 6px -2px rgba(0, 0, 0, 0.1);
        }
        .section-card {
            background-color: #064420; /* Darker Green for sections */
            border-radius: 0.75rem; /* rounded-xl */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); /* shadow-md */
            padding: 2rem;
            margin-bottom: 2rem;
            color: #F0F8FF; /* Off-white text */
        }
        .player-card {
            background-color: #125740; /* Slightly lighter green for cards */
            border-radius: 0.75rem; /* rounded-xl */
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.05); /* shadow-md */
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            border: 1px solid #1E794F; /* Subtle border */
            color: #F0F8FF; /* Off-white text */
        }
        .player-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.15), 0 4px 6px -2px rgba(0, 0, 0, 0.08);
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
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        /* Emotion specific colors (can adjust to fit football theme if desired) */
        .emotion-disgust { color: #FF4500; } /* OrangeRed for disgust */
        .emotion-happy { color: #ADFF2F; } /* GreenYellow for happy */
        .emotion-neutral { color: #F0F8FF; } /* Off-white for neutral */
        .emotion-sad { color: #87CEEB; } /* SkyBlue for sad */
        .emotion-angry { color: #FF6347; } /* Tomato for angry */
        .emotion-surprise { color: #FFFF00; } /* Yellow for surprise */
        .emotion-fear { color: #BA55D3; } /* MediumPurple for fear */
        .emotion-text { font-weight: 600; } /* semibold */

        h1, h2, h3 {
            color: #FFD700; /* Gold for titles */
        }
        strong {
            color: #F0F8FF; /* Off-white for labels */
        }
        a {
            color: #FFD700; /* Gold for links */
        }
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
            <h2 class="text-3xl font-bold text-center mb-6">Overall Emotion Distribution Across Playerbase</h2>
            <img src="{emotion_chart_src}" alt="Overall Emotion Distribution Chart" class="chart-image">
            <p class="text-center text-gray-300 text-sm mt-4">This chart provides a summary of the most prevalent inferred emotions across all analyzed players, showcasing the distribution of different emotional states within the league.</p>
        </div>
            """)
        
        # Add the team happiness scatter plot section
        if team_happiness_chart_src:
            report_content.append(f"""
        <div class="section-card">
            <h2 class="text-3xl font-bold text-center mb-6 mt-12">Team Emotion Distribution: Happy vs. Other</h2>
            <img src="{team_happiness_chart_src}" alt="Team Emotion Distribution Chart" class="chart-image">
            <p class="text-center text-gray-300 text-sm mt-4">This chart visualizes the balance of 'Happy' players versus players exhibiting 'Other Emotions' for each NFL team, with team logos marking their position.</p>
        </div>
            """)


        # Iterate through each emotion to create a section for featured players
        for emotion in all_inferred_emotions:
            featured_players = featured_players_by_emotion.get(emotion, [])
            if not featured_players:
                continue

            report_content.append(f"""
            <div class="section-card">
                <h2 class="text-3xl font-bold text-center mb-6 mt-12">Featured Players Exhibiting '{emotion.title()}' Emotion</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            """)

            for player_data in featured_players:
                player_name = player_data.get('PlayerName', 'N/A')
                player_position = player_data.get('PrimaryPosition', 'N/A') 
                player_team = player_data.get('TeamName', 'N/A') 

                player_url = player_data.get('PlayerURL', '')
                inferred_emotion = player_data.get('InferredEmotion', 'N/A')
                emotion_confidence = player_data.get('EmotionConfidence', 'N/A')
                
                player_birthdate = player_data.get('PlayerBirthdate', 'N/A') 

                player_height_inches = player_data.get('PlayerHeightInches', 'N/A')
                player_weight_lbs = player_data.get('PlayerWeightLBS', 'N/A')
                player_college = player_data.get('PlayerCollege', 'N/A')
                draft_year = player_data.get('DraftYear', 'N/A')
                draft_position = player_data.get('DraftPosition', 'N/A')
                draft_organization = player_data.get('DraftOrganization', 'N/A')
                player_overall_status = player_data.get('PlayerOverallStatus', 'N/A')

                # Handle Undrafted Logic
                draft_info_display = "Undrafted"
                if pd.notna(draft_year) and str(draft_year) != 'N/A' and \
                   pd.notna(draft_position) and str(draft_position) != 'N/A' and \
                   pd.notna(draft_organization) and str(draft_organization) != 'N/A':
                    draft_info_display = f"{int(draft_year)} {draft_position} ({draft_organization})"
                elif pd.isna(draft_year) and pd.isna(draft_position) and pd.isna(draft_organization):
                     draft_info_display = "Undrafted"
                elif str(draft_year) == 'N/A' and str(draft_position) == 'N/A' and str(draft_organization) == 'N/A':
                     draft_info_display = "Undrafted"


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
                    <h3 class="text-xl font-semibold mb-0">{player_name}</h3>
                    <p class="text-md text-gray-300 mb-2">{player_position}</p> 
                    <p class="text-sm mb-4 font-medium">Team: {player_team}</p> 
                    <div class="text-left w-full space-y-2 text-base">
                        <p><strong>Emotion:</strong> <span class="{emotion_class} emotion-text">{inferred_emotion}</span> (Confidence: {emotion_confidence})</p>
                        <p><strong>Birthdate:</strong> {player_birthdate}</p>
                        <p><strong>Height:</strong> {player_height_inches} inches</p>
                        <p><strong>Weight:</strong> {player_weight_lbs} lbs</p>
                        <p><strong>College:</strong> {player_college}</p>
                        <p><strong>Draft Info:</strong> {draft_info_display}</p>
                        <p><strong>Status:</strong> {player_overall_status}</p>
                        <p class="text-xs text-gray-400 mt-4"><a href="{player_url}" target="_blank" class="hover:underline">View ESPN Profile</a></p>
                    </div>
                </div>
                """)
            
            report_content.append("""
                </div>
            </div>
            """)

        # HTML Footer
        report_content.append("""
        <p class="text-center text-gray-400 mt-12 text-sm pb-8">Report generated on """ + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </div>
</body>
</html>
        """)

        # Write the report to an HTML file
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write("".join(report_content))
        
        print(f"\nReport saved successfully to: {output_html_path}")

    except FileNotFoundError:
        print(f"Error: A required CSV file was not found. Please check paths: '{input_csv_path}'.") # Updated error message
    except Exception as e:
        print(f"An unexpected error occurred during report generation: {e}")
    finally:
        if 'driver' in locals() and driver: # Ensure driver exists before quitting
            driver.quit() # Close the browser
            print("[Browser Cleanup] Headless browser closed.")

# --- Main execution ---
if __name__ == "__main__":
    # Define paths
    # Changed input_csv_path to use master_nfl_depth_chart_with_race.csv
    processed_data_file = os.path.join("combined_depth_charts", "master_nfl_depth_chart_with_race.csv") 
    
    # master_depth_chart_file is no longer needed as the input CSV is already merged
    # master_depth_chart_file = os.path.join("combined_depth_charts", "master_nfl_depth_chart.csv")
    
    # Updated path for real team logos
    team_logos_dir = os.path.join("race_composition_charts", "team_logos") 

    generate_player_emotions_report(processed_data_file, team_logos_dir=team_logos_dir) # Removed master_depth_chart_file from arguments
