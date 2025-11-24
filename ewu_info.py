import requests
from bs4 import BeautifulSoup, Tag
import json
import re
from typing import Dict, Any

def clean_text(text: str) -> str:
    """Removes excessive whitespace and cleans up text."""
    if not text:
        return ""
    # Replace multiple spaces/newlines/tabs with a single space, then strip leading/trailing whitespace
    return re.sub(r'\s+', ' ', text).strip()

def scrape_lab_facilities(url: str) -> Dict[str, Any]:
    """Scrapes the Lab Facilities page."""
    print(f"Scraping Lab Facilities: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {'url': url, 'title': 'Lab Facilities', 'sections': []}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return data

    soup = BeautifulSoup(resp.content, 'html.parser')

    # The main content on this page appears to be in the main content column.
    # Find the main article or content area, which usually follows the sidebar structure.
    main_content_div = soup.find('div', class_='col-sm-8')
    if not main_content_div:
        main_content_div = soup.find('article')

    if main_content_div:
        # We look for headings (h2, h3, h4) to structure the data, followed by their content.
        current_section = {'heading': 'Introduction', 'content': []}
        
        # Iterate over all children of the main content block
        for child in main_content_div.children:
            if isinstance(child, Tag):
                if child.name in ['h2', 'h3', 'h4']:
                    # New heading found, save the previous section and start a new one
                    if current_section['content']:
                        data['sections'].append({
                            'heading': clean_text(current_section['heading']),
                            'content': current_section['content']
                        })
                    
                    # Start new section
                    current_section = {'heading': child.get_text(strip=True), 'content': []}
                
                # Capture text content from paragraphs, lists, tables, etc.
                text_content = clean_text(child.get_text(separator=' ', strip=True))
                if text_content and child.name not in ['h2', 'h3', 'h4']:
                    current_section['content'].append(text_content)
            
            # Handle text nodes directly under the main div (for introductory text)
            elif isinstance(child, str) and child.strip():
                current_section['content'].append(clean_text(child))
        
        # Append the last collected section
        if current_section['content']:
            data['sections'].append({
                'heading': clean_text(current_section['heading']),
                'content': current_section['content']
            })

    # Join the list of content strings into one large string per section for cleaner JSON
    for section in data['sections']:
        section['content'] = '\n'.join(section['content'])
        
    return data

def scrape_tuition_fees(url: str) -> Dict[str, Any]:
    """Scrapes the Tuition Fees page, focusing on tables."""
    print(f"Scraping Tuition Fees: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {'url': url, 'title': 'Tuition and Fees', 'tables': [], 'notes': []}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return data

    soup = BeautifulSoup(resp.content, 'html.parser')

    # Find the main content area
    main_content_div = soup.find('div', class_='col-sm-8')
    if not main_content_div:
        main_content_div = soup.find('article')

    if main_content_div:
        # 1. Extract data from all tables
        tables = main_content_div.find_all('table')
        for table in tables:
            table_data = []
            # Find the caption or preceding heading for the table title
            table_title = table.find_previous(['h2', 'h3', 'h4', 'strong', 'caption'])
            title = clean_text(table_title.get_text(strip=True)) if table_title else "Fee Structure Table"
            
            # Extract rows
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                row_data = [clean_text(ele.get_text()) for ele in cols]
                table_data.append(row_data)
                
            if table_data:
                data['tables'].append({'title': title, 'data': table_data})

        # 2. Extract notes and general text that is not part of a table
        # We look for paragraphs that follow tables or headings
        notes_elements = main_content_div.find_all(['p', 'li'])
        for element in notes_elements:
            # Simple check to filter out elements that are clearly part of table extraction logic
            text = clean_text(element.get_text())
            # Skip if the text is empty or is already part of the tables data (e.g., table cells)
            if text and not any(text in item['content'] for item in data['tables'] if 'content' in item):
                 # Add to notes list, avoiding duplicates
                if text not in data['notes']:
                    data['notes'].append(text)

    # Final cleanup of notes to remove headers that might have been caught
    data['notes'] = [note for note in data['notes'] if len(note.split()) > 3]

    return data

def main():
    """Main function to orchestrate the scraping and saving."""
    
    # Store all data structures
    all_data = {}
    
    # --- Lab Facilities ---
    lab_url = "https://fse.ewubd.edu/computer-science-engineering/lab-facilities"
    all_data['lab_facilities'] = scrape_lab_facilities(lab_url)
    
    # --- Tuition Fees ---
    fee_url = "https://fse.ewubd.edu/computer-science-engineering/tuition-fees"
    all_data['tuition_fees'] = scrape_tuition_fees(fee_url)
    
    # Save JSON
    output_filename = 'ewu_cse_info_scraped.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    lab_sections = len(all_data['lab_facilities']['sections'])
    fee_tables = len(all_data['tuition_fees']['tables'])
    
    print("---")
    print(f"✅ Scraping complete!")
    print(f"Scraped {lab_sections} sections for Lab Facilities and {fee_tables} tables for Tuition Fees.")
    print(f"Saved all data to **{output_filename}**")

if __name__ == '__main__':
    main()