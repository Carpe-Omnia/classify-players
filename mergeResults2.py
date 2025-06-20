import os
import pandas as pd

def merge_depth_chart_with_race_data(
    master_csv_filename="master_nfl_depth_chart.csv",
    race_results_csv_filename="player_race_analysis_results.csv",
    output_csv_filename="master_nfl_depth_chart_with_race.csv"
):
    """
    Merges the master NFL depth chart CSV with the player race analysis results CSV
    based on PlayerUID, including all relevant bio and emotion data.
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

        # Define columns to select from df_race.
        # PlayerURL is included here as it's part of the new data.
        # If PlayerURL also exists in df_master, the merge will add a suffix
        # which can then be resolved (e.g., keeping _race version).
        # For this specific scenario, we'll let pandas handle suffixes for overlapping columns
        # and assume the 'race' version (which includes the URL scraped by Selenium) is preferred.
        columns_from_race_df = [
            'PlayerUID', 
            'InferredRace', 
            'RaceConfidence', 
            'InferredAge', 
            'InferredEmotion', 
            'EmotionConfidence', 
            'PlayerHeightWeight', 
            'PlayerBirthdate', 
            'PlayerCollege', 
            'PlayerDraftInfo', 
            'PlayerOverallStatus',
            'PlayerURL' # Include PlayerURL from the race analysis results
        ]

        # Merge the two DataFrames on 'PlayerUID'
        # Using a left merge to keep all players from the master depth chart,
        # and add analysis data where available.
        df_merged = pd.merge(
            df_master, 
            df_race[columns_from_race_df], # Select all desired columns from race results
            on='PlayerUID', 
            how='left',
            suffixes=('_master', '_analyzed') # Use clear suffixes for overlapping columns
        )
        
        # Post-merge cleanup for PlayerURL if it exists in both and we want one specific version.
        # If 'PlayerURL_analyzed' exists, use it and drop the '_master' version.
        # This prioritizes the URL from the scraped data which is more likely to be correct for image fetching.
        if 'PlayerURL_analyzed' in df_merged.columns:
            df_merged['PlayerURL'] = df_merged['PlayerURL_analyzed'].fillna(df_merged['PlayerURL_master'])
            df_merged.drop(columns=['PlayerURL_master', 'PlayerURL_analyzed'], inplace=True)
        elif 'PlayerURL_master' in df_merged.columns: # If only master URL exists
             df_merged.rename(columns={'PlayerURL_master': 'PlayerURL'}, inplace=True)


        # Save the merged DataFrame to a new CSV file
        df_merged.to_csv(output_csv_path, index=False, encoding='utf-8')

        print(f"\nSuccessfully merged data and saved to: {output_csv_path}")
        print(f"Total players in merged file: {len(df_merged)}")
        print(f"New columns added from race analysis: {[col for col in columns_from_race_df if col != 'PlayerUID']}")

    except Exception as e:
        print(f"An error occurred during the merging process: {e}")

if __name__ == "__main__":
    merge_depth_chart_with_race_data()
