import pandas as pd
import os

def merge_depth_charts_with_panthers(
    master_depth_chart_path="combined_depth_charts/master_nfl_depth_chart.csv",
    panthers_depth_chart_path="combined_depth_charts/depth_chart_with_panthers.csv"
):
    """
    Merges master_nfl_depth_chart.csv with depth_chart_with_panthers.csv on PlayerUID.
    It keeps all players from master_nfl_depth_chart.csv and adds/updates data
    from depth_chart_with_panthers.csv where PlayerUID matches.
    The result is saved back into master_nfl_depth_chart.csv.
    """
    
    print(f"Starting merge operation for CSV files.")
    print(f"Master depth chart: {master_depth_chart_path}")
    print(f"Panthers depth chart to merge: {panthers_depth_chart_path}")

    # Check if input files exist
    if not os.path.exists(master_depth_chart_path):
        print(f"Error: Master depth chart file not found at '{master_depth_chart_path}'. Exiting.")
        return
    if not os.path.exists(panthers_depth_chart_path):
        print(f"Error: Panthers depth chart file not found at '{panthers_depth_chart_path}'. Exiting.")
        return

    try:
        # Load the master depth chart
        df_master = pd.read_csv(master_depth_chart_path)
        print(f"Loaded master depth chart with {len(df_master)} rows.")

        # Load the Panthers depth chart
        df_panthers = pd.read_csv(panthers_depth_chart_path)
        print(f"Loaded Panthers depth chart with {len(df_panthers)} rows.")

        # Ensure PlayerUID columns are of the same type for merging
        df_master['PlayerUID'] = df_master['PlayerUID'].astype(str)
        df_panthers['PlayerUID'] = df_panthers['PlayerUID'].astype(str)

        # Check if df_panthers is empty. If so, don't try to concat.
        if df_panthers.empty:
            print(f"Warning: Panthers depth chart '{panthers_depth_chart_path}' is empty. No merge performed.")
            df_combined = df_master # Keep the master dataframe as is
        else:
            # Strategy: Combine both DataFrames, then drop duplicates based on PlayerUID,
            # keeping the entry from `df_panthers` if a PlayerUID exists in both,
            # effectively updating `master` with `panthers` data.
            df_combined = pd.concat([df_master, df_panthers]).drop_duplicates(subset=['PlayerUID'], keep='last')
            print(f"Combined dataframes and dropped duplicates based on PlayerUID, keeping the latest entry.")
            
        print(f"Resulting DataFrame has {len(df_combined)} rows.")

        # Save the merged DataFrame back to the master CSV path
        df_combined.to_csv(master_depth_chart_path, index=False)
        print(f"Successfully merged data and saved back to '{master_depth_chart_path}'.")

    except Exception as e:
        print(f"An error occurred during the merge operation: {e}")

if __name__ == "__main__":
    # Define paths (assuming they are in 'combined_depth_charts' relative to the script)
    base_dir = "combined_depth_charts"
    master_csv = os.path.join(base_dir, "master_nfl_depth_chart.csv")
    panthers_csv = os.path.join(base_dir, "depth_chart_with_panthers.csv")
    
    merge_depth_charts_with_panthers(master_csv, panthers_csv)
