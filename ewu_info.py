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

def save_html_debug(soup, filename):
    """Save prettified HTML for debugging."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print(f"  💾 Saved HTML to {filename} for inspection")

def diagnose_page_structure(url: str, page_name: str):
    """Diagnose the page structure to understand what we're dealing with."""
    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {page_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        print(f"✓ Status Code: {resp.status_code}")
        print(f"✓ Content Length: {len(resp.content)} bytes")
    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        return None
    
    soup = BeautifulSoup(resp.content, 'lxml')
    
    # Save HTML for manual inspection
    save_html_debug(soup, f'debug_{page_name.lower().replace(" ", "_")}.html')
    
    # Check for common content containers
    print(f"\n📦 Checking for content containers:")
    containers = [
        ('div.page-content', soup.find('div', class_='page-content')),
        ('div.container', soup.find('div', class_='container')),
        ('div.content', soup.find('div', class_='content')),
        ('article', soup.find('article')),
        ('main', soup.find('main')),
        ('div[class*="col-"]', soup.find('div', class_=re.compile(r'col-'))),
    ]
    
    found_container = None
    for name, container in containers:
        if container:
            print(f"  ✓ Found: {name}")
            if not found_container:
                found_container = container
        else:
            print(f"  ✗ Not found: {name}")
    
    if not found_container:
        print(f"  ⚠ No standard container found, using body")
        found_container = soup.body
    
    # Analyze content structure
    print(f"\n📊 Content structure analysis:")
    if found_container:
        all_tags = found_container.find_all()
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
        
        print(f"  Total elements: {len(all_tags)}")
        print(f"\n  Top 10 most common tags:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {tag}: {count}")
        
        # Check for paragraphs
        paragraphs = found_container.find_all('p')
        print(f"\n  📝 Paragraphs found: {len(paragraphs)}")
        if paragraphs:
            print(f"    First paragraph preview:")
            first_text = clean_text(paragraphs[0].get_text())
            print(f"    '{first_text[:100]}...'")
        
        # Check for headings
        headings = found_container.find_all(re.compile(r'^h[1-6]$'))
        print(f"\n  📌 Headings found: {len(headings)}")
        for i, h in enumerate(headings[:5]):
            print(f"    {h.name}: {clean_text(h.get_text())[:60]}")
        
        # Check for tables
        tables = found_container.find_all('table')
        print(f"\n  📋 Tables found: {len(tables)}")
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"    Table {i+1}: {len(rows)} rows")
    
    return soup

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
    """Scrapes the Lab Facilities page."""
    print(f"\n{'='*60}")
    print(f"SCRAPING LAB FACILITIES")
    print(f"{'='*60}")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    data: Dict[str, Any] = {
        'url': url, 
        'title': 'Lab Facilities', 
        'introduction': '', 
        'labs': [],
        'all_content': []  # Capture everything as fallback
    }

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'lxml')
    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        return data

    # Try multiple content selectors
    main_content = None
    for selector in ['div.page-content', 'div.container', 'article', 'main', 'body']:
        if '.' in selector:
            tag, cls = selector.split('.')
            main_content = soup.find(tag, class_=cls)
        else:
            main_content = soup.find(selector)
        
        if main_content:
            print(f"✓ Using content from: {selector}")
            break
    
    if not main_content:
        print(f"✗ Could not find content area")
        return data
    
    # Get ALL text content as fallback
    all_paragraphs = main_content.find_all('p')
    print(f"✓ Found {len(all_paragraphs)} paragraphs")
    
    for p in all_paragraphs:
        text = clean_text(p.get_text())
        if text and len(text) > 20:
            data['all_content'].append(text)
    
    # Try to find structured lab content
    # Look for bold text followed by descriptions
    for i, p in enumerate(all_paragraphs):
        # Check if this paragraph has bold text
        bold = p.find(['strong', 'b'])
        if bold:
            lab_name = clean_text(bold.get_text())
            
            # Check if this looks like a lab name
            if 'Lab' in lab_name or 'System' in lab_name:
                # Get description from this paragraph or next
                desc_text = clean_text(p.get_text())
                
                # If the bold text is the whole paragraph, get next paragraph
                if desc_text == lab_name and i + 1 < len(all_paragraphs):
                    desc_text = clean_text(all_paragraphs[i + 1].get_text())
                
                if len(desc_text) > len(lab_name) + 20:
                    data['labs'].append({
                        'name': lab_name,
                        'description': desc_text
                    })
                    print(f"  ✓ Found lab: {lab_name}")
    
    # Extract introduction (first substantial paragraph)
    for p in all_paragraphs:
        text = clean_text(p.get_text())
        if len(text.split()) > 30:
            data['introduction'] = text
            print(f"✓ Found introduction ({len(text)} chars)")
            break
    
    print(f"\n📊 Results: {len(data['labs'])} labs, {len(data['all_content'])} paragraphs total")
    return data

