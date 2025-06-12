import requests
from bs4 import BeautifulSoup
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
import time # For potential delays
from webdriver_manager.chrome import ChromeDriverManager # Import directly, assuming it will be installed

def get_player_image_url(player_url):
    """
    Fetches an ESPN NFL player's profile page using Selenium to handle dynamic content
    and extracts the URL of their headshot image.
    Specifically targets the <img> tag within the <figure class="PlayerHeader__HeadShot"> element.
    """
    # --- Selenium Setup ---
    chrome_options = Options()
    # Run Chrome in headless mode (no visible browser window)
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox") # Recommended for headless in some environments
    chrome_options.add_argument("--disable-dev-shm-usage") # Recommended for headless in some environments
    
    # Use WebDriverManager for automatic driver installation (recommended)
    service = Service(ChromeDriverManager().install())
    print("Using ChromeDriverManager to manage ChromeDriver.")
    
    driver = None
    try:
        print(f"Opening headless browser for {player_url}...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30) # Set a timeout for page load
        driver.get(player_url)
        
        # Give some time for dynamic content to load. Adjust if needed.
        time.sleep(3) 

        # Now get the page source after JavaScript has executed
        page_source = driver.page_source
        
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find the div with class 'PlayerHeader__Image'
        player_header_image_div = soup.find('div', class_='PlayerHeader__Image')
        
        if player_header_image_div:
            # --- DEBUG: Print content of the found main div (from Selenium) ---
            print("\n--- PlayerHeader__Image DIV CONTENT START (from Selenium) ---")
            print(player_header_image_div.prettify()) 
            print("--- PlayerHeader__Image DIV CONTENT END (from Selenium) ---\n")

            # --- Specific change: Find the <figure> for the headshot first ---
            # Based on the HTML, the player's headshot is within a <figure class="PlayerHeader__HeadShot">
            headshot_figure = player_header_image_div.find('figure', class_='PlayerHeader__HeadShot')

            if headshot_figure:
                # Find the <img> tag within this specific headshot figure
                img_tag = headshot_figure.find('img')
                
                if img_tag and 'src' in img_tag.attrs:
                    image_url = img_tag['src']
                    # Add a check to ensure it's a valid http/https URL and not a base64 placeholder
                    if image_url.startswith('http') and not image_url.startswith('data:image/gif'):
                        print(f"Found player headshot URL: {image_url}")
                        return image_url
                    else:
                        print("Error: Player headshot URL found but it's not a valid http/https URL (might still be placeholder).")
                        return None
                else:
                    print("Error: <img> tag or 'src' attribute not found within PlayerHeader__HeadShot figure.")
                    return None
            else:
                print("Error: <figure class='PlayerHeader__HeadShot'> not found within PlayerHeader__Image div.")
                return None
        else:
            print("Error: div with class 'PlayerHeader__Image' not found on the page.")
            return None
        
    except TimeoutException:
        print(f"Page load timed out for {player_url}.")
        return None
    except WebDriverException as e:
        print(f"WebDriver error (e.g., ChromeDriver not found/configured, browser issue): {e}")
        print("Please ensure ChromeDriver is installed and its path is correctly configured, or use webdriver_manager.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    finally:
        if driver:
            driver.quit() # Always close the browser
            print("Browser closed.")

if __name__ == "__main__":
    # Example URL for Justin Osborne
    player_profile_url = "https://www.espn.com/nfl/player/_/id/4567230/justin-osborne"
    
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")

    # Get the image URL using the scraping logic
    image_link = get_player_image_url(player_profile_url)
    
    if image_link:
        print(f"\nSuccessfully retrieved player image URL for Justin Osborne: {image_link}")
        
        # --- Download and Save Image ---
        # requests is already imported at the top, no need to re-import
        output_image_filename = "player_profile_scraped.png" 
        output_image_filepath = os.path.join(current_dir, output_image_filename) 

        try:
            print(f"Attempting to download image from: {image_link}")
            image_data = requests.get(image_link, timeout=10).content
            
            data_size = len(image_data)
            print(f"Downloaded image data size: {data_size} bytes")

            if data_size > 0:
                print(f"Attempting to save image to: {output_image_filepath}")
                with open(output_image_filepath, "wb") as f:
                    f.write(image_data)
                print(f"Image downloaded and saved successfully as {output_image_filename}")
            else:
                print("Downloaded image data is empty. The URL might not point to a valid image or download failed silently.")

        except Exception as e:
            print(f"Failed to download or save image: {e}")
            print("Possible reasons: Network issue, invalid image URL, or permission denied to write to directory.")
    else:
        print("\nFailed to retrieve player image URL through scraping.")
