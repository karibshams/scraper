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
    
    # 1. Get the combined text from the block using a pipe separator
    if isinstance(block, Tag):
        # Using '\n' as a separator might be better for this nested structure to preserve line breaks
        scheme_text = block.get_text(separator="\n", strip=True) 
    else:
        scheme_text = block

    # 2. Extract Code and Title (usually at the beginning)
    # The title text is the very first line of the block.
    first_line = scheme_text.split('\n')[0]
    
    # Example: "CSE479 Web Programming" or "CSE402 Computer and Cyber Security"
    header_match = re.match(r'([A-Z]{3}\d+)\s*(.*)', first_line, re.IGNORECASE)
    if header_match:
        result['code'] = header_match.group(1).strip()
        result['title'] = clean_text(header_match.group(2).strip())
    else:
        # Fallback for title if no code is found in the first line
        result['title'] = clean_text(first_line)

    # Convert all newlines to spaces for robust regex searching across sections
    search_text = scheme_text.replace('\n', ' ')

    # 3. Credit Hours / Teaching Scheme
    # Capture everything from "Credit Hours and Teaching Scheme:" up to "Prerequisite"
    m2 = re.search(r'Credit Hours and Teaching Scheme\s*:\s*(.*?)Prerequisite', search_text, re.IGNORECASE | re.DOTALL)
    if m2:
        scheme_raw = clean_text(m2.group(1))
        result['teaching_scheme'] = scheme_raw
        
        # Try to extract credit hours (e.g., 3, 4, etc.)
        credit_match = re.search(r'Credit hours\s*(\d+)', scheme_raw, re.IGNORECASE)
        if credit_match:
             result['credit_hours'] = credit_match.group(1).strip()

    # 4. Prerequisite
    # Capture until "Course Objective"
    m3 = re.search(r'Prerequisite\s*[:\-]?\s*(.*?)(?:Course Objective|$)', search_text, re.IGNORECASE | re.DOTALL)
    if m3:
        result['prerequisite'] = clean_text(m3.group(1))
    
    # 5. Objective
    # Capture until "Course Outcomes"
    m4 = re.search(r'Course Objective\s*[:\-]?\s*(.*?)Course Outcomes', search_text, re.IGNORECASE | re.DOTALL)
    if m4:
        result['objective'] = clean_text(m4.group(1))
    
    # 6. Outcomes
    # after "Course Outcomes (COs):" until "Course Contents"
    m5 = re.search(r'Course Outcomes\s*[(]COs[)]\s*:(.*?)(?:Course Contents|$)', search_text, re.IGNORECASE | re.DOTALL)
    if m5:
        outcomes_text = m5.group(1)
        # Find all CO# followed by the description until the next CO# or end of string
        # We look for (CO#) followed by any text, captured lazily.
        outcomes = re.findall(r'(CO\d+)\s+(.*?)(?=(CO\d+)|$)', outcomes_text, re.DOTALL)
        for oc in outcomes:
            # oc[0] is the code (e.g., CO1), oc[1] is the description
            result['outcomes'].append({'code': oc[0].strip(), 'description': clean_text(oc[1])})
    
    # 7. Contents
    # Capture from "Course Contents" until the end of the block
    m6 = re.search(r'Course Contents\s*[:\-]?\s*(.*)', search_text, re.IGNORECASE | re.DOTALL)
    if m6:
        result['contents'] = clean_text(m6.group(1))

    return result

def scrape_courses_from_page(url: str) -> List[Dict[str, Any]]:
    """
    Fetches a page and targets the main course container elements.
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
    
    # Based on the screenshot, the courses seem to be in distinct DIV elements, 
    # likely identified by a class or structure like 'CSExxx: Title' immediately inside.
    
    # We will search for all elements that contain a course code pattern in their text, 
    # and use a parent element as the course block.
    
    # Find all elements that contain text matching the course code pattern
    # The structure looks like a list of courses, where the main content is nested.
    
    # Searching for the most robust container element that holds the entire course info.
    # Looking at the HTML structure of the page, the courses are often wrapped in a <div> 
    # that starts with the course title.
    
    # Let's try to find the clickable headers first, then get their parent containers.
    course_headers = soup.find_all('div', class_=re.compile(r'course-title|course-header|acordian-item', re.I))
    
    if not course_headers:
        # Fallback: Look for any element whose text starts with a course code, and take its main parent.
        # This is less reliable but necessary if the class names change.
        course_containers = soup.find_all(lambda tag: tag.name in ['div', 'li'] and re.match(r'[A-Z]{3}\d{3}', tag.get_text(strip=True)))
    else:
        # Use the found headers' parents or the headers themselves as the block
        course_containers = [h.parent for h in course_headers] # Often the parent div is the full block
        # If the parent is the main container, use it.

    # Filter for unique containers and ensure they contain course code
    unique_containers = []
    seen_text = set()
    for container in course_containers:
        # Check if the container has enough text to be a full course block
        container_text = container.get_text(strip=True)
        if len(container_text) > 100 and container_text not in seen_text and re.search(r'[A-Z]{3}\d{3}', container_text):
            unique_containers.append(container)
            seen_text.add(container_text)

    if not unique_containers:
        print("Warning: Could not reliably find course container elements. Trying a broader search...")
        # Fallback to the broadest possible container that might hold course data
        main_content_div = soup.find('div', class_='col-sm-8') # Targeting the main content column
        if main_content_div:
            # We'll treat the entire block of content as a list of courses and try to split them
            full_text = main_content_div.get_text(separator="\n", strip=True)
            # Split the text by the course code pattern to get individual blocks
            course_blocks_raw = re.split(r'([A-Z]{3}\d{3}\s+.*?)', full_text)
            
            # The list will contain empty strings, the course header, and the content.
            for i in range(1, len(course_blocks_raw), 2):
                header = course_blocks_raw[i]
                content = course_blocks_raw[i+1] if (i+1) < len(course_blocks_raw) else ""
                
                # Combine header and content for parsing
                full_course_text = header + "\n" + content
                parsed_course = parse_course_block(full_course_text)
                if parsed_course.get('code'):
                    courses.append(parsed_course)
            return courses


    for container in unique_containers:
        parsed_course = parse_course_block(container)
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
    output_filename = 'ewu_cse_courses_full_corrected_v2.json'
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    core_count = len(all_data.get('core_courses', []))
    elective_count = len(all_data.get('elective_courses', []))
    print("---")
    print(f"✅ Scraping complete!")
    print(f"Saved {core_count} core courses and {elective_count} elective courses to **{output_filename}**")

if __name__ == '__main__':
    main()