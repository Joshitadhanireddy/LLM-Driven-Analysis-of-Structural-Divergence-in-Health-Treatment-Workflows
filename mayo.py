import requests
from bs4 import BeautifulSoup
from typing import Optional

def scrape_eczema_treatment(url: str) -> Optional[str]:
    """
    Scrapes the provided Mayo Clinic URL for the treatment plan and returns the extracted text. 

    Args:
        url: The URL of the Mayo Clinic article.

    Returns:
        A string containing the extracted treatment text, or None if extraction fails.
    """
    print(f"Attempting to scrape: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')
        main_content = soup.find('div', id='main-content')
        if not main_content:
            main_content = soup.find('div', class_='content')
            if not main_content:
                print("Error: Could not find the main content block using known IDs or classes.")
                return None
        treatment_heading = None
        for tag_name in ['h2', 'h3']:
            treatment_heading = main_content.find(tag_name, string=lambda t: t and 'treatment' in t.lower())
            if treatment_heading:
                print(f"Found treatment section under {treatment_heading.name}: {treatment_heading.get_text(strip=True)}")
                break

        if not treatment_heading:
            print("Error: Could not find any heading containing 'treatment' in the main content.")
            return None

        treatment_plan_text = []
        current_element = treatment_heading.next_sibling

        while current_element:
            if current_element.name in ['h2', 'h3']:
                if current_element.name == 'h2' or (treatment_heading.name == 'h3' and current_element.name == 'h3'):
                    break

            if current_element.name in ['p', 'ul', 'ol', 'h3', 'h4']:
                text = current_element.get_text(separator='\n', strip=True)
                if text:
                    if current_element.name in ['h3', 'h4']:
                        treatment_plan_text.append(f"\n## {text}\n")
                    elif current_element.name in ['ul', 'ol']:
                         treatment_plan_text.append(f"\n{text}\n")
                    else:
                        treatment_plan_text.append(text)

            current_element = current_element.next_sibling

        if not treatment_plan_text:
            print("Error: Extracted content for treatment plan is empty.")
            return None

        clean_text = "\n\n".join(filter(None, treatment_plan_text))
        return f"--- Progeria Treatment Plan (Extracted from Mayo Clinic) ---\n\n{clean_text}"

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

if __name__ == '__main__':
    mayo_clinic_url = "https://www.mayoclinic.org/diseases-conditions/progeria/diagnosis-treatment/drc-20356043"
    treatment_info = scrape_eczema_treatment(mayo_clinic_url)
    output_filepath = "progeria_mayo.txt"

    if treatment_info:
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(treatment_info)
            print("\n" + "="*50)
            print(f"SCRAPING SUCCESSFUL: Content saved to {output_filepath}")
            print("="*50)
        except IOError as e:
            print(f"ERROR: Could not write to file {output_filepath}. {e}")
    else:
        print("\n" + "="*50)
        print("SCRAPING FAILED: Check the URL or the element selectors.")
        print("="*50)