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
    """Scrapes the Lab Facilities page - extracts labs with bold headings."""
    print(f"Scraping Lab Facilities: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {
        'url': url, 
        'title': 'Lab Facilities', 
        'introduction': '', 
        'labs': []
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return data

    # Find main content area
    main_content = soup.find('div', class_='page-content')
    if not main_content:
        main_content = soup.find('div', class_=re.compile(r'col-sm-'))
    if not main_content:
        main_content = soup.body
        
    if not main_content:
        print("  ✗ Could not find content area")
        return data

    # Get all paragraphs
    paragraphs = main_content.find_all('p')
    print(f"  ✓ Found {len(paragraphs)} paragraphs")
    
    # First paragraph is usually the introduction
    if paragraphs:
        first_text = clean_text(paragraphs[0].get_text())
        if len(first_text.split()) > 30:
            data['introduction'] = first_text
            print(f"  ✓ Captured introduction ({len(first_text)} chars)")
    
    # Extract labs - they have bold text at the start
    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        text = clean_text(p.get_text())
        
        # Skip empty or very short paragraphs
        if not text or len(text) < 10:
            i += 1
            continue
        
        # Check if this paragraph starts with bold text
        bold = p.find(['strong', 'b'])
        
        if bold:
            # Get the bold text as lab name
            bold_text = clean_text(bold.get_text())
            
            # Check if this looks like a lab heading (contains "Lab" or ends with ":")
            if 'Lab' in bold_text or 'lab' in bold_text or bold_text.endswith(':'):
                lab_name = bold_text.rstrip(':').strip()
                
                # The description is the rest of this paragraph after the bold text
                # We need to get text after the bold element
                description = ""
                
                # Get all text from the paragraph
                full_text = text
                
                # If the bold text is at the start, the rest is the description
                if full_text.startswith(bold_text):
                    description = full_text[len(bold_text):].strip().lstrip(':').strip()
                else:
                    description = full_text
                
                # If description is too short, it might be in the next paragraph
                if len(description.split()) < 15 and i + 1 < len(paragraphs):
                    next_text = clean_text(paragraphs[i + 1].get_text())
                    # Check if next paragraph doesn't have bold (not another lab)
                    if not paragraphs[i + 1].find(['strong', 'b']):
                        description = next_text
                        i += 1  # Skip the next paragraph since we used it
                
                if description and len(description.split()) > 10:
                    data['labs'].append({
                        'name': lab_name,
                        'description': description
                    })
                    print(f"  ✓ Extracted: {lab_name}")
        
        i += 1
    
    print(f"  → Total labs extracted: {len(data['labs'])}")
    return data

def scrape_tuition_fees(url: str) -> Dict[str, Any]:
    """Scrapes the Tuition Fees page, focusing on tables."""
    print(f"Scraping Tuition Fees: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {
        'url': url, 
        'title': 'Tuition and Fees', 
        'tables': [],
        'notes': []
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error fetching {url}: {e}")
        return data

    # Find main content
    main_content = soup.find('div', class_='page-content')
    if not main_content:
        main_content = soup.find('div', class_=re.compile(r'col-sm-'))
    if not main_content:
        main_content = soup.body

    if not main_content:
        print("  ✗ Could not find content area")
        return data

    # Extract all tables
    tables = main_content.find_all('table')
    print(f"  ✓ Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        # Try to find the heading before this table
        title = f"Fee Table {i+1}"
        
        # Look for heading tags before the table
        prev_heading = table.find_previous(re.compile(r'^h[1-6]$'))
        if prev_heading:
            title_text = clean_text(prev_heading.get_text())
            if title_text and len(title_text) < 100:
                title = title_text
        
        # Extract table data
        table_data = extract_table_data(table)
        
        if table_data:
            data['tables'].append({
                'title': title,
                'data': table_data
            })
            print(f"  ✓ Extracted: {title} ({len(table_data)} rows)")
    
    # Extract notes/additional information from paragraphs
    paragraphs = main_content.find_all('p')
    for p in paragraphs:
        text = clean_text(p.get_text())
        
        # Filter out navigation and very short text
        if (text and 
            len(text.split()) > 5 and 
            'Faculty Member' not in text and
            text not in data['notes']):
            data['notes'].append(text)
    
    print(f"  → Total tables: {len(data['tables'])}, Notes: {len(data['notes'])}")
    return data

def main():
    """Main function to orchestrate the scraping and saving."""
    
    print("="*60)
    print("EWU CSE DEPARTMENT WEB SCRAPER")
    print("="*60)
    
    all_data = {}
    
    # Scrape Lab Facilities
    lab_url = "https://fse.ewubd.edu/computer-science-engineering/lab-facilities"
    all_data['lab_facilities'] = scrape_lab_facilities(lab_url)
    
    # Scrape Tuition Fees
    fee_url = "https://fse.ewubd.edu/computer-science-engineering/tuition-fees"
    all_data['tuition_fees'] = scrape_tuition_fees(fee_url)
    
    # Save JSON
    output_filename = 'ewu_cse_complete_data.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("✅ SCRAPING COMPLETE!")
    print("="*60)
    
    print(f"\n📚 Lab Facilities:")
    print(f"  • Introduction: {'Yes' if all_data['lab_facilities']['introduction'] else 'No'}")
    print(f"  • Labs extracted: {len(all_data['lab_facilities']['labs'])}")
    
    if all_data['lab_facilities']['labs']:
        print(f"\n  Lab names:")
        for lab in all_data['lab_facilities']['labs']:
            print(f"    • {lab['name']}")
    
    print(f"\n💰 Tuition Fees:")
    print(f"  • Tables extracted: {len(all_data['tuition_fees']['tables'])}")
    print(f"  • Additional notes: {len(all_data['tuition_fees']['notes'])}")
    
    if all_data['tuition_fees']['tables']:
        print(f"\n  Table titles:")
        for table in all_data['tuition_fees']['tables']:
            print(f"    • {table['title']}")
    
    print(f"\n📄 Data saved to: {output_filename}")
    print("="*60)

if __name__ == '__main__':
    main()