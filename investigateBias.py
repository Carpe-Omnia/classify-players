import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def analyze_racial_bias_in_emotions(input_csv_filename="master_nfl_depth_chart_with_race.csv",
                                     input_dir="combined_depth_charts",
                                     output_charts_dir="racial_bias_analysis_charts",
                                     output_plot_filename="emotion_distribution_by_race.png"):
    """
    Analyzes potential racial bias in emotion identification by breaking down
    emotion distributions by inferred race and normalizing the numbers.
    Generates a grouped bar chart for visualization.
    """
    
    input_csv_path = os.path.join(input_dir, input_csv_filename)
    os.makedirs(output_charts_dir, exist_ok=True)
    output_plot_path = os.path.join(output_charts_dir, output_plot_filename)

    print(f"Starting racial bias analysis from: {input_csv_path}")
    print(f"Charts will be saved to: {output_charts_dir}")

    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV file not found at '{input_csv_path}'. Exiting.")
        return

    try:
        df = pd.read_csv(input_csv_path)

        # --- Data Cleaning and Filtering ---
        # Define statuses that indicate incomplete/failed processing or empty slots
        invalid_race_statuses = {
            'N/A (No URL)', 'N/A (Scrape Failed)', 'N/A (Empty Download)', 
            'N/A (No Probabilities)', 'N/A (No Face Detected)', 'N/A (Skipped/Default)'
        }
        valid_emotions_order = ['Happy', 'Neutral', 'Sad', 'Angry', 'Surprise', 'Fear', 'Disgust']

        # Filter out rows with invalid race or emotion data, or invalid player names/UIDs
        df_filtered = df[
            ~df['InferredRace'].isin(invalid_race_statuses) & 
            ~df['InferredRace'].str.startswith('Error:', na=False) &
            df['InferredEmotion'].notna() & 
            df['InferredEmotion'].isin(valid_emotions_order) &
            df['PlayerName'].notna() & 
            (df['PlayerName'] != '-') &
            df['PlayerUID'].notna()
        ].copy()

        if df_filtered.empty:
            print("No valid player data with inferred race and emotion found for analysis after filtering. Exiting.")
            return

        # --- Grouping into 'Black', 'White', and 'Other' ---
        df_filtered['SimplifiedRace'] = df_filtered['InferredRace'].apply(
            lambda x: x if x in ['Black', 'White'] else 'Other'
        )

        print(f"\nTotal players with valid race and emotion data for analysis: {len(df_filtered)}")
        print(f"Unique simplified racial groups found: {df_filtered['SimplifiedRace'].unique()}")
        print(f"Unique emotions found: {df_filtered['InferredEmotion'].unique()}")


        # --- Calculate Emotion Distribution per Simplified Race Group ---
        # Group by SimplifiedRace and then by InferredEmotion to get counts
        emotion_counts_by_race = df_filtered.groupby(['SimplifiedRace', 'InferredEmotion']).size().unstack(fill_value=0)

        # Reindex columns to ensure all valid emotions are present, filling missing with 0
        emotion_counts_by_race = emotion_counts_by_race.reindex(columns=valid_emotions_order, fill_value=0)

        # Normalize the counts within each racial group to get percentages
        # Sum of emotions for each race will be 100%
        emotion_percentages_by_race = emotion_counts_by_race.div(emotion_counts_by_race.sum(axis=1), axis=0) * 100

        print("\n--- Emotion Distribution (Percentages) by Simplified Racial Group ---")
        print(emotion_percentages_by_race.to_string(float_format="%.2f%%"))

        # --- Concrete Number Comparisons (Examples) ---
        print("\n--- Specific Comparisons ---")
        # Updated racial groups for comparison to reflect simplified categories
        racial_groups_for_comparison = ['Black', 'White', 'Other'] 
        
        for emotion in ['Angry', 'Happy', 'Neutral', 'Sad']:
            print(f"\nEmotion: '{emotion}'")
            for race in racial_groups_for_comparison:
                if race in emotion_percentages_by_race.index:
                    percentage = emotion_percentages_by_race.loc[race, emotion]
                    count = emotion_counts_by_race.loc[race, emotion]
                    total_for_race = emotion_counts_by_race.loc[race].sum()
                    print(f"  {race}: {percentage:.2f}% ({int(count)} out of {int(total_for_race)} players)")
                else:
                    print(f"  {race}: No data available for this emotion.")


        # --- Visualization: Grouped Bar Chart ---
        fig, ax = plt.subplots(figsize=(14, 8), facecolor='#f0f0f0') # Larger figure for better readability
        
        # Get unique simplified races present in the data for plotting and ensure consistent order
        present_races_unordered = emotion_percentages_by_race.index.tolist()
        present_races = []
        if 'Black' in present_races_unordered: present_races.append('Black')
        if 'White' in present_races_unordered: present_races.append('White')
        if 'Other' in present_races_unordered: present_races.append('Other')
        # Add any other unexpected but present races for robustness
        for race in present_races_unordered:
            if race not in present_races:
                present_races.append(race)

        num_races = len(present_races)
        bar_width = 0.8 / num_races # Adjust bar width based on number of races
        index = np.arange(len(valid_emotions_order)) # Positions for each emotion group

        # Define a color palette for simplified racial groups
        race_plot_colors = {
            'White': '#ADD8E6',       # Light Blue
            'Black': '#36454F',       # Charcoal
            'Other': '#708090'        # Slate Gray (for "Other")
        }

        # Plot bars for each racial group
        for i, race in enumerate(present_races):
            # Calculate offset for grouped bars
            offset = i * bar_width - (bar_width * (num_races - 1) / 2)
            
            # Use data from emotion_percentages_by_race for plotting
            data_to_plot = emotion_percentages_by_race.loc[race, valid_emotions_order].values

            # Use defined colors, fallback to grey if race not in predefined colors
            color = race_plot_colors.get(race, '#A9A9A9') 
            
            bars = ax.bar(index + offset, data_to_plot, bar_width, 
                          label=race, color=color, edgecolor='black', alpha=0.9)
            
            # Add percentage labels on top of bars
            for bar in bars:
                height = bar.get_height()
                if height > 0: # Only label non-zero bars
                    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,
                            f'{height:.1f}%', ha='center', va='bottom', fontsize=8)


        ax.set_xlabel('Emotion', fontsize=12, labelpad=10)
        ax.set_ylabel('Percentage of Players (%)', fontsize=12, labelpad=10)
        ax.set_title('Normalized Emotion Distribution by Inferred Racial Group', fontsize=16, pad=15)
        
        ax.set_xticks(index)
        ax.set_xticklabels(valid_emotions_order, rotation=45, ha='right', fontsize=10)
        ax.tick_params(axis='y', labelsize=10)
        
        ax.legend(title="Inferred Race", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout() # Adjust layout to prevent labels from overlapping
        
        plt.savefig(output_plot_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"\nVisualization saved to: {output_plot_path}")

    except FileNotFoundError:
        print(f"Error: The input CSV file '{input_csv_path}' was not found. Please ensure the 'combined_depth_charts' directory exists and contains '{input_csv_filename}'.")
    except Exception as e:
        print(f"An unexpected error occurred during analysis or visualization: {e}")

if __name__ == "__main__":
    analyze_racial_bias_in_emotions()
