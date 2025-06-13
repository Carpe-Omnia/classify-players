import os
import pandas as pd

def merge_depth_chart_with_race_data(
    master_csv_filename="master_nfl_depth_chart.csv",
    race_results_csv_filename="player_race_analysis_results.csv",
    output_csv_filename="master_nfl_depth_chart_with_race.csv"
):
    """
    Merges the master NFL depth chart CSV with the player race analysis results CSV
    based on PlayerUID.
    """
    
    input_dir = "combined_depth_charts" # Assuming both input CSVs are in this directory
    master_csv_path = os.path.join(input_dir, master_csv_filename)
    race_results_csv_path = os.path.join(input_dir, race_results_csv_filename)
    output_csv_path = os.path.join(input_dir, output_csv_filename)

    # Validate input files exist
    if not os.path.exists(master_csv_path):
        print(f"Error: Master depth chart CSV '{master_csv_path}' not found.")
        return
    if not os.path.exists(race_results_csv_path):
        print(f"Error: Race analysis results CSV '{race_results_csv_path}' not found.")
        return

    print(f"Loading master depth chart from: {master_csv_path}")
    print(f"Loading player race analysis results from: {race_results_csv_path}")

    try:
        # Load the CSV files into pandas DataFrames
        df_master = pd.read_csv(master_csv_path)
        df_race = pd.read_csv(race_results_csv_path)

        # Ensure PlayerUID is treated as string to prevent merge issues with leading zeros, etc.
        df_master['PlayerUID'] = df_master['PlayerUID'].astype(str)
        df_race['PlayerUID'] = df_race['PlayerUID'].astype(str)

        # Merge the two DataFrames on 'PlayerUID'
        # Using a left merge to keep all players from the master depth chart,
        # and add race data where available.
        # Suffixes are used to differentiate columns if names overlap (e.g., 'PlayerURL')
        df_merged = pd.merge(
            df_master, 
            df_race[['PlayerUID', 'InferredRace', 'RaceConfidence']], # Select only desired columns from race results
            on='PlayerUID', 
            how='left',
            suffixes=('_master', '_race') # Add suffixes if PlayerUID is not unique
        )
        
        # Clean up any potential duplicate columns if PlayerURL was also in df_race.
        # The merge should handle PlayerURL automatically if it only exists in df_master,
        # but if it was in df_race and we *didn't* select it explicitly, this is fine.
        # If PlayerURL was in df_race and selected, it would get a _race suffix.
        # In our case, we explicitly picked columns, so this is cleaner.

        # Save the merged DataFrame to a new CSV file
        df_merged.to_csv(output_csv_path, index=False, encoding='utf-8')

        print(f"\nSuccessfully merged data and saved to: {output_csv_path}")
        print(f"Total players in merged file: {len(df_merged)}")

    except Exception as e:
        print(f"An error occurred during the merging process: {e}")

if __name__ == "__main__":
    # Ensure pandas is installed: pip install pandas
    merge_depth_chart_with_race_data()
