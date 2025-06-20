import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
import numpy as np
import math
from collections import defaultdict 
import requests
from PIL import Image, ImageDraw, ImageFont # Ensure ImageDraw and ImageFont are imported from PIL

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
    'San Francisco 49ers': 'sf', # Corrected spelling
    'Seattle Seahawks': 'sea',
    'Tampa Bay Buccaneers': 'tb',
    'Tennessee Titans': 'ten',
    'Washington Commanders': 'wsh' 
}

ESPN_LOGO_BASE_URL = "https://a.espncdn.com/i/teamlogos/nfl/500/"

def get_team_logo_image(team_name, logo_cache_dir="team_logo_cache", fixed_size=(50, 50)):
    """
    Downloads and caches team logos, resizes them to a fixed_size, and returns the image data.
    """
    if team_name not in TEAM_LOGO_MAP:
        print(f"Warning: Logo abbreviation not found for team '{team_name}'. Skipping logo for this team.")
        return None

    team_abbr = TEAM_LOGO_MAP[team_name]
    logo_url = f"{ESPN_LOGO_BASE_URL}{team_abbr}.png"
    
    os.makedirs(logo_cache_dir, exist_ok=True)
    local_logo_path = os.path.join(logo_cache_dir, f"{team_abbr}.png")

    # Download if not cached
    if not os.path.exists(local_logo_path):
        try:
            response = requests.get(logo_url, timeout=5)
            response.raise_for_status()
            with open(local_logo_path, 'wb') as f:
                f.write(response.content)
        except requests.exceptions.RequestException as e:
            print(f"  Error downloading logo for {team_name}: {e}. Skipping logo.")
            return None

    try:
        # Open, resize, and convert to numpy array for matplotlib
        img_pil = Image.open(local_logo_path)
        img_resized = img_pil.resize(fixed_size, Image.Resampling.LANCZOS) # Use LANCZOS for high quality downsampling
        
        # Return the resized PIL Image object (NumPy array conversion happens in OffsetImage)
        return img_resized
    except Exception as e:
        print(f"  Error processing cached logo {local_logo_path}: {e}. Skipping logo.")
        return None

def get_image(path, zoom=0.1):
    """
    Loads an image from a path and returns an OffsetImage object.
    (Note: This function is not used in the main plotting logic for team logos
    as get_team_logo_image directly returns a PIL image to be used by OffsetImage.)
    """
    try:
        img = mpimg.imread(path)
        return OffsetImage(img, zoom=zoom)
    except FileNotFoundError:
        print(f"Warning: Logo not found at {path}")
        return OffsetImage(np.zeros((10, 10, 3)), zoom=zoom)

def adjust_labels_for_overlap(positions, images_data, max_iterations=500, repulsion_strength=0.1, boundary_padding=0.1):
    """
    Adjusts the positions of images to prevent overlap using a simple repulsion algorithm.
    
    Args:
        positions (list of tuples): Initial (x, y) coordinates for each image.
        images_data (list of dicts): List containing 'image_obj' (OffsetImage), 'width', 'height' for each logo.
        max_iterations (int): Maximum iterations for the repulsion algorithm.
        repulsion_strength (float): How strongly images repel each other.
        boundary_padding (float): Padding to keep logos within plot bounds.
    
    Returns:
        list of tuples: Adjusted (x, y) coordinates.
    """
    adjusted_positions = list(positions)
    num_images = len(positions)
    
    # Use the provided fixed_size (width, height) from images_data to estimate nominal radius
    if images_data:
        nominal_image_width_pixels = images_data[0]['width']
        nominal_image_height_pixels = images_data[0]['height']

        # These values are empirical and might need tuning based on actual data range and figure size.
        nominal_image_radius_x = 1.0 # Approximate radius in X data units
        nominal_image_radius_y = 1.0 # Approximate radius in Y data units
    else: 
        nominal_image_radius_x = 0.5
        nominal_image_radius_y = 0.5


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


