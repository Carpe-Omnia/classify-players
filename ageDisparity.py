import pandas as pd
import os
from datetime import datetime

def analyze_age_disparity(input_csv_filename="master_nfl_depth_chart_with_race.csv",
                         input_dir="combined_depth_charts",
                         current_year=2025):
    """
    Analyzes the age disparity between a player's inferred age and their actual age
    (calculated from birthdate). Identifies players with the largest positive (older)
    and negative (younger) disparities.

    Args:
        input_csv_filename (str): Name of the input CSV file containing player data.
        input_dir (str): Directory where the input CSV file is located.
        current_year (int): The year to use as the "current" year for age calculation.
                            Defaults to 2025.
    """

    input_csv_path = os.path.join(input_dir, input_csv_filename)

    print(f"Starting age disparity analysis from: {input_csv_path}")

    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV file not found at '{input_csv_path}'. Exiting.")
        return

    try:
        df = pd.read_csv(input_csv_path)

        # Ensure necessary columns exist
        required_columns = ['PlayerName', 'PlayerBirthdate', 'InferredAge', 'TeamName', 'PlayerUID']
        for col in required_columns:
            if col not in df.columns:
                print(f"Error: Missing required column '{col}' in the input CSV. Exiting.")
                return

        # --- Data Cleaning and Preparation ---
        # Convert InferredAge to numeric, coercing errors to NaN
        df['InferredAge'] = pd.to_numeric(df['InferredAge'], errors='coerce')

        # Convert PlayerBirthdate to datetime objects
        # Handle potential errors during date parsing
        df['PlayerBirthdate_dt'] = pd.to_datetime(df['PlayerBirthdate'], errors='coerce')

        # Calculate ActualAge from PlayerBirthdate_dt
        # We calculate age as the difference between the current_year and birth year.
        # This simplifies the calculation and avoids needing specific month/day logic
        # for a general "age" comparison.
        df['ActualAge'] = current_year - df['PlayerBirthdate_dt'].dt.year

        # Filter out rows where either InferredAge or ActualAge could not be determined
        df_valid_ages = df.dropna(subset=['InferredAge', 'ActualAge']).copy()

        # Further filter to ensure ages are reasonable (e.g., positive)
        df_valid_ages = df_valid_ages[
            (df_valid_ages['InferredAge'] >= 0) & 
            (df_valid_ages['ActualAge'] >= 0)
        ].copy()

        if df_valid_ages.empty:
            print("No valid player data with both inferred and actual age found for analysis after filtering. Exiting.")
            return

        print(f"\nTotal players with valid age data for disparity analysis: {len(df_valid_ages)}")

        # --- Calculate Age Disparity ---
        # Disparity = Inferred Age - Actual Age
        # Positive disparity means inferred age is older than actual age
        # Negative disparity means inferred age is younger than actual age
        df_valid_ages['AgeDisparity'] = df_valid_ages['InferredAge'] - df_valid_ages['ActualAge']

        # Sort by AgeDisparity to find largest positive and largest negative
        df_sorted_by_disparity = df_valid_ages.sort_values(by='AgeDisparity', ascending=False)

        # --- Get players with largest positive disparity (inferred much older) ---
        # Get unique disparities first to handle ties, then select top 5
        largest_positive_disparities = df_sorted_by_disparity[df_sorted_by_disparity['AgeDisparity'] > 0]
        
        # Take the top 5 players based on disparity (or fewer if not enough)
        top_5_older = largest_positive_disparities.head(5)

        # --- Get players with largest negative disparity (inferred much younger) ---
        # Sort in ascending order for negative disparities
        df_sorted_by_disparity_asc = df_valid_ages.sort_values(by='AgeDisparity', ascending=True)
        
        # Get unique disparities, then select bottom 5
        largest_negative_disparities = df_sorted_by_disparity_asc[df_sorted_by_disparity_asc['AgeDisparity'] < 0]
        
        # Take the bottom 5 players based on disparity (or fewer if not enough)
        top_5_younger = largest_negative_disparities.head(5)

        # --- Output Results ---
        print("\n" + "="*50)
        print(f"Top 5 Players Inferred as Significantly OLDER Than Actual Age (as of {current_year})")
        print("="*50)
        if not top_5_older.empty:
            print(top_5_older[['PlayerName', 'TeamName', 'InferredAge', 'ActualAge', 'AgeDisparity']].to_string(index=False))
        else:
            print("No players found with positive age disparity.")

        print("\n" + "="*50)
        print(f"Top 5 Players Inferred as Significantly YOUNGER Than Actual Age (as of {current_year})")
        print("="*50)
        if not top_5_younger.empty:
            print(top_5_younger[['PlayerName', 'TeamName', 'InferredAge', 'ActualAge', 'AgeDisparity']].to_string(index=False))
        else:
            print("No players found with negative age disparity.")

        print("\nAge disparity analysis complete.")

    except Exception as e:
        print(f"An unexpected error occurred during age disparity analysis: {e}")

if __name__ == "__main__":
    analyze_age_disparity()
