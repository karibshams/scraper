import requests
from bs4 import BeautifulSoup
import json
import re
from typing import List, Dict, Any

def clean_text(text: str) -> str:
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
            result['title'] = clean_text(header_text)
    # Find credit/teaching scheme section
    scheme_text = block.get_text(separator="|", strip=True)
    # Try to extract "Credit Hours and Teaching Scheme:" section
    m2 = re.search(r'Credit Hours.*?Theory.*?Laboratory.*?Total', scheme_text, re.IGNORECASE | re.DOTALL)
    if m2:
        result['teaching_scheme'] = clean_text(m2.group(0))
    # Prerequisite
    m3 = re.search(r'Prerequisite\s*[:\-]?\s*(.*?)(?:\s{2,}|Course Objective|$)', scheme_text, re.IGNORECASE)
    if m3:
        result['prerequisite'] = clean_text(m3.group(1))
    # Objective
    m4 = re.search(r'Course Objective\s*[:\-]?\s*(.*?)Course Outcomes', scheme_text, re.IGNORECASE | re.DOTALL)
    if m4:
        result['objective'] = clean_text(m4.group(1))
    # Outcomes: after "Course Outcomes (COs):" until maybe "Course Contents"
    m5 = re.search(r'Course Outcomes\s*[(]COs[)]\s*:(.*?)(?:Course Contents|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m5:
        # split by CO1, CO2 etc.
        outcomes_text = m5.group(1)
        outcomes = re.findall(r'(CO\d+)\s+(.*?)((?=CO\d+)|$)', outcomes_text)
        for oc in outcomes:
            result['outcomes'].append({'code': oc[0].strip(), 'description': clean_text(oc[1])})
    # Contents
    m6 = re.search(r'Course Contents\s*[:\-]?\s*(.*?)((?=####)|$)', scheme_text, re.IGNORECASE | re.DOTALL)
    if m6:
        result['contents'] = clean_text(m6.group(1))

    return result

def scrape_courses_from_page(url: str) -> List[Dict[str, Any]]:
    print(f"Scraping: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')

    # Find each course block: They appear under headings (####) then course details.
    # We'll find all headings of courses and then their following siblings until the next heading.
    courses: List[Dict[str, Any]] = []
    # Example the page uses <h4> or <h5> for each course title. Let's search for <strong> inside anchor maybe
    for anchor in soup.select('a[href]'):
        # Many links: but the course blocks start with [link] CSExxx
        href = anchor.get('href')
        if href and re.search(r'CSE\d{3}', anchor.text):
            # find the parent block
            block = anchor.parent
            # collect siblings until next course heading
            course_block = block
            courses.append(parse_course_block(course_block))

    return courses

def main():
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
    with open('ewu_cse_courses_full.json', 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_data['core_courses'])} core courses and {len(all_data['elective_courses'])} elective courses")

if __name__ == '__main__':
    main()
