import requests
from bs4 import BeautifulSoup, Tag
import json
import re
from typing import Dict, Any, List

def clean_text(text: str) -> str:
    """Removes excessive whitespace and cleans up text."""
    if not text:
        return ""
    # Replace multiple spaces/newlines/tabs with a single space, then strip leading/trailing whitespace
    return re.sub(r'\s+', ' ', text).strip()

def extract_table_data(table: Tag) -> List[List[str]]:
    """Helper function to extract data from a BeautifulSoup table tag."""
    table_data = []
    rows = table.find_all('tr')
    for row in rows:
        # Collect data from both header (th) and data (td) cells
        cols = row.find_all(['td', 'th'])
        row_data = [clean_text(ele.get_text()) for ele in cols]
        if any(row_data): # Only add non-empty rows
            table_data.append(row_data)
    return table_data

def scrape_lab_facilities(url: str) -> Dict[str, Any]:
    """Scrapes the Lab Facilities page using structural HTML analysis."""
    print(f"Scraping Lab Facilities: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {'url': url, 'title': 'Lab Facilities', 'lab_descriptions': []}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return data

    # Target the primary content area where labs are listed
    # Adjust this selector if necessary, but this is a good starting point
    main_content_div = soup.find('div', class_=re.compile(r'page-content|col-sm-\d+|article|container'))
    if not main_content_div:
        main_content_div = soup.body
        
    if not main_content_div:
        print("Error: Could not find main content area for labs.")
        return data

    # 1. Capture the general introductory text (The very first <p> or <section> content)
    intro_element = main_content_div.find('p')
    if intro_element:
        intro_text = clean_text(intro_element.get_text())
        if len(intro_text.split()) > 30 and 'Faculty Member' not in intro_text:
             data['lab_descriptions'].append({
                 'name': 'General Introduction',
                 'description': intro_text
             })

    # 2. Find all elements that look like Lab Headings (e.g., h4, h5, or bolded P)
    # This targets the actual structural elements
    
    # We will search for all <p> elements AND all h tags (h3-h6)
    potential_headings = main_content_div.find_all(re.compile(r'^h[3-6]$|p'))
    
    for heading in potential_headings:
        # Check if the text is long enough to be a lab name but not a full paragraph
        text = clean_text(heading.get_text())
        
        # Check for strong signals: contains "Lab" or "System", is relatively short,
        # and/or is an explicit heading tag (h3-h6)
        is_lab_heading = (
            (re.match(r'^h[3-6]$', heading.name)) or 
            ("Lab" in text or "System" in text) and len(text.split()) < 15
        )
        
        # Additional check: If it's a paragraph, check if it contains a bolded/strong child
        if heading.name == 'p' and (heading.find('strong') or heading.find('b')):
            is_lab_heading = True
        
        if is_lab_heading and text:
            # Found a lab name. Now find the description immediately following it.
            
            # The description is typically the *next* sibling <p> tag
            description_element = heading.find_next_sibling('p')
            
            # If the heading itself IS a paragraph, the description might be the element 
            # *after* that, or already part of the current element if it's a mix.
            # In the common case (heading followed by paragraph):
            
            description = ""
            if description_element and description_element != heading:
                description = clean_text(description_element.get_text())
            
            # Ensure the description is not just whitespace or navigation text
            if len(description.split()) > 10:
                data['lab_descriptions'].append({
                    'name': text,
                    'description': description
                })
                
    return data

def scrape_tuition_fees(url: str) -> Dict[str, Any]:
    """Scrapes the Tuition Fees page, focusing on tables."""
    print(f"Scraping Tuition Fees: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {'url': url, 'title': 'Tuition and Fees', 'tables': [], 'notes': []}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return data

    main_content_div = soup.find('div', class_=re.compile(r'page-content|col-sm-\d+|article|container'))
    if not main_content_div:
        main_content_div = soup.body

    if main_content_div:
        # 1. Extract data from all tables directly
        tables = main_content_div.find_all('table')
        
        # Titles are provided explicitly for the two main tables from the image, 
        # but we must find the titles from the page content itself for accuracy.
        
        for i, table in enumerate(tables):
            # Attempt to find a preceding heading (h2, h3, h4) for the table title
            prev_heading = table.find_previous(re.compile(r'h[2-4]'))
            title = clean_text(prev_heading.get_text()) if prev_heading else f"Fee Table {i+1}"
            
            table_data = extract_table_data(table)
            
            if table_data:
                data['tables'].append({'title': title, 'data': table_data})

        # 2. Extract surrounding notes (paragraphs, list items)
        for element in main_content_div.find_all(['p', 'li']):
            # Skip if the element is an empty paragraph or contains only an image
            if not element.get_text(strip=True) and not element.find(string=True, recursive=False):
                continue
                
            text = clean_text(element.get_text())
            # Simple check to filter out empty/short text
            if text and len(text.split()) > 5:
                # Add notes, avoiding known navigation text or elements that are part of the table logic
                # also avoid elements that are direct parents of the tables
                is_parent_of_table = bool(element.find('table'))
                
                if 'Faculty Member' not in text and not is_parent_of_table and text not in data['notes']:
                    data['notes'].append(text)

    return data

def main():
    """Main function to orchestrate the scraping and saving."""
    
    all_data = {}
    
    # --- Lab Facilities ---
    # NOTE: Using the lab_facilities_improved logic
    lab_url = "https://fse.ewubd.edu/computer-science-engineering/lab-facilities"
    all_data['lab_facilities'] = scrape_lab_facilities(lab_url)
    
    # --- Tuition Fees ---
    fee_url = "https://fse.ewubd.edu/computer-science-engineering/tuition-fees"
    all_data['tuition_fees'] = scrape_tuition_fees(fee_url)
    
    # Save JSON
    output_filename = 'ewu_cse_info_scraped_v5_final.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    lab_sections = len(all_data['lab_facilities']['lab_descriptions'])
    fee_tables = len(all_data['tuition_fees']['tables'])
    
    print("---")
    print(f"✅ Scraping complete!")
    print(f"Scraped {lab_sections} descriptions for Lab Facilities and {fee_tables} tables for Tuition Fees.")
    print(f"Saved all data to **{output_filename}**")

if __name__ == '__main__':
    main()