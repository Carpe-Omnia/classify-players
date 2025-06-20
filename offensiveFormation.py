import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image # For robust image loading/handling if needed
import matplotlib.patheffects as pe # Ensure this is imported for text effects

def create_offensive_formation_graphic(input_charts_dir="race_composition_charts_for_embedding",
                                     output_graphic_dir="formation_graphics",
                                     output_graphic_filename="offensive_formation_race_composition.png"):
    """
    Creates a composite graphic showing demographic pie charts for various offensive positions
    arranged in a typical offensive formation with a legend.
    """
    
    os.makedirs(output_graphic_dir, exist_ok=True)
    
    print(f"Reading individual pie charts from: {input_charts_dir}")
    print(f"Generating composite graphic and saving to: {os.path.join(output_graphic_dir, output_graphic_filename)}")

    # Define the racial categories and their colors (updated as requested)
    racial_categories = {
        'White': '#D2B48C',       # Tan Beige
        'Black': '#4A2C2A',       # Chocolatey Brown
        'Other': '#808080'        # Grey for "Other"
    }

    offensive_formation_layout = {
        'C': {'coords': (50, 30), 'label': 'C'},
        'LG': {'coords': (40, 30), 'label': 'LG'},
        'RG': {'coords': (60, 30), 'label': 'RG'},
        'LT': {'coords': (30, 30), 'label': 'LT'},
        'RT': {'coords': (70, 30), 'label': 'RT'},
        'QB': {'coords': (50, 22), 'label': 'QB'},
        'RB': {'coords': (50, 5), 'label': 'RB'},
        'WR1': {'coords': (10, 30), 'label': 'WR'},
        'WR2': {'coords': (85, 30), 'label': 'WR'},
        'TE': {'coords': (20, 30), 'label': 'TE'},
        'FB': {'coords': (50, 15), 'label': 'FB'},
    }

    position_chart_filenames = {
        'C': 'position_c_race_composition.png',
        'LG': 'position_lg_race_composition.png',
        'RG': 'position_rg_race_composition.png',
        'LT': 'position_lt_race_composition.png',
        'RT': 'position_rt_race_composition.png',
        'QB': 'position_qb_race_composition.png',
        'RB': 'position_rb_race_composition.png',
        'WR1': 'position_wr_race_composition.png',
        'WR2': 'position_wr_race_composition.png',
        'TE': 'position_te_race_composition.png',
        'FB': 'position_fb_race_composition.png',
    }

    fig, ax = plt.subplots(figsize=(18, 12))
    ax.set_facecolor('#006400')
    ax.set_title('NFL Offensive Formation: Player Race Composition', fontsize=40, color='black', pad=30)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 40)

    # Field lines
    ax.axhline(y=15, color='white', linestyle='--', alpha=0.5, linewidth=1)
    ax.axhline(y=25, color='white', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(x=50, color='white', linestyle=':', alpha=0.3, linewidth=1)

    try:
        # First, add all the position charts
        for pos_key, details in offensive_formation_layout.items():
            pos_label = details['label']
            coords = details['coords']
            chart_filename = position_chart_filenames.get(pos_key)
            
            if not chart_filename:
                print(f"Warning: No chart filename mapping for position key '{pos_key}'. Skipping.")
                continue

            chart_path = os.path.join(input_charts_dir, chart_filename)

            if os.path.exists(chart_path):
                try:
                    pie_chart_img = mpimg.imread(chart_path)
                    imagebox = OffsetImage(pie_chart_img, zoom=0.25)
                    ab = AnnotationBbox(imagebox, coords, frameon=False, pad=0.0)
                    ax.add_artist(ab)

                    ax.text(coords[0], coords[1] - 3, pos_label, 
                           color='white', fontsize=12, ha='center', va='top', 
                           path_effects=[pe.withStroke(linewidth=3, foreground="black")])
                    
                    print(f"  Added chart for {pos_label} at {coords}")

                except Exception as e:
                    print(f"Error embedding chart for {pos_key} from {chart_path}: {e}")
            else:
                print(f"Warning: Pie chart file not found for {pos_key} at {chart_path}. Skipping.")
        
        # Create a custom legend for racial categories with larger size
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', label=race,
                          markerfacecolor=color, markersize=20)  # Increased marker size
                         for race, color in racial_categories.items()]
        
        # Add the legend to the plot in bottom left with larger font and box
        legend = ax.legend(handles=legend_elements, 
                          title='Racial Composition',
                          loc='lower left',
                          bbox_to_anchor=(0.05, 0.05),  # Position in bottom left
                          fontsize=16,  # Increased font size
                          title_fontsize=18,  # Increased title size
                          facecolor='white',
                          edgecolor='black',
                          framealpha=0.9,  # Slightly transparent
                          borderpad=1.5,  # More padding inside box
                          handletextpad=1.5,  # More space between marker and text
                          labelspacing=1.2)  # More space between labels
        
        # Make the legend text more readable against the green background
        for text in legend.get_texts():
            text.set_color('black')
            text.set_path_effects([pe.withStroke(linewidth=2, foreground="white")])
        
        legend.get_title().set_color('black')
        legend.get_title().set_path_effects([pe.withStroke(linewidth=2, foreground="white")])

        # Save the composite graphic
        output_filepath = os.path.join(output_graphic_dir, output_graphic_filename)
        plt.tight_layout()
        plt.savefig(output_filepath, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        print(f"\nComposite graphic saved to: {output_filepath}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    create_offensive_formation_graphic()
