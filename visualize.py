import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def analyze_and_visualize_race_composition(input_csv_filename="master_nfl_depth_chart_with_race.csv",
                                           output_charts_dir="race_composition_charts"):
    """
    Analyzes the racial composition of NFL players from the merged CSV data
    and generates pie charts for overall, unit-wise, position-wise,
    and broader position group breakdowns.
    """
    
    input_dir = "combined_depth_charts" 
    input_csv_path = os.path.join(input_dir, input_csv_filename)
    
    # Create directory for charts if it doesn't exist
    os.makedirs(output_charts_dir, exist_ok=True)

    print(f"Loading data from: {input_csv_path}")
    print(f"Saving charts to: {output_charts_dir}")

    try:
        df = pd.read_csv(input_csv_path)

        # --- Data Cleaning and Preparation ---
        # Ensure PlayerUID is string for consistency
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

        print(f"\nTotal players with valid race data: {len(df_valid_race)}")
        print(f"Total players in original file: {len(df)}")
        print(f"Players without valid race data (skipped): {len(df) - len(df_valid_race)}")


        # --- Define Position Categories (flexible for any NFL positions) ---
        offensive_positions = ['QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT', 'OG', 'OT', 'OC', 'G', 'T', 'OL']
        defensive_positions = ['DE', 'DT', 'NT', 'LDE', 'RDE', 'LDT', 'RDT', 'MLB', 'WLB', 'SLB', 'CB', 'LCB', 'RCB', 'SS', 'FS', 'S', 'DB', 'LB', 'DL', 'EDGE']
        special_teams_positions = ['PK', 'P', 'H', 'LS', 'PR', 'KR', 'K']

        def assign_unit(position):
            if pd.isna(position) or position == '':
                return 'Unknown'
            pos_upper = str(position).upper()
            if pos_upper in offensive_positions:
                return 'Offense'
            elif pos_upper in defensive_positions:
                return 'Defense'
            elif pos_upper in special_teams_positions:
                return 'Special Teams'
            return 'Other'

        # Assign a primary unit to each player based on PrimaryPosition
        df_valid_race['PrimaryUnit'] = df_valid_race['PrimaryPosition'].apply(assign_unit)
        
        # --- Define Broader Position Groups ---
        # Group individual positions into broader categories for additional analysis
        offensive_line_positions = ['LT', 'LG', 'C', 'RG', 'RT', 'OG', 'OT', 'OC', 'G', 'T', 'OL']
        defensive_line_positions = ['DE', 'DT', 'NT', 'LDE', 'RDE', 'LDT', 'RDT', 'DL']
        linebacker_positions = ['MLB', 'WLB', 'SLB', 'LB', 'EDGE'] # EDGE often overlaps with DL/LB
        secondary_positions = ['CB', 'LCB', 'RCB', 'SS', 'FS', 'S', 'DB']

        # --- Define a consistent color palette for races ---
        # This ensures consistency across all charts
        race_colors = {
            'White': '#FFFFFF',       # White
            'Black': '#654321',       # Black
            'Asian': '#2ca02c',       # Green
            'Indian': '#d62728',      # Red
            'Latino Hispanic': '#9467bd', # Purple
            'Middle Eastern': '#8c564b',# Brown
            'East Asian': '#e377c2',  # Pink
            'Southeast Asian': '#7f7f7f', # Grey
            'Other': '#bcbd22'        # Olive
        }
        # If any race detected by DeepFace is not in our predefined colors, assign a default
        unique_races_in_data = df_valid_race['InferredRace'].unique()
        for race in unique_races_in_data:
            if race not in race_colors:
                race_colors[race] = mcolors.rand(1) # Assign a random color if new

        # --- Function to generate and save a pie chart ---
        def generate_pie_chart(data_series, title, filename_suffix, min_percent_display=1.0):
            if data_series.empty or data_series.sum() == 0:
                print(f"  No data for '{title}', skipping chart generation.")
                return

            labels = data_series.index.tolist()
            sizes = data_series.values.tolist()
            
            # Map labels to colors, using a default if not found
            colors = [race_colors.get(label, '#cccccc') for label in labels] # Use light gray for unassigned colors

            # Filter out very small slices for display on chart labels to prevent clutter
            # For actual data, we still use all sizes, but autopct formats might skip them.
            def autopct_format(pct):
                return ('%1.1f%%' % pct) if pct >= min_percent_display else ''

            plt.figure(figsize=(10, 8), facecolor='#f0f0f0') # Set plot background color to light gray
            plt.pie(sizes, labels=labels, autopct=autopct_format, startangle=140, colors=colors, 
                    pctdistance=0.85, textprops={'fontsize': 10})
            plt.title(title, fontsize=14, pad=20)
            plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
            plt.tight_layout()
            chart_path = os.path.join(output_charts_dir, f"{filename_suffix}.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close() # Close the plot to free memory
            print(f"  Chart saved: {chart_path}")


        # --- 1. Overall Race Composition ---
        print("\n--- Overall NFL Player Race Composition ---")
        overall_race_counts = df_valid_race['InferredRace'].value_counts()
        overall_race_percentages = df_valid_race['InferredRace'].value_counts(normalize=True) * 100
        
        print(overall_race_percentages.to_string(float_format="%.2f%%"))
        generate_pie_chart(overall_race_percentages, "Overall NFL Player Race Composition", "overall_race_composition")


        # --- 2. Race Composition by Unit (Offense, Defense, Special Teams, Other) ---
        print("\n--- NFL Player Race Composition by Unit ---")
        for unit in df_valid_race['PrimaryUnit'].unique():
            print(f"\n--- {unit} Unit Race Composition ---")
            unit_df = df_valid_race[df_valid_race['PrimaryUnit'] == unit]
            if not unit_df.empty:
                unit_race_percentages = unit_df['InferredRace'].value_counts(normalize=True) * 100
                print(unit_race_percentages.to_string(float_format="%.2f%%"))
                generate_pie_chart(unit_race_percentages, f"{unit} Unit Race Composition", f"{unit.lower().replace(' ', '_')}_race_composition")
            else:
                print(f"No valid players found for {unit} unit.")


        # --- 3. Race Composition by Broader Position Groups ---
        print("\n--- NFL Player Race Composition by Broader Position Groups ---")

        broad_position_groups = {
            'Offensive Line': offensive_line_positions,
            'Defensive Line': defensive_line_positions,
            'Linebackers': linebacker_positions,
            'Secondary': secondary_positions
        }

        for group_name, positions_list in broad_position_groups.items():
            print(f"\n--- {group_name} Race Composition ---")
            
            # Filter players whose PrimaryPosition is in the current group's list
            group_df = df_valid_race[df_valid_race['PrimaryPosition'].isin(positions_list)]
            
            if not group_df.empty:
                group_race_percentages = group_df['InferredRace'].value_counts(normalize=True) * 100
                print(group_race_percentages.to_string(float_format="%.2f%%"))
                generate_pie_chart(group_race_percentages, f"{group_name} Race Composition", f"{group_name.lower().replace(' ', '_')}_race_composition")
            else:
                print(f"No valid players found for {group_name}.")

        # --- 4. Race Composition by Individual Position ---
        print("\n--- NFL Player Race Composition by Individual Position ---")
        
        # Get all unique positions from PrimaryPosition, Position2, Position3
        # Stack all position columns, drop NaNs, and get unique values
        all_individual_positions = pd.concat([
            df_valid_race['PrimaryPosition'], 
            df_valid_race['Position2'], 
            df_valid_race['Position3']
        ]).dropna().unique()
        
        # Sort positions for consistent output order
        all_individual_positions.sort()

        for position in all_individual_positions:
            if pd.isna(position) or position == '' or position == '-': # Skip empty/invalid position names
                continue
            
            # Skip if this individual position is already covered by a broad group's primary position check
            # This avoids redundant charts if an individual position is very common and already charted
            # as part of a larger group where it is the *primary* position.
            # However, the user asked for *each* position, so we won't skip based on broad groups here.
            
            print(f"\n--- Position: {position} Race Composition ---")
            
            # Filter players who have this position in any of the three position columns
            # This is important for players who might be Secondary/Tertiary at a position
            position_df = df_valid_race[
                (df_valid_race['PrimaryPosition'] == position) |
                (df_valid_race['Position2'] == position) |
                (df_valid_race['Position3'] == position)
            ]

            if not position_df.empty:
                # Count race distribution for this position
                # Using 'InferredRace' from df_valid_race ensures we're only counting valid analyses
                position_race_percentages = position_df['InferredRace'].value_counts(normalize=True) * 100
                print(position_race_percentages.to_string(float_format="%.2f%%"))
                generate_pie_chart(position_race_percentages, f"Position: {position} Race Composition", f"position_{position.lower().replace(' ', '_')}_race_composition")
            else:
                print(f"No valid players found for position: {position}.")

        print("\nAnalysis and visualization complete.")

    except FileNotFoundError:
        print(f"Error: The input CSV file '{input_csv_path}' was not found. Please ensure the 'combined_depth_charts' directory exists and contains '{input_csv_filename}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    analyze_and_visualize_race_composition()
