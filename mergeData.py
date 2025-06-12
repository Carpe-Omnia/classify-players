import os
import csv

def merge_player_race_analysis_results(input_csv_filename="player_race_analysis_results.csv",
                                     output_csv_filename="player_race_analysis_results_merged.csv"):
    """
    Merges rows in the player_race_analysis_results.csv that have the same PlayerUID.
    Prioritizes rows with valid InferredRace data over those with 'N/A' or 'Error' statuses.
    """
    
    input_dir = "combined_depth_charts" # Assuming the results CSV is in this directory
    input_csv_path = os.path.join(input_dir, input_csv_filename)
    output_csv_path = os.path.join(input_dir, output_csv_filename)

    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV file '{input_csv_path}' not found. Please ensure it exists.")
        return

    print(f"Reading results from: {input_csv_path}")
    print(f"Merging and writing to: {output_csv_path}")

    # Define statuses that indicate incomplete/failed processing
    failed_statuses = {
        'N/A (No URL)', 'N/A (Scrape Failed)', 'N/A (Empty Download)', 
        'N/A (No Probabilities)', 'N/A (No Face Detected)'
    }

    # Dictionary to store the best row for each PlayerUID
    # Key: PlayerUID, Value: Dictionary representing the selected row
    merged_data = {} 

    try:
        with open(input_csv_path, 'r', encoding='utf-8', newline='') as infile:
            reader = csv.DictReader(infile)
            
            # Ensure essential columns exist
            if 'PlayerUID' not in reader.fieldnames or 'InferredRace' not in reader.fieldnames:
                print("Error: Input CSV must contain 'PlayerUID' and 'InferredRace' columns.")
                return

            for i, row in enumerate(reader):
                player_uid = row.get('PlayerUID')
                inferred_race = row.get('InferredRace', '')

                if not player_uid:
                    print(f"Warning: Row {i+1} has no PlayerUID. Skipping: {row}")
                    continue

                # Determine if the current row has valid race data
                is_current_row_valid = not (inferred_race.startswith('N/A (') or inferred_race.startswith('Error:') or inferred_race in failed_statuses)

                if player_uid not in merged_data:
                    # If this is the first time we see this PlayerUID, just add it
                    merged_data[player_uid] = row
                else:
                    # If we've seen this PlayerUID before, apply merging logic
                    existing_row = merged_data[player_uid]
                    existing_inferred_race = existing_row.get('InferredRace', '')
                    is_existing_row_valid = not (existing_inferred_race.startswith('N/A (') or existing_inferred_race.startswith('Error:') or existing_inferred_race in failed_statuses)

                    # Prioritize the valid row
                    if is_current_row_valid and not is_existing_row_valid:
                        # Current row is valid, existing is not -> replace
                        merged_data[player_uid] = row
                        print(f"  Merged {player_uid}: Replaced old (invalid) data with new (valid).")
                    elif is_current_row_valid and is_existing_row_valid:
                        # Both are valid, keep the first one encountered (assuming higher confidence or original source)
                        # No action needed, existing_row already holds the first valid one.
                        print(f"  Merged {player_uid}: Both valid, keeping first encountered valid entry.")
                    elif not is_current_row_valid and is_existing_row_valid:
                        # Current is not valid, existing is -> keep existing
                        # No action needed
                        pass
                    else: # Both are invalid
                        # Both are invalid, keep the first one encountered
                        # No action needed
                        pass
        
        print(f"\nFinished reading input file. Total unique players after merging: {len(merged_data)}")

        # Prepare header for the output CSV (assuming all rows have the same structure)
        if not merged_data:
            print("No data to write to output CSV.")
            return

        output_fieldnames = list(reader.fieldnames) # Use the original header fields

        # Write the merged data to the new output CSV file
        with open(output_csv_path, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()
            
            for player_uid in merged_data:
                writer.writerow(merged_data[player_uid])
        
        print(f"Successfully merged and saved results to '{output_csv_path}'")

    except FileNotFoundError:
        print(f"Error: Input file '{input_csv_path}' not found.")
    except Exception as e:
        print(f"An error occurred during merging: {e}")

if __name__ == "__main__":
    merge_player_race_analysis_results()

