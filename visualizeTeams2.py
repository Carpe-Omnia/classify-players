import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import requests
from io import BytesIO
from PIL import Image # Import Pillow for image resizing
import numpy as np # Import numpy for array conversions
from collections import defaultdict # For grouping overlapping points

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
    'San Francisco 49Ers': 'sf',
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
        print(f"Warning: Logo not found for team '{team_name}'. Skipping logo for this team.")
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
        
        # Convert the resized PIL Image object directly to a NumPy array
        return np.asarray(img_resized) 
    except Exception as e:
        print(f"  Error processing cached logo {local_logo_path}: {e}. Skipping logo.")
        return None


def visualize_team_race_composition(input_csv_filename="master_nfl_depth_chart_with_race.csv",
                                     output_charts_dir="race_composition_charts",
                                     output_plot_filename="team_white_vs_black_players.png"):
    """
    Generates a scatter plot showing the number of White players vs. Black players for each NFL team,
    using resized team logos as data points.
    Includes logic to slightly offset overlapping team logos.
    """
    
    input_dir = "combined_depth_charts" 
    input_csv_path = os.path.join(input_dir, input_csv_filename)
    output_plot_path = os.path.join(output_charts_dir, output_plot_filename)
    logo_cache_dir = os.path.join(output_charts_dir, "team_logos") 
    
    os.makedirs(output_charts_dir, exist_ok=True)
    os.makedirs(logo_cache_dir, exist_ok=True)

    print(f"Loading data from: {input_csv_path}")
    print(f"Generating plot and saving to: {output_plot_path}")

    try:
        df = pd.read_csv(input_csv_path)

        # --- Data Cleaning and Preparation ---
        df['PlayerUID'] = df['PlayerUID'].astype(str)
        
        invalid_race_statuses = {
            'N/A (No URL)', 'N/A (Scrape Failed)', 'N/A (Empty Download)', 
            'N/A (No Probabilities)', 'N/A (No Face Detected)', 'N/A (Skipped/Default)'
        }
        
        df_valid_race = df[~df['InferredRace'].isin(invalid_race_statuses) & ~df['InferredRace'].str.startswith('Error:', na=False)].copy()
        df_valid_race = df_valid_race[df_valid_race['PlayerName'].notna() & (df_valid_race['PlayerName'] != '-')].copy()

        if df_valid_race.empty:
            print("No valid player data with inferred race found for analysis after filtering. Exiting.")
            return

        # --- Calculate White and Black Player Counts per Team ---
        df_white_black = df_valid_race[df_valid_race['InferredRace'].isin(['White', 'Black'])].copy()

        if df_white_black.empty:
            print("No White or Black players with valid race data found for plotting. Exiting.")
            return

        team_composition = df_white_black.groupby('TeamName')['InferredRace'].value_counts().unstack(fill_value=0)
        
        if 'White' not in team_composition.columns:
            team_composition['White'] = 0
        if 'Black' not in team_composition.columns:
            team_composition['Black'] = 0

        team_composition = team_composition.sort_index()

        print("\n--- Team White vs. Black Player Counts ---")
        print(team_composition[['White', 'Black']].to_string())

        # --- Overlap Resolution Logic ---
        # Store original and adjusted positions
        team_positions = {}
        # Group teams by their initial (x, y) coordinates
        overlapping_groups = defaultdict(list)

        for team_name in team_composition.index:
            num_white = team_composition.loc[team_name, 'White']
            num_black = team_composition.loc[team_name, 'Black']
            team_positions[team_name] = {'original_x': num_white, 'original_y': num_black}
            overlapping_groups[(num_white, num_black)].append(team_name)

        # Define offsets for overlapping points
        # These are fractions of a unit to spread out logos
        offset_distance = 0.75 # Adjust this value to control spacing
        offsets = [
            (0, 0),                        # Center (for single or first in group)
            (offset_distance, offset_distance),  # Top-right
            (-offset_distance, offset_distance), # Top-left
            (offset_distance, -offset_distance), # Bottom-right
            (-offset_distance, -offset_distance),# Bottom-left
            (0, offset_distance),          # Up
            (0, -offset_distance),         # Down
            (offset_distance, 0),          # Right
            (-offset_distance, 0)          # Left
            # Add more offsets if more than 9 teams could overlap at the exact same spot
        ]

        # Apply offsets to overlapping teams
        for (x, y), teams_at_coords in overlapping_groups.items():
            if len(teams_at_coords) > 1:
                print(f"Detected overlap at ({x}, {y}) for teams: {', '.join(teams_at_coords)}. Applying offsets.")
                for i, team_name in enumerate(teams_at_coords):
                    if i < len(offsets):
                        ox, oy = offsets[i]
                        team_positions[team_name]['adjusted_x'] = x + ox
                        team_positions[team_name]['adjusted_y'] = y + oy
                    else:
                        # Fallback for more than 9 overlaps, just stack for now or create more offsets
                        team_positions[team_name]['adjusted_x'] = x + offsets[0][0] # No offset
                        team_positions[team_name]['adjusted_y'] = y + offsets[0][1]
                        print(f"  Warning: Not enough unique offsets for all teams at ({x}, {y}). Team '{team_name}' might still overlap.")
            else:
                # No overlap, use original coordinates
                team_name = teams_at_coords[0]
                team_positions[team_name]['adjusted_x'] = x
                team_positions[team_name]['adjusted_y'] = y


        # --- Generate Scatter Plot with Logos ---
        fig, ax = plt.subplots(figsize=(16, 12), facecolor='#f0f0f0') # Larger figure, light gray background

        # Add team logos as data points using adjusted coordinates
        for team_name in team_composition.index:
            adjusted_x = team_positions[team_name]['adjusted_x']
            adjusted_y = team_positions[team_name]['adjusted_y']
            
            # Get the resized logo image
            logo_img = get_team_logo_image(team_name, logo_cache_dir)
            
            if logo_img is not None:
                # Create an OffsetImage object with the resized logo image
                imagebox = OffsetImage(logo_img, zoom=1.0) 
                # Create an AnnotationBbox to place the image at specific coordinates
                ab = AnnotationBbox(imagebox, (adjusted_x, adjusted_y), frameon=False, pad=0.0)
                ax.add_artist(ab)
            
        ax.set_title('NFL Team Composition: Number of White vs. Black Players ', fontsize=18, pad=20)
        ax.set_xlabel('Number of White Players', fontsize=14)
        ax.set_ylabel('Number of Black Players', fontsize=14)
        
        # Adjust axes limits based on data range, adding some padding
        # Ensure limits encompass all original and adjusted points
        all_x_coords = [data['adjusted_x'] for data in team_positions.values()]
        all_y_coords = [data['adjusted_y'] for data in team_positions.values()]

        ax.set_xlim(min(all_x_coords) - 2, max(all_x_coords) + 2)
        ax.set_ylim(min(all_y_coords) - 2, max(all_y_coords) + 2)

        # Set integer ticks for clarity, if appropriate for your data range
        ax.set_xticks(range(int(ax.get_xlim()[0]), int(ax.get_xlim()[1]) + 1, 5))
        ax.set_yticks(range(int(ax.get_ylim()[0]), int(ax.get_ylim()[1]) + 1, 5))

        ax.grid(True, linestyle='--', alpha=0.6) # Add grid for easier readability
        
        plt.tight_layout()
        plt.savefig(output_plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Plot saved: {output_plot_path}")

    except FileNotFoundError:
        print(f"Error: The input CSV file '{input_csv_path}' was not found. Please ensure the 'combined_depth_charts' directory exists and contains '{input_csv_filename}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    visualize_team_race_composition()
