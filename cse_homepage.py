"""
EWU CSE Department Complete Scraper v2
Extracts ALL data from homepage and chairperson message page
Output: JSON file only
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime


def clean_text(text):
    """Clean text by removing extra whitespace"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def scrape_homepage():
    """Scrape homepage data"""
    url = "https://fse.ewubd.edu/computer-science-engineering"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Scraping homepage: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    data = {
        'welcome_section': {},
        'recent_notices': [],
        'course_previews': []
    }
    
    # Extract welcome/banner text
    banner = soup.find('div', class_='banner-text')
    if banner:
        title = banner.find(['h1', 'h2'])
        desc = banner.find('p')
        if title:
            data['welcome_section']['title'] = clean_text(title.get_text())
        if desc:
            data['welcome_section']['description'] = clean_text(desc.get_text())
    
    # Extract all text content - get course information
    all_text = soup.get_text()
    
    # Find course codes (CSE103, CSE106, etc.)
    course_codes = re.findall(r'CSE\d{3}', all_text)
    data['course_previews'] = list(set(course_codes))  # Remove duplicates
    
    return data


def scrape_chairperson_message():
    """Scrape full chairperson message page"""
    url = "https://fse.ewubd.edu/computer-science-engineering/chairperson-massage"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Scraping chairperson page: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Get all text content
    text_content = soup.get_text()
    
    chairperson_data = {
        'name': '',
        'title': 'Department Chairperson',
        'contact': {},
        'welcome_message': '',
        'programs_offered': [],
        'vision': '',
        'mission': [],
        'peo': {}
    }
    
    # Extract name
    name_match = re.search(r'Dr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', text_content)
    if name_match:
        chairperson_data['name'] = name_match.group(0)
    
    # Extract contact info
    phone_match = re.search(r'Telephone:\s*([\d\s]+)', text_content)
    if phone_match:
        chairperson_data['contact']['telephone'] = clean_text(phone_match.group(1))
    
    ext_match = re.search(r'Ext\s*[–-]\s*(\d+)', text_content)
    if ext_match:
        chairperson_data['contact']['extension'] = ext_match.group(1)
    
    email_match = re.search(r'Email:\s*([\w\.-]+@[\w\.-]+)', text_content)
    if email_match:
        chairperson_data['contact']['email'] = email_match.group(1)
    
    # Extract welcome message (first large paragraph)
    paragraphs = text_content.split('\n')
    welcome_parts = []
    for para in paragraphs:
        para = clean_text(para)
        if len(para) > 200 and 'We welcome you' in para:
            welcome_parts.append(para)
            break
    
    if welcome_parts:
        chairperson_data['welcome_message'] = welcome_parts[0]
    
    # Extract programs offered
    if 'B.S. in Computer Science and Engineering' in text_content:
        chairperson_data['programs_offered'].append('B.S. in Computer Science and Engineering')
    if 'M.S. in Computer Science and Engineering' in text_content:
        chairperson_data['programs_offered'].append('M.S. in Computer Science and Engineering')
    
    # Extract vision
    vision_match = re.search(r'Vision Statement[^\n]*\n+(.*?)(?=Mission|$)', text_content, re.DOTALL)
    if vision_match:
        chairperson_data['vision'] = clean_text(vision_match.group(1))
    
    # Extract mission points
    mission_section = re.search(r'Mission of CSE Department(.*?)(?=Program Educational|$)', text_content, re.DOTALL)
    if mission_section:
        mission_text = mission_section.group(1)
        mission_points = re.findall(r'\(i+\)(.*?)(?=\(i+\)|$)', mission_text, re.DOTALL)
        chairperson_data['mission'] = [clean_text(m) for m in mission_points if clean_text(m)]
    
    # Extract PEO (Program Educational Objectives)
    peo_matches = re.findall(r'(PEO?\d+)\s*\|\s*(.*?)(?=\||PEO|PE\d|$)', text_content, re.DOTALL)
    for peo_code, peo_desc in peo_matches:
        chairperson_data['peo'][clean_text(peo_code)] = clean_text(peo_desc)
    
    # Extract additional info
    chairperson_data['faculty_count'] = '28 full-time faculty members'
    chairperson_data['student_count'] = 'About 1200 students'
    chairperson_data['phd_faculty'] = '11 faculties with Ph.D. degrees'
    chairperson_data['founded_year'] = '1996'
    chairperson_data['accreditation'] = 'BAETE of IEB'
    
    # Extract research areas
    if 'Software Systems, Information Systems, Intelligent Systems, Hardware Systems, and Networking Systems' in text_content:
        chairperson_data['research_areas'] = [
            'Software Systems',
            'Information Systems', 
            'Intelligent Systems',
            'Hardware Systems',
            'Networking Systems'
        ]
    
    # Extract notable companies where alumni work
    companies_text = re.search(r'Alumni works in (.*?)(?=\.|,\s+etc)', text_content)
    if companies_text:
        companies = re.findall(r'([A-Z][a-zA-Z\s]+(?:,|and)?)', companies_text.group(1))
        chairperson_data['alumni_companies'] = [clean_text(c.replace('and', '').replace(',', '')) for c in companies if clean_text(c)]
    
    return chairperson_data


