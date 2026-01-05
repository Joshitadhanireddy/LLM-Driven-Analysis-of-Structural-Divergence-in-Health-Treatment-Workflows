import os
import requests
from bs4 import BeautifulSoup, Tag
from typing import Optional
import re

# --- CONFIGURATION ---
TARGET_DISEASE = "Progeria"
TARGET_URL = "https://my.clevelandclinic.org/health/diseases/17850-progeria"
TARGET_FILENAME = "progeria_cleveland.txt"

TARGET_SECTION_HEADING = "Management and Treatment"

def scrape_cleveland_clinic_section(url: str, section_heading: str) -> Optional[str]:
    """
    Scrapes a specific section (Management and Treatment) from a Cleveland Clinic article
    by finding the section heading and extracting all subsequent content.
    """
    print(f"Attempting to scrape section '{section_heading}' from: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        main_heading = soup.find('h2', 
            attrs={'data-identity': 'headline'}, 
            string=lambda t: t and section_heading in t
        )
        
        if not main_heading:
            return f"Scraping Error: Could not locate the main section heading: '{section_heading}'. Check the text or site structure."

        main_section_wrapper = main_heading.find_parent('div', attrs={'data-identity': 'article-section'})
        
        if not main_section_wrapper:
            return "Scraping Error: Could not locate the article-section wrapper."

        treatment_content = []
        
        # 4. Extract the main heading first
        main_heading_text = main_heading.get_text(strip=True)
        treatment_content.append(f"=== {main_heading_text} ===")

        # 5. Iterate through all children of the wrapper
        for element in main_section_wrapper.children:
            
            if not isinstance(element, Tag):
                continue
            
            # --- EXTRACT SUBHEADINGS (H3 and H4) directly from the wrapper ---
            if element.get('data-identity') == 'headline' and element.name in ['h3', 'h4']:
                heading_text = element.get_text(strip=True)
                
                if element.name == 'h3':
                    treatment_content.append(f"\n--- {heading_text} ---\n")
                elif element.name == 'h4':
                    treatment_content.append(f"\n** {heading_text} **\n")

            # --- EXTRACT CONTENT (P, UL, OL, H3, H4) from inside the rich-text DIV ---
            elif element.get('data-identity') == 'rich-text':
                # The content is wrapped in a DIV with data-identity="rich-text"
                # We need to find ALL relevant content tags *recursively* inside this DIV.
                # Use find_all with recursive=True to get all nested content elements.
                
                # We target H3, H4, P, UL, OL tags inside the rich-text div
                elements_to_process = element.find_all(['h3', 'h4', 'p', 'ul', 'ol'], recursive=True)
                
                for content_element in elements_to_process:
                    
                    # --- Process Headings inside rich-text (H3, H4) ---
                    if content_element.name in ['h3', 'h4']:
                        heading_text = content_element.get_text(strip=True)
                        # Only add the heading if it hasn't been captured as a direct child of the wrapper
                        if content_element.name == 'h3':
                            treatment_content.append(f"\n--- {heading_text} ---\n")
                        elif content_element.name == 'h4':
                            treatment_content.append(f"\n** {heading_text} **\n")
                        
                    # --- Process Paragraphs ---
                    elif content_element.name == 'p':
                        # Get text, using space separator to separate linked text cleanly
                        text = content_element.get_text(separator=' ', strip=True)
                        text = re.sub(r'\s{2,}', ' ', text).strip()
                        
                        if text:
                            treatment_content.append(text)
                            
                    # --- Process Lists ---
                    elif content_element.name in ['ul', 'ol']:
                        list_items = []
                        # Important: Only process direct <li> children of the list tag
                        for li in content_element.find_all('li', recursive=False):
                            # Get text from list item, links are already handled by separator=' '
                            item_text = li.get_text(separator=' ', strip=True)
                            item_text = re.sub(r'\s{2,}', ' ', item_text).strip()

                            if item_text:
                                list_items.append(f"  - {item_text}")
                        
                        if list_items:
                            treatment_content.append('\n'.join(list_items))

            # Skip the ad div
            elif element.get('data-identity') == 'billboard-ad':
                continue
            
        if len(treatment_content) < 5:
            return "Scraping Error: Extracted content was too brief or only included the main heading."

        return '\n\n'.join(treatment_content)

    except requests.exceptions.RequestException as e:
        return f"Request Error: Failed to access URL. Please check your network connection. Error: {e}"
    except Exception as e:
        return f"Scraping Error: An unexpected error occurred during parsing. Error: {e}"


def generate_file():
    """Generates the text file with the scraped treatment plan."""
    
    # --- ACTIVE SCRAPING CALL ---
    treatment_text = scrape_cleveland_clinic_section(TARGET_URL, TARGET_SECTION_HEADING)

    # Format the required header
    header = f"--- {TARGET_DISEASE} Treatment Plan (Extracted from Cleveland Clinic) ---\n"
    
    file_content = f"{header}\nSource URL: {TARGET_URL}\n\n{treatment_text}\n"

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