import os
import requests
from bs4 import BeautifulSoup, Tag
from typing import Optional
import re

# --- CONFIGURATION ---
TARGET_DISEASE = "Gigantism and Acromegaly"
TARGET_URL = "https://www.merckmanuals.com/professional/endocrine-and-metabolic-disorders/pituitary-disorders/gigantism-and-acromegaly?query=acromegaly#Treatment_v980861"
TARGET_FILENAME = "acromegaly_merck.txt"
# Keywords to match section headings for treatment
TREATMENT_KEYWORDS = ["Treatment", "Management", "Therapy", "Prognosis", "Skin Care"]
# ---------------------

def scrape_merck_manuals_section(url: str, section_keywords: list) -> Optional[str]:
    """
    Scrapes specific sections from a Merck Manuals article by targeting the main 
    section heading and extracting all content from its dedicated content wrapper DIV.
    """
    print(f"Attempting to scrape content from: {url}")
    try:
        # Use a common User-Agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 1. Fetch the page content
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # 2. Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # 3. Find the main section heading (e.g., "Treatment of Common Cold")
        # FIX: Dynamically search for "Treatment of {Disease Name}" using the configured TARGET_DISEASE.
        search_term = f"Treatment of {TARGET_DISEASE}"
        start_element_span = soup.find('span', string=lambda t: t and search_term in t)
        
        main_heading = None
        if start_element_span:
            main_heading = start_element_span.find_parent('h2')
        
        if not main_heading:
             # Fallback 1: Try finding the section using the explicit ID found in inspection
             main_section = soup.find('section', id='Treatment_v1018817')
             if main_section:
                 main_heading = main_section.find('h2')

        if not main_heading:
            return "Scraping Error: Could not locate the main 'Treatment' heading (h2)."

        # 4. Find the dedicated content wrapper DIV that is a sibling of the <h2>
        content_wrapper = main_heading.find_next_sibling('div', attrs={'data-testid': 'fheadbody'})
        
        if not content_wrapper:
            content_wrapper = main_heading.find_next_sibling('div', class_=lambda c: c and 'fHeadBody' in c)

        if not content_wrapper:
            return "Scraping Error: Could not locate the dedicated content body DIV (fheadbody) after the main heading."

        # 5. Extract all paragraphs, lists, and subheadings from inside the content wrapper
        all_content_elements = content_wrapper.find_all(['h3', 'h4', 'p', 'ul', 'ol', 'section'])
        
        treatment_content = []
        stop_keywords = ["key points", "test your knowledge", "more information", "etiology", "symptoms", "references"]
        
        for element in all_content_elements:
            
            # Skip elements related to references or end-of-article material
            if element.name in ['section', 'h3', 'h4']:
                heading_text = element.get_text(strip=True)
                if any(stop.lower() in heading_text.lower() for stop in stop_keywords):
                    continue

            # Process Paragraphs
            if element.name == 'p':
                # Use simple get_text() on the P tag for better text flow
                text = element.get_text(separator=' ', strip=True) 
                
                # Clean up citations/artifacts (e.g., [1], [2, 3])
                text = re.sub(r'\[\s*\d+(?:,\s*\d+)*\s*\]', '', text) 
                
                # Cleanup drug/schema redundancy
                text = re.sub(r'(Topical crisaborole)\s*(Topical crisaborole)', r'\1', text, flags=re.IGNORECASE)
                text = re.sub(r'(Dupilumab|Tralokinumab|Ruxolitinib)\s*(is\s*a\s*Janus\s*kinase)\s*\1', r'\1 \2', text, flags=re.IGNORECASE)
                
                # Remove the remaining partial duplication artifacts found in the error output
                text = re.sub(r'(is not recomended for children).+\1', r'\1', text)
                text = re.sub(r'(Low-sedating or nonsedating antihistamines, such as loratadine, fexofenadine, or cetirizine may be useful, butheir eficacy has not ben established.)\s*\1', r'\1', text)
                
                # Simple cleanup for leading bolded drug names when repeated
                text = re.sub(r'^\s*([A-Za-z]+)\s*\1\s*', r'\1 ', text)


                if text and len(text.split()) > 5:
                    treatment_content.append(text)
            
            # Process Lists
            elif element.name in ['ul', 'ol']:
                list_items = []
                for li in element.find_all('li', recursive=False): 
                    # Get clean text from the list item, then clean up artifacts
                    item_text = li.get_text(separator=' ', strip=True)
                    item_text = re.sub(r'\[\s*\d+(?:,\s*\d+)*\s*\]', '', item_text)
                    
                    # Clean up repetition and list item cleanup
                    item_text = re.sub(r'(Topical crisaborole)\s*(Topical crisaborole)', r'\1', item_text, flags=re.IGNORECASE)
                    
                    # Remove bolding tag wrappers like 'General skin care' and trailing cleanup markers
                    item_text = re.sub(r'^(General skin care|Oral antihistamines|Reduction of emotional stress|Antistaphylococcal antibiotics|Eczema herpeticum)\s*', '', item_text).strip()
                    
                    # Remove list item content repetition from the beginning (e.g., 'Limithe frequency Limithe frequency...')
                    item_text = re.sub(r'^(.+?)\s*\1\s*', r'\1 ', item_text)
                    
                    if item_text:
                        treatment_content.append(f"  - {item_text}")
            
            # Process Subheadings
            elif element.name in ['h3', 'h4']:
                heading_text = element.get_text(strip=True)
                heading_text = re.sub(r'^\d+\.\s*', '', heading_text).strip()
                heading_text = re.sub(r'\[\s*\d+(?:,\s*\d+)*\s*\]', '', heading_text) 
                
                if element.name == 'h3':
                    treatment_content.append(f"\n--- {heading_text} ---\n")
                elif element.name == 'h4':
                    treatment_content.append(f"\n** {heading_text} **\n")


        if len(treatment_content) < 5:
            return "Scraping Error: Extracted content was too brief. The scraper found the wrapper but failed to find enough paragraph or list content inside."

        # Prepend the main heading manually as it was not included in the content_wrapper
        main_heading_text = main_heading.get_text(strip=True)
        main_heading_text = re.sub(r'\[\d+\]', '', main_heading_text).strip()
        treatment_content.insert(0, f"=== {main_heading_text} ===")
        
        return '\n\n'.join(treatment_content)

    except requests.exceptions.RequestException as e:
        return f"Request Error: Failed to access URL. Error: {e}"
    except Exception as e:
        return f"Scraping Error: An unexpected error occurred during parsing. Error: {e}"


def generate_file():
    """Generates the text file with the scraped treatment plan."""
    
    # --- ACTIVE SCRAPING CALL ---
    treatment_text = scrape_merck_manuals_section(TARGET_URL, TREATMENT_KEYWORDS)

    # Format the required header
    header = f"--- {TARGET_DISEASE} Treatment Plan (Extracted from Merck Manuals) ---"
    
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