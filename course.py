import requests
from bs4 import BeautifulSoup, Tag
import json
import re
from typing import List, Dict, Any, Union

def clean_text(text: str) -> str:
    """Removes excessive whitespace and cleans up text."""
    if not text:
        return ""
    # Replace multiple spaces/newlines/tabs with a single space, then strip leading/trailing whitespace
    return re.sub(r'\s+', ' ', text).strip()

def parse_course_block(block: Union[Tag, str]) -> Dict[str, Any]:
    """
    Given a BeautifulSoup tag block (or string) for one course, extract details.
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
    
    # 1. Get the combined text from the block
    if isinstance(block, Tag):
        scheme_text = block.get_text(separator="|", strip=True)
    else:
        scheme_text = block

    # 2. Extract Code and Title (usually at the beginning)
    # Search for the first instance of a course code pattern
    header_match = re.search(r'([A-Z]{3}\d+)\s*[:\-\s]*(.*?)(?=\|Credit Hours|\|Course Objective|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if header_match:
        result['code'] = header_match.group(1).strip()
        # The title is the text following the code, up to the next section delimiter
        title_raw = header_match.group(2).split('|')[0] # Only take the first part before any separator
        result['title'] = clean_text(title_raw.strip())
    else:
        # Fallback for title if no code is found
        result['title'] = clean_text(scheme_text.split('|')[0])


    # 3. Credit Hours / Teaching Scheme
    # Search for the full scheme text including Theory/Lab/Total
    m2 = re.search(r'(Credit Hours.*?Theory.*?Laboratory.*?Total.*?)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m2:
        scheme_raw = clean_text(m2.group(1))
        # Remove pipe separators to clean up the scheme text before saving
        result['teaching_scheme'] = scheme_raw.replace('|', ' ')
        
        # Try to extract credit hours (e.g., Credit Hours : 3)
        credit_match = re.search(r'Credit\s*Hours\s*:\s*(\d+)', scheme_raw, re.IGNORECASE)
        if credit_match:
             result['credit_hours'] = credit_match.group(1).strip()

    # 4. Prerequisite
    # Capture until the next section header (Credit or Objective) or multiple spaces
    m3 = re.search(r'Prerequisite\s*[:\-]?\s*(.*?)(?:\|Course Objective|\|Credit Hours|\s{2,}|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m3:
        # Clean up the Prereq text; remove trailing pipes
        prereq_raw = m3.group(1).split('|')[0]
        result['prerequisite'] = clean_text(prereq_raw)
    
    # 5. Objective
    # Capture until 'Course Outcomes'
    m4 = re.search(r'Course Objective\s*[:\-]?\s*(.*?)Course Outcomes', scheme_text, re.IGNORECASE | re.DOTALL)
    if m4:
        result['objective'] = clean_text(m4.group(1))
    
    # 6. Outcomes
    # after "Course Outcomes (COs):" until maybe "Course Contents"
    m5 = re.search(r'Course Outcomes\s*[(]COs[)]\s*:(.*?)(?:Course Contents|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m5:
        outcomes_text = m5.group(1)
        # Find all CO# followed by the description until the next CO# or end of string
        outcomes = re.findall(r'(CO\d+)\s+(.*?)((?=CO\d+)|$)', outcomes_text, re.DOTALL)
        for oc in outcomes:
            result['outcomes'].append({'code': oc[0].strip(), 'description': clean_text(oc[1])})
    
    # 7. Contents
    # Capture from "Course Contents" until the end of the content block
    m6 = re.search(r'Course Contents\s*[:\-]?\s*(.*)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m6:
        # We need to stop the content extraction at the next course title/header which might be present in the text if we concatenated too much
        # However, since we are now building the content block by siblings, simply cleaning the group(1) should work.
        result['contents'] = clean_text(m6.group(1))

    return result

def scrape_courses_from_page(url: str) -> List[Dict[str, Any]]:
    """
    Fetches a page, finds course headings, and collects the heading plus all 
    following sibling content up to the next heading to form a complete course block.
    """
    print(f"Scraping: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(resp.content, 'html.parser')

    courses: List[Dict[str, Any]] = []
    
    # Course titles are typically in <h4> tags. We'll search for <h4> that contain a course code pattern.
    # Note: On this specific site, the content seems to be in the main content area.
    course_headings = soup.find_all(['h4', 'h5', 'h6'])
    
    for i, heading in enumerate(course_headings):
        # Only process headings that look like course titles (e.g., containing 'CSE' and digits)
        if not re.search(r'[A-Z]{3}\d{3}', heading.get_text()):
            continue

        # 1. Initialize the block with the heading itself
        course_block_content = [heading]
        
        # 2. Iterate over the following siblings to collect the rest of the course details
        current_element = heading.next_sibling
        while current_element:
            # Stop when we hit the next course heading (h4/h5/h6)
            if current_element.name in ['h4', 'h5', 'h6'] and re.search(r'[A-Z]{3}\d{3}', current_element.get_text()):
                break
            
            # Add the element if it's a non-empty tag or a non-whitespace string
            if isinstance(current_element, Tag):
                course_block_content.append(current_element)
            elif isinstance(current_element, str) and current_element.strip():
                course_block_content.append(current_element)
            
            current_element = current_element.next_sibling
        
        # 3. Combine the elements into a single BeautifulSoup Tag for parsing
        # We use a dummy div to contain all parts of the course for effective parsing
        if course_block_content:
            combined_block = soup.new_tag("div")
            for element in course_block_content:
                combined_block.append(element)
            
            # 4. Parse the complete block
            parsed_course = parse_course_block(combined_block)
            if parsed_course.get('code'): # Only add if we successfully extracted a course code
                courses.append(parsed_course)

    return courses

def main():
    """Main function to orchestrate the scraping and saving."""
    urls = [
        "https://fse.ewubd.edu/computer-science-engineering/core-courses",
        "https://fse.ewubd.edu/computer-science-engineering/elective-courses"
    ]
    all_data = {}
    
    for url in urls:
        key = 'core_courses' if 'core-courses' in url else 'elective_courses'
        all_data[key] = scrape_courses_from_page(url)
    
    # Save JSON
    output_filename = 'ewu_cse_courses_full_corrected.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    core_count = len(all_data.get('core_courses', []))
    elective_count = len(all_data.get('elective_courses', []))
    print("---")
    print(f"✅ Scraping complete!")
    print(f"Saved {core_count} core courses and {elective_count} elective courses to **{output_filename}**")

if __name__ == '__main__':
    main()