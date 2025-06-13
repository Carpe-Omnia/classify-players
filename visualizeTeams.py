import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe # For text outlines

def visualize_team_race_composition(input_csv_filename="master_nfl_depth_chart_with_race.csv",
                                     output_charts_dir="race_composition_charts",
                                     output_plot_filename="team_white_vs_black_players.png"):
    """
    Generates a scatter plot showing the number of White players vs. Black players for each NFL team.
    Each data point is labeled with the team name.
    """
    
    input_dir = "combined_depth_charts" 
    input_csv_path = os.path.join(input_dir, input_csv_filename)
    output_plot_path = os.path.join(output_charts_dir, output_plot_filename)
    
    # Create directory for charts if it doesn't exist
    os.makedirs(output_charts_dir, exist_ok=True)

    print(f"Loading data from: {input_csv_path}")
    print(f"Generating plot and saving to: {output_plot_path}")

    try:
        df = pd.read_csv(input_csv_path)

        # --- Data Cleaning and Preparation ---
        df['PlayerUID'] = df['PlayerUID'].astype(str)
        
        # Define statuses that indicate incomplete/failed processing or empty slots
        invalid_race_statuses = {
            'N/A (No URL)', 'N/A (Scrape Failed)', 'N/A (Empty Download)', 
            'N/A (No Probabilities)', 'N/A (No Face Detected)', 'N/A (Skipped/Default)'
        }
        
        # Filter out rows where race inference failed or was not applicable
        df_valid_race = df[~df['InferredRace'].isin(invalid_race_statuses) & ~df['InferredRace'].str.startswith('Error:', na=False)].copy()
        
        # Handle cases where PlayerName is empty or a placeholder from depth chart (e.g., '-')
        df_valid_race = df_valid_race[df_valid_race['PlayerName'].notna() & (df_valid_race['PlayerName'] != '-')].copy()

        if df_valid_race.empty:
            print("No valid player data with inferred race found for analysis after filtering. Exiting.")
            return

        # --- Calculate White and Black Player Counts per Team ---
        # Filter for White and Black players only
        df_white_black = df_valid_race[df_valid_race['InferredRace'].isin(['White', 'Black'])].copy()

        if df_white_black.empty:
            print("No White or Black players with valid race data found for plotting. Exiting.")
            return

        # Group by TeamName and pivot to get counts for White and Black
        team_composition = df_white_black.groupby('TeamName')['InferredRace'].value_counts().unstack(fill_value=0)
        
        # Ensure 'White' and 'Black' columns exist even if no players of that race were found
        if 'White' not in team_composition.columns:
            team_composition['White'] = 0
        if 'Black' not in team_composition.columns:
            team_composition['Black'] = 0

        # Sort by TeamName for consistent output order
        team_composition = team_composition.sort_index()

        print("\n--- Team White vs. Black Player Counts ---")
        print(team_composition[['White', 'Black']].to_string())

        # --- Generate Scatter Plot ---
        plt.figure(figsize=(14, 10), facecolor='#f0f0f0') # Set plot background color to light gray

        # Scatter plot
        plt.scatter(team_composition['White'], team_composition['Black'], s=100, alpha=0.7, color='skyblue', edgecolors='navy')

        # Add team names as labels for each point
        for i, team_name in enumerate(team_composition.index):
            num_white = team_composition.loc[team_name, 'White']
            num_black = team_composition.loc[team_name, 'Black']
            
            # Use a slightly offset text to prevent overlap with the point
            plt.text(num_white + 0.5, num_black, team_name, fontsize=9,
                     path_effects=[pe.withStroke(linewidth=2, foreground="white")], # Add white outline for readability
                     ha='left', va='center')

        plt.title('NFL Team Composition: Number of White vs. Black Players', fontsize=16, pad=20)
        plt.xlabel('Number of White Players', fontsize=12)
        plt.ylabel('Number of Black Players', fontsize=12)
        
        # Add grid for easier readability
        plt.grid(True, linestyle='--', alpha=0.6)
        
        # Set integer ticks for clarity, if appropriate for your data range
        plt.xticks(range(int(team_composition['White'].min()), int(team_composition['White'].max()) + 2, 5))
        plt.yticks(range(int(team_composition['Black'].min()), int(team_composition['Black'].max()) + 2, 5))

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