def create_team_happiness_scatter(processed_data_path, master_depth_chart_path, logos_dir):
    """
    Generates a scatter plot showing team happiness (Happy vs. Other Emotions)
    using team logos, after merging processed player data with master depth chart.
    """
    try:
        # Load processed player data (with emotions)
        df_processed = pd.read_csv(processed_data_path)
        print(f"Loaded processed player data from: {processed_data_path} ({len(df_processed)} rows)")

        # Load master depth chart (with team names)
        df_master = pd.read_csv(master_depth_chart_path)
        print(f"Loaded master depth chart from: {master_depth_chart_path} ({len(df_master)} rows)")

        # --- Merge the two dataframes on PlayerUID ---
        df_master_unique_players = df_master.drop_duplicates(subset=['PlayerUID'])
        
        df_merged = pd.merge(
            df_processed, 
            df_master_unique_players[['PlayerUID', 'TeamName']], 
            on='PlayerUID', 
            how='left' # Keep all players from processed_data, add TeamName if match found
        )
        print(f"Merged dataframes. Total rows after merge: {len(df_merged)}")

        # --- DIAGNOSTIC: Check Carolina Panthers in merged DataFrame ---
        panthers_in_merged = df_merged[df_merged['TeamName'] == 'Carolina Panthers']
        print(f"  [DIAGNOSTIC] Carolina Panthers players in df_merged: {len(panthers_in_merged)} rows.")
        if not panthers_in_merged.empty:
            print(panthers_in_merged[['PlayerName', 'TeamName', 'InferredEmotion']].head())


        # Filter out rows where InferredEmotion or TeamName is missing/invalid
        df_filtered = df_merged[
            df_merged['InferredEmotion'].notna() & 
            df_merged['InferredEmotion'].isin(['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']) &
            df_merged['TeamName'].notna() # Ensure TeamName is present after merge
        ].copy() 
        print(f"Filtered data for valid emotions and teams: {len(df_filtered)} rows")

        # --- DIAGNOSTIC: Check Carolina Panthers in filtered DataFrame ---
        panthers_in_filtered = df_filtered[df_filtered['TeamName'] == 'Carolina Panthers']
        print(f"  [DIAGNOSTIC] Carolina Panthers players in df_filtered: {len(panthers_in_filtered)} rows.")
        if not panthers_in_filtered.empty:
            print(panthers_in_filtered[['PlayerName', 'TeamName', 'InferredEmotion']].head())


        if df_filtered.empty:
            print("No valid player data with inferred emotion and team found for plotting after filtering. Exiting.")
            return

        # Calculate happy and other emotions counts per team
        team_emotion_counts = df_filtered.groupby('TeamName')['InferredEmotion'].apply(
            lambda x: pd.Series({
                'Happy': (x == 'Happy').sum(),
                'Other_Emotions': (x != 'Happy').sum()
            })
        ).unstack(fill_value=0)

        if team_emotion_counts.empty:
            print("No valid team emotion counts found to plot. Exiting.")
            return

        # --- DIAGNOSTIC: Check Carolina Panthers in team_emotion_counts ---
        if 'Carolina Panthers' in team_emotion_counts.index:
            print(f"  [DIAGNOSTIC] Carolina Panthers emotion counts: {team_emotion_counts.loc['Carolina Panthers']}")
        else:
            print(f"  [DIAGNOSTIC] Carolina Panthers not found in team_emotion_counts. This means they have no players with valid emotion data after filtering.")

        # Prepare data for plotting
        x_coords = team_emotion_counts['Happy'].values
        y_coords = team_emotion_counts['Other_Emotions'].values
        team_names_for_plot = team_emotion_counts.index.tolist()
        
        # Get initial positions for the logos
        initial_positions = [(x, y) for x, y in zip(x_coords, y_coords)]

        # Load logos and store dimensions for overlap adjustment
        images_data = []
        team_logo_objects = {} 
        fixed_logo_size = (50, 50) # Define fixed size once

        for team_name in team_names_for_plot:
            logo_pil_img = get_team_logo_image(team_name, logos_dir, fixed_size=fixed_logo_size) 
            # --- DIAGNOSTIC: Check if Carolina Panthers logo is loaded ---
            if team_name == 'Carolina Panthers':
                print(f"  [DIAGNOSTIC] Attempting to load logo for Carolina Panthers. Result: {'Success' if logo_pil_img is not None else 'Failed'}")

            if logo_pil_img is not None:
                image_np_array = np.asarray(logo_pil_img)
                image_obj = OffsetImage(image_np_array, zoom=1.0) 
                
                images_data.append({'image_obj': image_obj, 'team_name': team_name, 
                                    'width': fixed_logo_size[0], 'height': fixed_logo_size[1]})
                team_logo_objects[team_name] = image_obj
            else:
                print(f"Skipping plotting for team '{team_name}' due to missing logo.")


        # --- Plotting ---
        fig, ax = plt.subplots(figsize=(14, 10))

        if len(initial_positions) > 1 and images_data:
            adjusted_positions = adjust_labels_for_overlap(initial_positions, images_data)
        else:
            adjusted_positions = initial_positions 

        # Plot logos at adjusted positions
        for i, (x_adj, y_adj) in enumerate(adjusted_positions):
            team_name = team_names_for_plot[i]
            if team_name == 'Carolina Panthers':
                print(f"  [DIAGNOSTIC] Carolina Panthers plotting at adjusted coordinates: ({x_adj}, {y_adj})")
            
            if team_name in team_logo_objects: 
                image_obj = team_logo_objects[team_name] 
                ab = AnnotationBbox(image_obj, (x_adj, y_adj), frameon=False, pad=0.0)
                ax.add_artist(ab)
        
        # Set labels and title
        ax.set_xlabel("Number of Players with 'Happy' Emotion")
        ax.set_ylabel("Number of Players with 'Other Emotions'")
        ax.set_title("NFL Teams: Distribution of Player Emotions (Happy vs. Other)")
        
        # Adjust x and y limits for better spacing around logos
        final_x_coords = [p[0] for p in adjusted_positions]
        final_y_coords = [p[1] for p in adjusted_positions]

        if final_x_coords and final_y_coords: 
            x_min_data, x_max_data = min(final_x_coords), max(final_x_coords)
            y_min_data, y_max_data = min(final_y_coords), max(final_y_coords)
            
            x_pad = (x_max_data - x_min_data) * 0.20 if (x_max_data - x_min_data) > 0 else 2
            y_pad = (y_max_data - y_min_data) * 0.20 if (y_max_data - y_min_data) > 0 else 2
            
            ax.set_xlim(x_min_data - x_pad, x_max_data + x_pad)
            ax.set_ylim(y_min_data - y_pad, y_max_data + y_pad)
        else:
            ax.set_xlim(0, 10) 
            ax.set_ylim(0, 10)

        ax.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.show()

    except FileNotFoundError as e:
        print(f"Error: Required input file not found: {e}. Please ensure both CSV files are in the 'combined_depth_charts' directory.")
    except Exception as e:
        print(f"An unexpected error occurred during plotting: {e}")