def scrape_tuition_fees(url: str) -> Dict[str, Any]:
    """Scrapes the Tuition Fees page."""
    print(f"\n{'='*60}")
    print(f"SCRAPING TUITION FEES")
    print(f"{'='*60}")
    
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
        print(f"✗ Error: {e}")
        return data

    # Find main content
    main_content = None
    for selector in ['div.page-content', 'div.container', 'article', 'main', 'body']:
        if '.' in selector:
            tag, cls = selector.split('.')
            main_content = soup.find(tag, class_=cls)
        else:
            main_content = soup.find(selector)
        
        if main_content:
            print(f"✓ Using content from: {selector}")
            break

    if not main_content:
        print(f"✗ Could not find content area")
        return data

    # Extract tables
    tables = main_content.find_all('table')
    print(f"✓ Found {len(tables)} tables")
    
    for i, table in enumerate(tables):
        # Look for table title
        title = f"Fee Table {i+1}"
        prev_heading = table.find_previous(re.compile(r'^h[2-6]$'))
        if prev_heading:
            title = clean_text(prev_heading.get_text())
        
        table_data = extract_table_data(table)
        
        if table_data:
            data['tables'].append({
                'title': title,
                'data': table_data
            })
            print(f"  ✓ Extracted table: {title} ({len(table_data)} rows)")
    
    # Extract additional text
    for p in main_content.find_all('p'):
        text = clean_text(p.get_text())
        if text and len(text) > 20 and text not in data['additional_info']:
            data['additional_info'].append(text)
    
    print(f"\n📊 Results: {len(data['tables'])} tables, {len(data['additional_info'])} notes")
    return data

def main():
    """Main function."""
    
    print("\n" + "="*60)
    print("EWU CSE DEPARTMENT WEB SCRAPER - DIAGNOSTIC MODE")
    print("="*60)
    
    # URLs
    lab_url = "https://fse.ewubd.edu/computer-science-engineering/lab-facilities"
    fee_url = "https://fse.ewubd.edu/computer-science-engineering/tuition-fees"
    
    # First, diagnose both pages
    print("\n🔍 PHASE 1: DIAGNOSIS")
    diagnose_page_structure(lab_url, "Lab Facilities")
    diagnose_page_structure(fee_url, "Tuition Fees")
    
    # Now scrape with informed approach
    print("\n\n🔍 PHASE 2: SCRAPING")
    all_data = {}
    all_data['lab_facilities'] = scrape_lab_facilities(lab_url)
    all_data['tuition_fees'] = scrape_tuition_fees(fee_url)
    
    # Save results
    output_filename = 'ewu_cse_complete_data.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    # Final summary
    print("\n" + "="*60)
    print("✅ SCRAPING COMPLETE!")
    print("="*60)
    print(f"\n📄 Files created:")
    print(f"  • {output_filename}")
    print(f"  • debug_lab_facilities.html")
    print(f"  • debug_tuition_fees.html")
    print(f"\n💡 Check the debug HTML files to see the actual page structure")
    print("="*60)

if __name__ == '__main__':
    main()