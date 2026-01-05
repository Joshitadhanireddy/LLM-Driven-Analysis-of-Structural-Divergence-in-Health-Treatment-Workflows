import os
import requests
from bs4 import BeautifulSoup, Tag
from typing import Optional
import re

# --- CONFIGURATION ---
TARGET_DISEASE = "Atopic Dermatitis (Eczema)"
TARGET_URL = "https://www.merckmanuals.com/professional/dermatologic-disorders/dermatitis/atopic-dermatitis-eczema?query=atopic%20dermatitis#Treatment_v961091"
TARGET_FILENAME = "atopic_dermatitis_merck.txt"
# Keywords to match section headings for treatment
TREATMENT_KEYWORDS = ["Treatment", "Management", "Therapy", "Prognosis", "Skin Care"]
# ---------------------

def scrape_merck_manuals_section(url: str, section_keywords: list) -> Optional[str]:
    """
    Scrapes specific sections from a Merck Manuals article, targeting modern SPA structures.
    It locates the treatment heading (often a <span>) and extracts subsequent content.
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

        # 3. Find the starting element based on your inspection (the span for "Treatment")
        # We look for the span that contains the word 'Treatment'
        # This will be our starting point, regardless of the main article wrapper.
        start_element_span = soup.find('span', string=lambda t: t and "Treatment" in t and "Atopic Dermatitis" in t)
        
        # Fallback search for a generic topic text span
        if not start_element_span:
             start_element_span = soup.find('span', class_=lambda c: c and 'topicText' in c)

        if not start_element_span:
            # If we can't find the specific starting span, we default to the broader article wrapper search
            content_wrapper = soup.find('div', id='article-container')
            if not content_wrapper:
                 return "Scraping Error: Could not locate the 'Treatment' starting element or a suitable main article wrapper."
            # If we found a wrapper, we'll search all elements inside it (less precise but covers the whole page)
            all_elements_to_iterate = content_wrapper.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'div', 'span'])
            
        else:
            # The start element is found! The content often follows the parent of this span
            # Get the parent that is likely a block-level element (div or p)
            parent_block = start_element_span.find_parent(['div', 'p']) or start_element_span.find_parent()
            
            # Start iterating from the element immediately following this block-level parent
            current_element = parent_block.find_next_sibling()
            
            # Collect all subsequent siblings (which should contain the content)
            all_elements_to_iterate = []
            while current_element:
                all_elements_to_iterate.append(current_element)
                current_element = current_element.find_next_sibling()


        # 4. Process all elements, starting capture when a keyword is matched
        treatment_content = []
        capturing = False
        sections_found = []
        
        # Sections that mark the end of the desired content
        stop_keywords = ["key points", "test your knowledge", "more information", "etiology", "symptoms"]
        
        # If we didn't find the specific span, iterate over all elements we found in the fallback wrapper
        if not start_element_span:
             for element in all_elements_to_iterate:
                
                # Check if this is a heading or span that acts as a heading
                if element.name in ['h2', 'h3', 'h4'] or (element.name == 'span' and element.get('class') and 'TopicPara_topicText' in element.get('class')):
                    heading_text = element.get_text(strip=True)
                    heading_text = re.sub(r'^\d+\.\s*', '', heading_text).strip()
                    
                    if any(stop.lower() in heading_text.lower() for stop in stop_keywords):
                        if capturing:
                            break
                        continue
                        
                    is_treatment_section = any(keyword.lower() in heading_text.lower() for keyword in section_keywords)

                    if not capturing and is_treatment_section:
                        capturing = True
                        sections_found.append(heading_text)
                        treatment_content.append(f"=== {heading_text} ===\n")
                    
                    elif capturing:
                        if element.name == 'h2' or (element.name == 'span' and is_treatment_section):
                            treatment_content.append(f"\n=== {heading_text} ===\n")
                        elif element.name == 'h3':
                            treatment_content.append(f"\n--- {heading_text} ---\n")
                        elif element.name == 'h4':
                            treatment_content.append(f"\n** {heading_text} **\n")
                            
                # Capture paragraphs and lists when capturing is True
                elif capturing and element.name in ['p', 'ul', 'ol']:
                    if element.name == 'p':
                        text = element.get_text(separator=' ', strip=True) 
                        text = re.sub(r'\[\d+\]', '', text) 
                        if text and len(text.split()) > 5:
                            treatment_content.append(text)
                    
                    elif element.name in ['ul', 'ol']:
                        list_items = [re.sub(r'\[\d+\]', '', li.get_text(separator=' ', strip=True)) 
                                      for li in element.find_all('li', recursive=False)]
                        if list_items:
                            treatment_content.append('\n'.join([f"  - {item}" for item in list_items]))
                        

        # If the start_element_span was found, the iteration must capture content
        # by searching inside the elements of all_elements_to_iterate
        if start_element_span:
             for element in all_elements_to_iterate:
                # We expect the main content to be immediately following the span's parent
                
                # Check for explicit stop condition
                if element.name in ['h2', 'h3'] and any(stop.lower() in element.get_text(strip=True).lower() for stop in stop_keywords):
                    break
                    
                # Search for all content elements within the current sibling element (handles deep nesting)
                nested_elements = element.find_all(['p', 'ul', 'ol', 'h3', 'h4'], recursive=True)
                
                # Check the element itself if it's a heading-like span or div title
                if element.name in ['span', 'div'] and element.get('class') and 'topicText' in element.get('class'):
                    heading_text = element.get_text(strip=True)
                    heading_text = re.sub(r'^\d+\.\s*', '', heading_text).strip()
                    treatment_content.append(f"\n--- {heading_text} ---\n")
                
                
                for item in nested_elements:
                    if item.name in ['h3', 'h4']:
                        heading_text = item.get_text(strip=True)
                        heading_text = re.sub(r'^\d+\.\s*', '', heading_text).strip()
                        treatment_content.append(f"\n--- {heading_text} ---\n")
                        
                    elif item.name == 'p':
                        text = item.get_text(separator=' ', strip=True) 
                        text = re.sub(r'\[\d+\]', '', text) 
                        if text and len(text.split()) > 5:
                            treatment_content.append(text)
                    
                    elif item.name in ['ul', 'ol']:
                        list_items = [re.sub(r'\[\d+\]', '', li.get_text(separator=' ', strip=True)) 
                                      for li in item.find_all('li', recursive=False)]
                        if list_items:
                            treatment_content.append('\n'.join([f"  - {item}" for item in list_items]))


        if len(treatment_content) < 5:
            available_keywords = ', '.join(section_keywords)
            return f"Scraping Error: Extracted content was too brief. Could not find sections matching keywords: {available_keywords} or locate the specific starting span."

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