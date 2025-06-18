import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def generate_simplified_pie_charts(input_csv_filename="master_nfl_depth_chart_with_race.csv",
                                   output_charts_dir="race_composition_charts_for_embedding"):
    """
    Generates simplified pie charts for each NFL position, suitable for embedding.
    Charts will have no title/labels, and all races other than White/Black are
    grouped into an 'Other' category.
    """
    
    input_dir = "combined_depth_charts" 
    input_csv_path = os.path.join(input_dir, input_csv_filename)
    
    os.makedirs(output_charts_dir, exist_ok=True)

    print(f"Loading data from: {input_csv_path}")
    print(f"Saving simplified charts to: {output_charts_dir}")

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

        print(f"\nTotal players with valid race data: {len(df_valid_race)}")

        # --- Define consistent color palette for simplified races ---
        # White, Black, and a new 'Other' category
        simplified_race_colors = {
            'White': '#D2B48C',       # Tan Beige
            'Black': '#4A2C2A',       # Chocolatey Brown
            'Other': '#808080'        # Grey for "Other"
        }

        # --- Function to generate and save a simplified pie chart ---
        def generate_pie_chart_for_embedding(data_series, filename_suffix):
            if data_series.empty or data_series.sum() == 0:
                print(f"  No data for '{filename_suffix}', skipping chart generation.")
                return

            # Group all non-White/Black races into 'Other'
            temp_data = data_series.copy()
            other_sum = 0
            for race_type in temp_data.index:
                if race_type not in ['White', 'Black']:
                    other_sum += temp_data[race_type]
                    temp_data = temp_data.drop(race_type)
            if other_sum > 0:
                temp_data['Other'] = other_sum
            
            # Reorder for consistent slice order (White, Black, Other)
            ordered_labels = []
            if 'White' in temp_data.index: ordered_labels.append('White')
            if 'Black' in temp_data.index: ordered_labels.append('Black')
            if 'Other' in temp_data.index: ordered_labels.append('Other')
            
            # Ensure only relevant labels are included
            labels = [label for label in ordered_labels if label in temp_data.index]
            sizes = [temp_data[label] for label in labels]

            # Map labels to colors
            colors = [simplified_race_colors.get(label, '#cccccc') for label in labels] 

            plt.figure(figsize=(2, 2), dpi=300, facecolor='none') # Very small figure, high DPI, transparent background
            plt.pie(sizes, colors=colors, startangle=90) # No labels or autopct
            plt.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
            
            chart_path = os.path.join(output_charts_dir, f"{filename_suffix}.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', pad_inches=0, transparent=True)
            plt.close() # Close the plot to free memory
            print(f"  Simplified chart saved: {chart_path}")


        # --- Process and Generate Charts for Individual Positions ---
        print("\n--- Generating Simplified Charts for Individual Positions ---")
        
        # Get all unique positions from PrimaryPosition, Position2, Position3
        all_individual_positions = pd.concat([
            df_valid_race['PrimaryPosition'], 
            df_valid_race['Position2'], 
            df_valid_race['Position3']
        ]).dropna().unique()
        
        all_individual_positions.sort()

        for position in all_individual_positions:
            if pd.isna(position) or position == '' or position == '-':
                continue
            
            print(f"\n--- Processing Position: {position} ---")
            
            position_df = df_valid_race[
                (df_valid_race['PrimaryPosition'] == position) |
                (df_valid_race['Position2'] == position) |
                (df_valid_race['Position3'] == position)
            ]

            if not position_df.empty:
                # Get value counts for race and pass to chart generation
                position_race_counts = position_df['InferredRace'].value_counts()
                generate_pie_chart_for_embedding(position_race_counts, f"position_{position.lower().replace(' ', '_')}_race_composition")
            else:
                print(f"No valid players found for position: {position}. Skipping chart generation.")

        print("\nSimplified chart generation complete.")

    except FileNotFoundError:
        print(f"Error: The input CSV file '{input_csv_path}' was not found. Please ensure the 'combined_depth_charts' directory exists and contains '{input_csv_filename}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    generate_simplified_pie_charts()
