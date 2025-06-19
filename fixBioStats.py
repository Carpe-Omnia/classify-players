import csv
import re
import os

def convert_height_to_inches(height_str):
    """
    Converts a height string (e.g., "6' 8"") to total inches.
    Returns None if conversion fails.
    """
    if not height_str or "N/A" in height_str:
        return None
    try:
        # Robustly extract feet and inches using regex
        # This regex handles formats like "6' 8"", "6'8", "6'"
        match = re.match(r'(\d+)\'\s*(\d+)?', height_str.strip().replace('"', ''))
        
        if match:
            feet = int(match.group(1))
            inches_str = match.group(2)
            inches = int(inches_str) if inches_str else 0 # If inches part is missing (e.g., "6'"), default to 0
            return (feet * 12) + inches
        else:
            # If the format doesn't match expected patterns, return None
            return None
    except (ValueError, TypeError): # Catch errors from int conversion or NoneType if match fails
        return None

def parse_draft_info(draft_info_str):
    """
    Parses a draft information string (e.g., "2008: Rd 2, Pk 50 (ARI)")
    into year, position, and organization.
    Returns (None, None, None) if parsing fails or info is N/A.
    """
    year = None
    position = None
    organization = None

    if not draft_info_str or "N/A" in draft_info_str:
        return year, position, organization

    # Example: "2018: Rd 1, Pk 7 (BUF)"
    # Regex to capture year, round/pick, and organization
    match = re.match(r'(\d{4}): Rd (\d+), Pk (\d+) \((.+)\)', draft_info_str)
    if match:
        year = int(match.group(1))
        # Combine Rd and Pk for position for simplicity, or keep separate if needed
        position = f"Rd {match.group(2)}, Pk {match.group(3)}"
        organization = match.group(4)
    else:
        # Handle cases like "Undrafted" or "Signed"
        if "Undrafted" in draft_info_str:
            organization = "Undrafted"
            position = "Undrafted"
        elif "Signed" in draft_info_str: 
            org_match = re.search(r'\((.+)\)', draft_info_str)
            if org_match:
                organization = org_match.group(1)
            position = "Signed" # Or "Undrafted Free Agent" if that's more accurate

    return year, position, organization

def process_player_data(input_csv_path, output_csv_path):
    """
    Reads player data from an input CSV, processes specific columns,
    and writes the enhanced data to a new output CSV.
    """
    processed_data = []
    
    # Define the new fieldnames for the output CSV
    output_fieldnames = [
        'PlayerName', 'PlayerUID', 'InferredRace', 'RaceConfidence', 
        'InferredAge', 'InferredEmotion', 'EmotionConfidence',
        'PlayerHeightInches', 'PlayerWeightLBS', 'PlayerBirthdate', 
        'PlayerCollege', 'DraftYear', 'DraftPosition', 'DraftOrganization', 
        'PlayerOverallStatus', 'PlayerURL'
    ]

    try:
        with open(input_csv_path, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            
            # Check if required columns exist
            required_cols = ['PlayerName', 'PlayerUID', 'PlayerHeightWeight', 'PlayerDraftInfo']
            if not all(col in reader.fieldnames for col in required_cols):
                print(f"Error: Missing one or more required columns ({', '.join(required_cols)}) in input CSV.")
                return

            for row in reader:
                new_row = row.copy() # Start with a copy of the original row

                # --- Process PlayerHeightWeight ---
                height_weight_str = row.get('PlayerHeightWeight', 'N/A')
                height_inches = None
                weight_lbs = None

                if height_weight_str and "N/A" not in height_weight_str:
                    parts = height_weight_str.split(',')
                    height_raw = ''
                    weight_raw = ''

                    if len(parts) == 2: # Typical "Height", " Weight lbs" format
                        height_raw = parts[0].strip()
                        weight_raw = parts[1].strip()
                    elif len(parts) == 1: # Sometimes only height or only weight might be present
                        # Try to determine if it's height or weight based on format
                        if "'" in parts[0] or '"' in parts[0]:
                            height_raw = parts[0].strip()
                        elif 'lbs' in parts[0]:
                            weight_raw = parts[0].strip()
                    
                    height_inches = convert_height_to_inches(height_raw)
                    
                    # Extract weight using regex, robust to presence of 'lbs' or just number
                    weight_match = re.search(r'(\d+)\s*lbs', weight_raw)
                    if weight_match:
                        weight_lbs = int(weight_match.group(1))
                    elif weight_raw.isdigit(): # If it's just a number string without 'lbs'
                        weight_lbs = int(weight_raw)


                new_row['PlayerHeightInches'] = height_inches
                new_row['PlayerWeightLBS'] = weight_lbs
                
                # Remove the original combined column
                new_row.pop('PlayerHeightWeight', None)

                # --- Process PlayerDraftInfo ---
                draft_info_str = row.get('PlayerDraftInfo', 'N/A')
                draft_year, draft_position, draft_organization = parse_draft_info(draft_info_str)
                
                new_row['DraftYear'] = draft_year
                new_row['DraftPosition'] = draft_position
                new_row['DraftOrganization'] = draft_organization
                
                # Remove the original combined column
                new_row.pop('PlayerDraftInfo', None)
                
                # Reorder keys to match output_fieldnames and handle any missing original columns
                final_row = {field: new_row.get(field, None) for field in output_fieldnames}
                processed_data.append(final_row)

        print(f"Successfully processed {len(processed_data)} player records.")

        with open(output_csv_path, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()
            writer.writerows(processed_data)
        
        print(f"Processed data saved to: {output_csv_path}")

    except FileNotFoundError:
        print(f"Error: The input file '{input_csv_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Main execution ---
if __name__ == "__main__":
    input_file = os.path.join("combined_depth_charts", "output.csv") # Assuming 'output.csv' is your input file
    processed_file = os.path.join("combined_depth_charts", "processed_player_data.csv") 
    
    process_player_data(input_file, processed_file)