# --- Main execution ---
if __name__ == "__main__":
    # Define paths
    processed_data_file = os.path.join("combined_depth_charts", "processed_player_data.csv")
    master_depth_chart_file = os.path.join("combined_depth_charts", "master_nfl_depth_chart.csv")
    team_logos_dir = os.path.join("race_composition_charts", "team_logos")

    # Create dummy logo files for testing if they don't exist
    if not os.path.exists(team_logos_dir):
        os.makedirs(team_logos_dir)
    
    dummy_teams = list(TEAM_LOGO_MAP.keys()) 
    
    for team_name in dummy_teams:
        team_abbr = TEAM_LOGO_MAP[team_name]
        dummy_logo_path = os.path.join(team_logos_dir, f"{team_abbr}.png")
        if not os.path.exists(dummy_logo_path):
            try:
                img = Image.new('RGBA', (100, 100), (0, 0, 0, 0)) # Transparent background
                draw = ImageDraw.Draw(img)
                try:
                    # Use textbbox instead of textsize
                    bbox = draw.textbbox((0, 0), team_abbr, font=ImageFont.truetype("arial.ttf", 40))
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    # Calculate position to center the text
                    x_pos = (100 - text_width) / 2
                    y_pos = (100 - text_height) / 2
                    draw.text((x_pos, y_pos), team_abbr, font=ImageFont.truetype("arial.ttf", 40), fill=(255, 0, 0, 255)) 
                except IOError: # Fallback font if "arial.ttf" is not found
                    font = ImageFont.load_default()
                    # Recalculate bbox and position for default font
                    bbox = draw.textbbox((0,0), team_abbr, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x_pos = (100 - text_width) / 2
                    y_pos = (100 - text_height) / 2
                    draw.text((x_pos, y_pos), team_abbr, font=font, fill=(255, 0, 0, 255))

                img.save(dummy_logo_path)
                print(f"Created dummy logo for {team_abbr} at {dummy_logo_path}")
            except ImportError:
                print("Pillow not installed. Cannot create dummy logos. Please install Pillow (`pip install Pillow`) or provide real logos.")
                break 
            except Exception as e:
                print(f"Could not create dummy logo for {team_name} ({team_abbr}): {e}")
                break

    create_team_happiness_scatter(processed_data_file, master_depth_chart_file, team_logos_dir)
