## NFL Player race analysis w/ deepface
Uses Selenium and to retrieve player headshots from ESPN.com
Uses Deepface open source AI to analyze the player's image and infer race (dodgy)
Outputs results into player_race_analysis_results.csv

## Usage
use provided master_nfl_depth_chart.csv collected June 2025 or collect your own using https://github.com/Carpe-Omnia/ScrapePlayers
run doBoth.py 
-this will take a long time. 
If selenium crashes it will create a bunch of "scrape failed" entries in the output CSV>
-use mergeData.py to merge entries in the output CSV. Copy & Paste player_race_analysis_results_merged.csv over the original output CSV after marge script runs. 
Once script finishes running you will have an OK but not particularly good look at the racial makeup of players in the NFL. 

## License
MIT
