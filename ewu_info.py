import requests
from bs4 import BeautifulSoup, Tag
import json
import re
from typing import Dict, Any, List

def clean_text(text: str) -> str:
    """Removes excessive whitespace and cleans up text."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_table_data(table: Tag) -> List[List[str]]:
    """Helper function to extract data from a BeautifulSoup table tag."""
    table_data = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all(['td', 'th'])
        row_data = [clean_text(ele.get_text()) for ele in cols]
        if any(row_data):
            table_data.append(row_data)
    return table_data

def scrape_lab_facilities(url: str) -> Dict[str, Any]:
    """Scrapes the Lab Facilities page with improved extraction."""
    print(f"Scraping Lab Facilities: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {'url': url, 'title': 'Lab Facilities', 'introduction': '', 'labs': []}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return data

    # Find main content area
    main_content = soup.find('div', class_=re.compile(r'page-content|col-sm-|article|container|content'))
    if not main_content:
        main_content = soup.body
        
    if not main_content:
        print("Error: Could not find main content area")
        return data

    # Extract all paragraphs and headings in order
    elements = main_content.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    # First, capture the introductory paragraph(s)
    intro_paras = []
    for elem in elements:
        text = clean_text(elem.get_text())
        if not text:
            continue
            
        # Introduction paragraphs typically come before lab-specific content
        if elem.name == 'p' and len(text.split()) > 20:
            # Check if this looks like intro text (mentions university, programs, etc.)
            if any(keyword in text.lower() for keyword in ['university', 'program', 'student', 'faculty', 'department']):
                intro_paras.append(text)
            # Stop collecting intro when we hit a lab heading
            if 'lab:' in text.lower() or text.endswith('Lab:'):
                break
        elif elem.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
            # Stop at first heading
            break
    
    if intro_paras:
        data['introduction'] = ' '.join(intro_paras)

    # Now extract lab information
    current_lab = None
    
    for i, elem in enumerate(elements):
        text = clean_text(elem.get_text())
        if not text:
            continue
        
        # Detect lab headings - look for patterns like "Lab Name:" or bold lab names
        is_lab_heading = False
        
        # Pattern 1: Ends with "Lab:" or "Lab."
        if re.search(r'\bLab[:.]?\s*$', text, re.IGNORECASE):
            is_lab_heading = True
        
        # Pattern 2: Contains "Lab" and is in a heading tag or bold
        elif 'Lab' in text and (elem.name in ['h3', 'h4', 'h5', 'h6'] or elem.find(['strong', 'b'])):
            is_lab_heading = True
        
        # Pattern 3: Short text (< 15 words) in bold that looks like a title
        elif elem.name == 'p' and elem.find(['strong', 'b']) and len(text.split()) < 15:
            # Check if next element is a longer paragraph (description)
            next_elem = elements[i + 1] if i + 1 < len(elements) else None
            if next_elem and next_elem.name == 'p':
                next_text = clean_text(next_elem.get_text())
                if len(next_text.split()) > 15:
                    is_lab_heading = True
        
        if is_lab_heading:
            # Save previous lab if exists
            if current_lab and current_lab.get('description'):
                data['labs'].append(current_lab)
            
            # Start new lab
            current_lab = {
                'name': text.rstrip(':. '),
                'description': ''
            }
        
        # Collect description for current lab
        elif current_lab and elem.name == 'p':
            # This paragraph belongs to the current lab
            if len(text.split()) > 10:  # Meaningful description
                if current_lab['description']:
                    current_lab['description'] += ' ' + text
                else:
                    current_lab['description'] = text
    
    # Add the last lab
    if current_lab and current_lab.get('description'):
        data['labs'].append(current_lab)
    
    print(f"  → Extracted {len(data['labs'])} labs")
    return data

def scrape_tuition_fees(url: str) -> Dict[str, Any]:
    """Scrapes the Tuition Fees page with improved extraction."""
    print(f"Scraping Tuition Fees: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {
        'url': url, 
        'title': 'Tuition and Fees', 
        'tables': [],
        'additional_info': []
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return data

    main_content = soup.find('div', class_=re.compile(r'page-content|col-sm-|article|container|content'))
    if not main_content:
        main_content = soup.body

    if not main_content:
        print("Error: Could not find main content area")
        return data

    # Extract all tables
    tables = main_content.find_all('table')
    
    for table in tables:
        # Find the table heading (look backwards for h2, h3, h4)
        title = None
        prev_elem = table.find_previous(['h2', 'h3', 'h4', 'h5'])
        
        if prev_elem:
            title = clean_text(prev_elem.get_text())
        else:
            # Try to infer from context
            title = "Fee Table"
        
        table_data = extract_table_data(table)
        
        if table_data:
            data['tables'].append({
                'title': title,
                'data': table_data
            })
    
    # Extract additional information (paragraphs and lists near tables)
    all_text_elements = main_content.find_all(['p', 'li', 'div'])
    
    for elem in all_text_elements:
        # Skip if element contains a table
        if elem.find('table'):
            continue
        
        text = clean_text(elem.get_text())
        
        # Filter criteria
        if (text and 
            len(text.split()) > 3 and  # More than 3 words
            'Faculty Member' not in text and  # Not navigation
            text not in data['additional_info']):  # Not duplicate
            
            # Check if it's meaningful content
            if any(char.isalnum() for char in text):
                data['additional_info'].append(text)
    
    print(f"  → Extracted {len(data['tables'])} tables and {len(data['additional_info'])} additional notes")
    return data

def main():
    """Main function to orchestrate the scraping and saving."""
    
    print("=" * 60)
    print("EWU CSE Department Web Scraper")
    print("=" * 60)
    
    all_data = {}
    
    # Lab Facilities
    lab_url = "https://fse.ewubd.edu/computer-science-engineering/lab-facilities"
    all_data['lab_facilities'] = scrape_lab_facilities(lab_url)
    
    # Tuition Fees
    fee_url = "https://fse.ewubd.edu/computer-science-engineering/tuition-fees"
    all_data['tuition_fees'] = scrape_tuition_fees(fee_url)
    
    # Save JSON
    output_filename = 'ewu_cse_complete_data.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ SCRAPING COMPLETE!")
    print("=" * 60)
    print(f"Lab Facilities:")
    print(f"  • Introduction: {'Yes' if all_data['lab_facilities']['introduction'] else 'No'}")
    print(f"  • Labs extracted: {len(all_data['lab_facilities']['labs'])}")
    
    if all_data['lab_facilities']['labs']:
        print(f"\n  Lab names:")
        for lab in all_data['lab_facilities']['labs']:
            print(f"    - {lab['name']}")
    
    print(f"\nTuition Fees:")
    print(f"  • Tables extracted: {len(all_data['tuition_fees']['tables'])}")
    print(f"  • Additional notes: {len(all_data['tuition_fees']['additional_info'])}")
    
    if all_data['tuition_fees']['tables']:
        print(f"\n  Table titles:")
        for table in all_data['tuition_fees']['tables']:
            print(f"    - {table['title']}")
    
    print(f"\n📄 Data saved to: {output_filename}")
    print("=" * 60)

if __name__ == '__main__':
    main()