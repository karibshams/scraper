import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """Removes excessive whitespace and cleans up text."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_course_block(block) -> Dict[str, Any]:
    """
    Given a BeautifulSoup tag block for one course, extract details:
    code, title, credit hours / teaching scheme, prerequisite (if any),
    objective, course outcomes (list), course contents.
    """
    result: Dict[str, Any] = {
        'code': None,
        'title': None,
        'credit_hours': None,
        'teaching_scheme': None,
        'prerequisite': None,
        'objective': None,
        'outcomes': [],
        'contents': None
    }

    # Typically the heading (#### [link] COURSECODE: Title)
    header = block.find(['h4','h5','h6']) or block.find('strong')
    if header:
        header_text = header.get_text(separator=" ", strip=True)
        # Example: "CSE487: Computer and Cyber Security"
        m = re.match(r'([A-Z]{3}\d+)\s*[:\-]\s*(.*)', header_text)
        if m:
            result['code'] = m.group(1).strip()
            result['title'] = clean_text(m.group(2).strip())
        else:
            # Fallback if the regex doesn't match the expected code: title format
            result['title'] = clean_text(header_text)
    
    # Extract all text from the block for multi-line/section regex search
    scheme_text = block.get_text(separator="|", strip=True)
    
    # Try to extract "Credit Hours and Teaching Scheme:" section
    # Note: The original logic for 'teaching_scheme' extraction is maintained.
    m2 = re.search(r'Credit Hours.*?Theory.*?Laboratory.*?Total', scheme_text, re.IGNORECASE | re.DOTALL)
    if m2:
        result['teaching_scheme'] = clean_text(m2.group(0))
        # A simple attempt to also grab 'credit_hours' from this scheme text if possible
        credit_match = re.search(r'Credit\s*Hours\s*:\s*(\d+)', m2.group(0), re.IGNORECASE)
        if credit_match:
             result['credit_hours'] = credit_match.group(1).strip()


    # Prerequisite: Capture until 2+ spaces (paragraph break) or 'Course Objective' or end of string
    m3 = re.search(r'Prerequisite\s*[:\-]?\s*(.*?)(?:\s{2,}|Course Objective|$)', scheme_text, re.IGNORECASE)
    if m3:
        result['prerequisite'] = clean_text(m3.group(1))
    
    # Objective: Capture until 'Course Outcomes'
    m4 = re.search(r'Course Objective\s*[:\-]?\s*(.*?)Course Outcomes', scheme_text, re.IGNORECASE | re.DOTALL)
    if m4:
        result['objective'] = clean_text(m4.group(1))
    
    # Outcomes: after "Course Outcomes (COs):" until maybe "Course Contents"
    m5 = re.search(r'Course Outcomes\s*[(]COs[)]\s*:(.*?)(?:Course Contents|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m5:
        # split by CO1, CO2 etc.
        outcomes_text = m5.group(1)
        # Find all CO# followed by the description until the next CO# or end of string
        outcomes = re.findall(r'(CO\d+)\s+(.*?)((?=CO\d+)|$)', outcomes_text, re.DOTALL)
        for oc in outcomes:
            result['outcomes'].append({'code': oc[0].strip(), 'description': clean_text(oc[1])})
    
    # Contents: until the next level heading (e.g., ####) or end of string
    m6 = re.search(r'Course Contents\s*[:\-]?\s*(.*?)((?=####)|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m6:
        result['contents'] = clean_text(m6.group(1))

    return result

def scrape_courses_from_page(url: str) -> List[Dict[str, Any]]:
    """Fetches a page, parses the HTML, and extracts all course blocks."""
    print(f"Scraping: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(resp.content, 'html.parser')

    courses: List[Dict[str, Any]] = []
    
    # The courses are primarily identified by an anchor tag whose text contains a course code (e.g., CSExxx)
    # The actual course content often follows this anchor/header.
    # We will find the parent of the anchor which is usually the containing block.
    
    # Using 'h4' or 'h5' as a more robust starting point for course blocks, as the anchor is often inside them.
    # The provided original logic was based on finding the anchor, which might be sufficient, 
    # but let's try to ensure we capture the whole content block.
    
    # Based on observation of similar university sites, the course block starts with a heading tag.
    
    # We will stick to the original logic which targets the specific structure implied by the original code.
    processed_blocks = set() # To avoid processing the same course twice if multiple anchors point to it
    
    for anchor in soup.select('a[href]'):
        # Check if the anchor text looks like a course code (e.g., CSE487)
        href = anchor.get('href')
        anchor_text = anchor.get_text(strip=True)
        
        # Check if the text matches the course code pattern.
        if re.search(r'[A-Z]{3}\d{3}', anchor_text) or re.search(r'[A-Z]{3}\d{3}', anchor.parent.get_text(strip=True)):
            
            # Find the closest parent that contains the entire course details
            # This is often an 'h4' or a 'div' that wraps the content.
            # Start at the anchor's parent.
            block = anchor.parent
            
            # The course data is often spread across the heading and its following sibling elements.
            # For simplicity and to match the original function's structure:
            # We'll use the parent element that contains the anchor/header as the "block" 
            # and rely on 'parse_course_block' to extract text via `block.get_text(separator="|", strip=True)`.
            
            # To ensure we don't duplicate, use the element as a key.
            if block not in processed_blocks:
                courses.append(parse_course_block(block))
                processed_blocks.add(block)

    return courses

def main():
    """Main function to orchestrate the scraping and saving."""
    urls = [
        "https://fse.ewubd.edu/computer-science-engineering/core-courses",
        "https://fse.ewubd.edu/computer-science-engineering/elective-courses"
    ]
    all_data = {}
    
    for url in urls:
        # key by a friendly name
        key = 'core_courses' if 'core-courses' in url else 'elective_courses'
        all_data[key] = scrape_courses_from_page(url)
    
    # Save JSON
    output_filename = 'ewu_cse_courses_full.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    core_count = len(all_data.get('core_courses', []))
    elective_count = len(all_data.get('elective_courses', []))
    print("---")
    print(f"✅ Scraping complete!")
    print(f"Saved {core_count} core courses and {elective_count} elective courses to **{output_filename}**")

if __name__ == '__main__':
    main()