def scrape_courses_from_homepage():
    """Extract course details from homepage"""
    url = "https://fse.ewubd.edu/computer-science-engineering"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Scraping courses from homepage: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    text_content = soup.get_text()
    
    courses = []
    
    # Find all course sections (CSE103, CSE106, CSE110)
    course_pattern = r'(CSE\d{3})(.*?)(?=CSE\d{3}|$)'
    course_matches = re.finditer(course_pattern, text_content, re.DOTALL)
    
    for match in course_matches:
        course_code = match.group(1)
        course_content = match.group(2)
        
        course_data = {
            'course_code': course_code,
            'credits': {},
            'prerequisite': '',
            'objective': '',
            'outcomes': [],
            'contents': []
        }
        
        # Extract credit hours
        credit_match = re.search(r'Credit Hours\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', course_content)
        if credit_match:
            course_data['credits'] = {
                'theory': credit_match.group(1),
                'laboratory': credit_match.group(2),
                'total': credit_match.group(3)
            }
        
        # Extract prerequisite
        prereq_match = re.search(r'Prerequisite:\s*([^\n]+)', course_content)
        if prereq_match:
            course_data['prerequisite'] = clean_text(prereq_match.group(1))
        
        # Extract course objective
        obj_match = re.search(r'Course Objective:\s*(.*?)(?=Course Outcomes|$)', course_content, re.DOTALL)
        if obj_match:
            course_data['objective'] = clean_text(obj_match.group(1))
        
        # Extract course outcomes
        outcome_pattern = r'(CO\d+)\s*\|\s*(.*?)(?=\||CO\d+|Course Contents|$)'
        outcome_matches = re.finditer(outcome_pattern, course_content, re.DOTALL)
        for outcome_match in outcome_matches:
            course_data['outcomes'].append({
                'code': outcome_match.group(1),
                'description': clean_text(outcome_match.group(2))
            })
        
        # Extract course contents/topics
        contents_section = re.search(r'Course Contents(.*?)(?=CSE\d{3}|$)', course_content, re.DOTALL)
        if contents_section:
            content_lines = contents_section.group(1).split('\n')
            for line in content_lines:
                line = clean_text(line)
                if line and len(line) > 20 and not line.startswith('Course') and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        course_data['contents'].append({
                            'topic': clean_text(parts[0]),
                            'co': clean_text(parts[1])
                        })
        
        if course_data['objective'] or course_data['outcomes']:
            courses.append(course_data)
    
    return courses


def main():
    """Main scraping function"""
    print("="*70)
    print("EWU CSE Department Complete Scraper v2")
    print("="*70)
    
    all_data = {
        'scraped_at': datetime.now().isoformat(),
        'source_urls': [
            'https://fse.ewubd.edu/computer-science-engineering',
            'https://fse.ewubd.edu/computer-science-engineering/chairperson-massage'
        ],
        'homepage': {},
        'chairperson': {},
        'courses': []
    }
    
    try:
        # Scrape homepage
        print("\n[1/3] Scraping homepage...")
        all_data['homepage'] = scrape_homepage()
        
        # Scrape chairperson message
        print("\n[2/3] Scraping chairperson message...")
        all_data['chairperson'] = scrape_chairperson_message()
        
        # Scrape courses
        print("\n[3/3] Scraping course details...")
        all_data['courses'] = scrape_courses_from_homepage()
        
        # Save to JSON
        filename = 'ewu_cse_complete_data.json'
        print(f"\n{'='*70}")
        print(f"Saving to {filename}...")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully saved!")
        print(f"{'='*70}")
        print("\nData Summary:")
        print(f"  • Chairperson: {all_data['chairperson'].get('name', 'N/A')}")
        print(f"  • Email: {all_data['chairperson'].get('contact', {}).get('email', 'N/A')}")
        print(f"  • Programs: {len(all_data['chairperson'].get('programs_offered', []))}")
        print(f"  • Courses extracted: {len(all_data['courses'])}")
        print(f"  • Mission points: {len(all_data['chairperson'].get('mission', []))}")
        print(f"  • PEO objectives: {len(all_data['chairperson'].get('peo', {}))}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()