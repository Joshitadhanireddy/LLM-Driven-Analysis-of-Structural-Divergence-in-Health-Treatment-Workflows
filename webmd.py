import os
import requests
from bs4 import BeautifulSoup
from typing import Optional

# Define the target disease and URL
TARGET_DISEASE = "Progeria"
TARGET_URL = "https://www.webmd.com/children/progeria#1-6"
TARGET_FILENAME = "progeria_webmd.txt"

def scrape_webmd_treatment(url: str) -> Optional[str]:
    """
    Scrapes the main treatment article content from the given WebMD URL 
    by targeting the primary article body container based on the current HTML structure.
    """
    print(f"Attempting to scrape content from: {url}")
    try:
        # Use a common User-Agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 1. Fetch the page content
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise exception for bad status codes

        # 2. Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # 3. TARGET THE CORRECT MAIN WRAPPER: <div class="article__body">
        content_wrapper = soup.find('div', class_='article__body')
        
        # Fallback to general main area if primary class is not found
        if not content_wrapper:
            content_wrapper = soup.find('section', role='main')
        if not content_wrapper:
            # If all attempts fail, return the error
            return "Scraping Error: Could not locate the article content. WebMD's structure has changed dramatically."

        treatment_content = []

        # Extract text from paragraph, list, and heading elements found within the wrapper
        for element in content_wrapper.find_all(['p', 'ul', 'ol', 'h2', 'h3'], recursive=True):
            
            text = element.get_text(strip=True)
            
            # Skip common introductory text or empty strings
            if not text:
                continue

            if element.name in ['h2', 'h3']:
                # Add headings with clear formatting
                treatment_content.append(f"\n--- {text} ---\n")
            
            elif element.name == 'p':
                # Add regular paragraphs
                treatment_content.append(text)
            
            elif element.name in ['ul', 'ol']:
                # Extract and format list items cleanly
                list_items = [li.get_text(strip=True) for li in element.find_all('li', recursive=False)]
                if list_items:
                    list_text = '\n'.join([f"  - {item}" for item in list_items])
                    treatment_content.append(list_text)
                    
        # Final cleanup to remove ads, slideshow links, or end-of-article junk
        treatment_content = [
            item for item in treatment_content 
            if not item.lower().startswith("view a slideshow") and not item.lower().startswith("find out which eczema treatment")
        ]
        
        if len(treatment_content) < 5:
             # If we only got boilerplate text, flag it
             return "Scraping Error: Extracted content was too brief or contained only boilerplate text. The selector still needs refinement."

        # Re-join the content pieces
        return '\n\n'.join(treatment_content)

    except requests.exceptions.RequestException as e:
        return f"Request Error: Failed to access URL. Please check your network connection. Error: {e}"
    except Exception as e:
        return f"Scraping Error: An unexpected error occurred during parsing. Error: {e}"


def generate_file():
    """Generates the single text file with the scraped Eczema treatment plan."""
    
    # --- ACTIVE SCRAPING CALL ---
    treatment_text = scrape_webmd_treatment(TARGET_URL)

    # Format the required header
    header = f"--- {TARGET_DISEASE} Treatment Plan (Extracted from WebMD) ---"
    
    file_content = f"{header}\n\nSource URL: {TARGET_URL}\n\n{treatment_text}\n"

    # Write content to the file
    try:
        with open(TARGET_FILENAME, 'w', encoding='utf-8') as f:
            f.write(file_content)
        print(f"\nSuccessfully generated file: {TARGET_FILENAME}")
        print("Please run this script locally to execute the web scrape and populate the file with data.")
    except Exception as e:
        print(f"Error writing file {TARGET_FILENAME}: {e}")


if __name__ == "__main__":
    generate_file()