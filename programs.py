"""
EWU CSE Programs Complete Scraper
Extracts ALL data from Undergraduate and Graduate Programs
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


def scrape_undergraduate_programs():
    """Scrape complete undergraduate program details"""
    url = "https://fse.ewubd.edu/computer-science-engineering/undergraduate-programs"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Scraping undergraduate programs: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    text_content = soup.get_text()
    
    data = {
        'url': url,
        'program_name': 'B. Sc. in Computer Science and Engineering',
        'vision': '',
        'mission': [],
        'peo': {},
        'po': {},
        'po_to_peo_mapping': {},
        'knowledge_profile': {},
        'complex_problem_solving': {},
        'complex_activities': {},
        'course_summary': {},
        'course_list': {
            'language_general_education': [],
            'elective_general_education': [],
            'natural_science': [],
            'mathematics_statistics': [],
            'core_cse': [],
            'capstone': [],
            'major_areas': []
        },
        'non_major_electives': [],
        'course_flowchart': {}
    }
    
    # Extract Vision
    vision_match = re.search(r'Vision Statement of CSE Department:\s*(.*?)(?=Mission|$)', text_content, re.DOTALL)
    if vision_match:
        data['vision'] = clean_text(vision_match.group(1))
    
    # Extract Mission (3 points)
    mission_section = re.search(r'Mission of CSE Department:(.*?)(?=Program Educational|$)', text_content, re.DOTALL)
    if mission_section:
        mission_points = re.findall(r'-\s*(To .*?)(?=-\s*To|Program|$)', mission_section.group(1), re.DOTALL)
        data['mission'] = [clean_text(m) for m in mission_points]
    
    # Extract PEO (Program Educational Objectives)
    peo_pattern = r'(PEO\d+)\s*\|\s*(.*?)(?=\||PEO\d+|Program Outcomes|$)'
    peo_matches = re.finditer(peo_pattern, text_content, re.DOTALL)
    for match in peo_matches:
        data['peo'][match.group(1)] = clean_text(match.group(2))
    
    # Extract PO (Program Outcomes) with full descriptions
    po_pattern = r'(PO\d+):\s*([^|]+)\s*\|\s*(.*?)(?=\||PO\d+:|Mapping of Program|$)'
    po_matches = re.finditer(po_pattern, text_content, re.DOTALL)
    for match in po_matches:
        po_code = match.group(1)
        po_title = clean_text(match.group(2))
        po_desc = clean_text(match.group(3))
        data['po'][po_code] = {
            'title': po_title,
            'description': po_desc
        }
    
    # Extract PO to PEO Mapping
    mapping_section = re.search(r'Mapping of Program Outcomes.*?Program Educational Objectives.*?PEO1.*?PEO2.*?PEO3(.*?)(?=Knowledge Profile|$)', text_content, re.DOTALL)
    if mapping_section:
        mapping_text = mapping_section.group(1)
        for i in range(1, 13):
            po_key = f"PO{i}"
            # Look for X markers in the mapping table
            po_line = re.search(rf'PO{i}:.*?\n', mapping_text)
            if po_line:
                line = po_line.group(0)
                data['po_to_peo_mapping'][po_key] = {
                    'PEO1': 'X' in line.split('|')[1] if '|' in line else False,
                    'PEO2': 'X' in line.split('|')[2] if len(line.split('|')) > 2 else False,
                    'PEO3': 'X' in line.split('|')[3] if len(line.split('|')) > 3 else False
                }
    
    # Extract Knowledge Profile (K1-K8)
    knowledge_pattern = r'(K\d+):\s*([^|]+)\s*\|\s*(.*?)(?=\||K\d+:|Range of Complex|$)'
    knowledge_matches = re.finditer(knowledge_pattern, text_content, re.DOTALL)
    for match in knowledge_matches:
        k_code = match.group(1)
        k_title = clean_text(match.group(2))
        k_desc = clean_text(match.group(3))
        data['knowledge_profile'][k_code] = {
            'title': k_title,
            'description': k_desc
        }
    
    # Extract Complex Engineering Problem Solving (EP1-EP7)
    ep_pattern = r'(EP\s*\d+):\s*([^|]+)\s*\|\s*(.*?)(?=\||EP\s*\d+:|Range of Complex Activities|$)'
    ep_matches = re.finditer(ep_pattern, text_content, re.DOTALL)
    for match in ep_matches:
        ep_code = match.group(1).replace(' ', '')
        ep_title = clean_text(match.group(2))
        ep_desc = clean_text(match.group(3))
        data['complex_problem_solving'][ep_code] = {
            'attribute': ep_title,
            'characteristics': ep_desc
        }
    
    # Extract Complex Engineering Activities (EA1-EA5)
    ea_pattern = r'(EA\d+):\s*([^|]+)\s*\|\s*(.*?)(?=\||EA\d+:|Course Summary|$)'
    ea_matches = re.finditer(ea_pattern, text_content, re.DOTALL)
    for match in ea_matches:
        ea_code = match.group(1)
        ea_title = clean_text(match.group(2))
        ea_desc = clean_text(match.group(3))
        data['complex_activities'][ea_code] = {
            'attribute': ea_title,
            'characteristics': ea_desc
        }
    
    # Extract Course Summary
    summary_pattern = r'Course Summary.*?Course Category\s*\|\s*Credits(.*?)(?=List of Courses|$)'
    summary_match = re.search(summary_pattern, text_content, re.DOTALL)
    if summary_match:
        summary_lines = summary_match.group(1).split('\n')
        for line in summary_lines:
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2 and parts[0] and parts[1].isdigit():
                    data['course_summary'][parts[0]] = int(parts[1])
    
    # Extract Course Lists
    # Language and General Education
    lang_section = re.search(r'Compulsory Language and General Education Courses\s*\|\s*9(.*?)(?=Elective General|$)', text_content, re.DOTALL)
    if lang_section:
        courses = re.findall(r'(ENG\d+|GEN\d+)\s+([^|]+)\s*\|\s*(\d+)', lang_section.group(1))
        for course_code, course_name, credits in courses:
            data['course_list']['language_general_education'].append({
                'code': course_code,
                'name': clean_text(course_name),
                'credits': credits
            })
    
    # Natural Science Courses
    science_section = re.search(r'Compulsory Natural Science Courses.*?(\d+\+\d+=\d+)(.*?)(?=Compulsory Mathematics|$)', text_content, re.DOTALL)
    if science_section:
        courses = re.findall(r'(PHY\d+|CHE\d+)\s+([^|]+)\s*\|\s*([\d.+]+)', science_section.group(2))
        for course_code, course_name, credits in courses:
            data['course_list']['natural_science'].append({
                'code': course_code,
                'name': clean_text(course_name),
                'credits': credits
            })
    
    # Mathematics and Statistics
    math_section = re.search(r'Compulsory Mathematics and Statistics Courses.*?15(.*?)(?=Core Computer Science|$)', text_content, re.DOTALL)
    if math_section:
        courses = re.findall(r'(MAT\d+|STA\d+)\s+([^|]+)\s*\|\s*(\d+)', math_section.group(1))
        for course_code, course_name, credits in courses:
            prereq_match = re.search(rf'{course_code}.*?\|\s*(\w+)', text_content)
            prereq = prereq_match.group(1) if prereq_match and prereq_match.group(1) not in [course_code, ''] else None
            data['course_list']['mathematics_statistics'].append({
                'code': course_code,
                'name': clean_text(course_name),
                'credits': credits,
                'prerequisite': prereq
            })
    
    # Core CSE Courses
    core_section = re.search(r'Core Computer Science and Engineering Courses.*?([\d.+]+)(.*?)(?=Core Capstone|$)', text_content, re.DOTALL)
    if core_section:
        courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', core_section.group(2))
        for course_code, course_name, credits, prereq in courses:
            data['course_list']['core_cse'].append({
                'code': course_code,
                'name': clean_text(course_name),
                'credits': credits,
                'prerequisite': clean_text(prereq) if clean_text(prereq) else None
            })
    
    # Capstone Project
    capstone_match = re.search(r'(CSE400)\s+Capstone Project\s*\|\s*([\d.+]+)\s*\|\s*([^\n]+)', text_content)
    if capstone_match:
        data['course_list']['capstone'] = {
            'code': capstone_match.group(1),
            'name': 'Capstone Project',
            'credits': capstone_match.group(2),
            'prerequisite': clean_text(capstone_match.group(3))
        }
    
    # Extract 4 Major Areas with all courses
    major_areas = [
        ('Intelligent Systems and Data Science', 'CSE303|CSE366'),
        ('Software Engineering', 'CSE412|CSE430'),
        ('Communications and Networking', 'CSE350|CSE432'),
        ('Hardware Engineering', 'CSE355|CSE442')
    ]
    
    for major_name, compulsory_pattern in major_areas:
        major_data = {
            'name': major_name,
            'total_credits': '15+5=20',
            'compulsory_courses': [],
            'elective_courses': []
        }
        
        # Find major section
        major_section = re.search(rf'{major_name}.*?(15\+5=20)(.*?)(?=\d+\.|Non-Major|Note:|Course Flowchart|$)', text_content, re.DOTALL)
        if major_section:
            section_text = major_section.group(2)
            
            # Extract compulsory courses
            compulsory = re.search(r'Compulsory Courses.*?(6\+2=8)(.*?)(?=Elective|$)', section_text, re.DOTALL)
            if compulsory:
                courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', compulsory.group(2))
                for code, name, credits, prereq in courses:
                    major_data['compulsory_courses'].append({
                        'code': code,
                        'name': clean_text(name),
                        'credits': credits,
                        'prerequisite': clean_text(prereq) if clean_text(prereq) else None
                    })
            
            # Extract elective courses
            elective = re.search(r'Elective Courses.*?(9\+3=12)(.*?)(?=\d+\.|$)', section_text, re.DOTALL)
            if elective:
                courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', elective.group(2))
                for code, name, credits, prereq in courses:
                    major_data['elective_courses'].append({
                        'code': code,
                        'name': clean_text(name),
                        'credits': credits,
                        'prerequisite': clean_text(prereq) if clean_text(prereq) else None
                    })
        
        data['course_list']['major_areas'].append(major_data)
    
    # Extract Non-Major Area (Computational Theory)
    nonmajor_section = re.search(r'Non-Major Area: Computational Theory(.*?)(?=Note:|Course Flowchart|$)', text_content, re.DOTALL)
    if nonmajor_section:
        courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', nonmajor_section.group(1))
        for code, name, credits, prereq in courses:
            data['non_major_electives'].append({
                'code': code,
                'name': clean_text(name),
                'credits': credits,
                'prerequisite': clean_text(prereq) if clean_text(prereq) else None
            })
    
    return data


def scrape_graduate_programs():
    """Scrape complete graduate program details"""
    url = "https://fse.ewubd.edu/computer-science-engineering/graduate-programs"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Scraping graduate programs: {url}")
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    
    text_content = soup.get_text()
    
    data = {
        'url': url,
        'program_name': 'Master of Science in Computer Science and Engineering',
        'major_areas': [],
        'admission_requirements': [],
        'study_tracks': [],
        'program_length': '',
        'program_cost': {},
        'degree_requirements': {
            'thesis_track': {},
            'project_track': {}
        },
        'compulsory_courses_all_majors': [],
        'major_specific_courses': []
    }
    
    # Extract major areas
    major_areas_section = re.search(r'Major Areas:.*?program is organized into four major areas:(.*?)(?=A student will|$)', text_content, re.DOTALL)
    if major_areas_section:
        areas = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', major_areas_section.group(1))
        data['major_areas'] = [clean_text(area) for area in areas if len(area) > 5]
    
    # Extract admission requirements
    admission_section = re.search(r'Admission Requirements:(.*?)(?=Study Track:|$)', text_content, re.DOTALL)
    if admission_section:
        requirements = re.findall(r'-\s*(.*?)(?=-\s*|Candidates must|Study Track|$)', admission_section.group(1), re.DOTALL)
        data['admission_requirements'] = [clean_text(req) for req in requirements if clean_text(req)]
    
    # Extract study tracks
    if 'Thesis Track' in text_content:
        data['study_tracks'].append('Thesis Track')
    if 'Project Track' in text_content:
        data['study_tracks'].append('Project Track')
    
    # Extract program length
    length_match = re.search(r'Length of the Program:\s*(.*?)(?=MS in CSE Program Cost|$)', text_content, re.DOTALL)
    if length_match:
        data['program_length'] = clean_text(length_match.group(1))
    
    # Extract program cost
    cost_pattern = r'MS in CSE\s*\|\s*([\d.]+)\s*\|\s*([\d,/=]+)\s*\|\s*([\d,/=]+)\s*\|\s*([\d,/=]+)\s*\|\s*([\d,/=]+)\s*\|\s*([\d,/=]+)'
    cost_match = re.search(cost_pattern, text_content)
    if cost_match:
        data['program_cost'] = {
            'total_credit': cost_match.group(1),
            'fee_per_credit': cost_match.group(2),
            'tuition_fees': cost_match.group(3),
            'lab_activities_fees': cost_match.group(4),
            'admission_fee': cost_match.group(5),
            'grand_total': cost_match.group(6)
        }
    
    # Extract degree requirements - Thesis Track
    thesis_section = re.search(r'Thesis Track(.*?)Project Track', text_content, re.DOTALL)
    if thesis_section:
        thesis_text = thesis_section.group(1)
        categories = re.findall(r'([A-Za-z\s]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)', thesis_text)
        for category, num_courses, credits in categories:
            cat_name = clean_text(category)
            if cat_name and len(cat_name) > 5:
                data['degree_requirements']['thesis_track'][cat_name] = {
                    'number_of_courses': num_courses,
                    'credits': credits
                }
    
    # Extract degree requirements - Project Track
    project_section = re.search(r'Project Track(.*?)(?=Course Summary:|$)', text_content, re.DOTALL)
    if project_section:
        project_text = project_section.group(1)
        categories = re.findall(r'([A-Za-z\s]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)', project_text)
        for category, num_courses, credits in categories:
            cat_name = clean_text(category)
            if cat_name and len(cat_name) > 5:
                data['degree_requirements']['project_track'][cat_name] = {
                    'number_of_courses': num_courses,
                    'credits': credits
                }
    
    # Extract Compulsory Courses for all Major Areas
    compulsory_all = re.search(r'Compulsory Courses for all Major Areas.*?Compulsory Courses\s*\|(.*?)(?=1\. Major Area:|$)', text_content, re.DOTALL)
    if compulsory_all:
        # Extract prerequisite course
        prereq_course = re.search(r'(CSE\d+)\s+([^|]+)\s*\|\s*(\d+)\s*\|\s*Pass or Fail', compulsory_all.group(1))
        if prereq_course:
            data['compulsory_courses_all_majors'].append({
                'code': prereq_course.group(1),
                'name': clean_text(prereq_course.group(2)),
                'credits': prereq_course.group(3),
                'type': 'Non-credit Prerequisite',
                'comment': 'Pass or Fail'
            })
        
        # Extract regular compulsory courses
        courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*(\d+)\s*\|\s*(?!Pass or Fail)', compulsory_all.group(1))
        for code, name, credits in courses:
            if code != prereq_course.group(1) if prereq_course else True:
                data['compulsory_courses_all_majors'].append({
                    'code': code,
                    'name': clean_text(name),
                    'credits': credits,
                    'type': 'Compulsory'
                })
    
    # Extract each Major Area with courses
    major_names = ['Data Science', 'Software Engineering', 'Networking', 'Systems Engineering']
    
    for major_name in major_names:
        major_data = {
            'name': major_name,
            'prerequisite_courses': [],
            'compulsory_courses': [],
            'elective_courses': []
        }
        
        # Find major section
        major_section = re.search(rf'\d+\.\s*Major Area:\s*{major_name}(.*?)(?=\d+\.\s*Major Area:|Thesis/Project|$)', text_content, re.DOTALL)
        if major_section:
            section_text = major_section.group(1)
            
            # Extract prerequisite
            prereq = re.search(r'(CSE\d+)\s+([^|]+)\s*\|\s*(\d+)\s*\|\s*Pass or Fail', section_text)
            if prereq:
                major_data['prerequisite_courses'].append({
                    'code': prereq.group(1),
                    'name': clean_text(prereq.group(2)),
                    'credits': prereq.group(3),
                    'comment': 'Pass or Fail'
                })
            
            # Extract compulsory courses
            compulsory = re.search(r'Compulsory Courses(.*?)Elective Courses', section_text, re.DOTALL)
            if compulsory:
                courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*(\d+)\s*\|(?!\s*Pass or Fail)', compulsory.group(1))
                for code, name, credits in courses:
                    major_data['compulsory_courses'].append({
                        'code': code,
                        'name': clean_text(name),
                        'credits': credits
                    })
            
            # Extract elective courses
            elective = re.search(r'Elective Courses(.*?)(?=\d+\.\s*Major Area:|Thesis/Project|$)', section_text, re.DOTALL)
            if elective:
                courses = re.findall(r'(CSE\d+)\s+([^|]+)\s*\|\s*(\d+)', elective.group(1))
                for code, name, credits in courses:
                    major_data['elective_courses'].append({
                        'code': code,
                        'name': clean_text(name),
                        'credits': credits
                    })
        
        data['major_specific_courses'].append(major_data)
    
    # Extract Thesis/Project info
    thesis_project = re.search(r'Thesis/Project.*?(CSE\d+)\s+Master Project\s*\|\s*(\d+).*?(CSE\d+)\s+Master Thesis\s*\|\s*(\d+)', text_content, re.DOTALL)
    if thesis_project:
        data['thesis_project'] = {
            'project': {
                'code': thesis_project.group(1),
                'name': 'Master Project',
                'credits': thesis_project.group(2)
            },
            'thesis': {
                'code': thesis_project.group(3),
                'name': 'Master Thesis',
                'credits': thesis_project.group(4)
            }
        }
    
    return data


def main():
    """Main scraping function"""
    print("="*70)
    print("EWU CSE Programs Complete Scraper")
    print("="*70)
    
    all_data = {
        'scraped_at': datetime.now().isoformat(),
        'undergraduate_program': {},
        'graduate_program': {}
    }
    
    try:
        # Scrape undergraduate
        print("\n[1/2] Scraping Undergraduate Programs...")
        all_data['undergraduate_program'] = scrape_undergraduate_programs()
        print(f"✓ Extracted {len(all_data['undergraduate_program']['course_list']['core_cse'])} core CSE courses")
        print(f"✓ Extracted {len(all_data['undergraduate_program']['course_list']['major_areas'])} major areas")
        
        # Scrape graduate
        print("\n[2/2] Scraping Graduate Programs...")
        all_data['graduate_program'] = scrape_graduate_programs()
        print(f"✓ Extracted {len(all_data['graduate_program']['major_specific_courses'])} major areas")
        
        # Save to JSON
        filename = 'ewu_cse_programs_complete.json'
        print(f"\n{'='*70}")
        print(f"Saving to {filename}...")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully saved!")
        print(f"{'='*70}")
        print("\nData Summary:")
        print(f"\nUNDERGRADUATE PROGRAM:")
        print(f"  • Vision: {'✓' if all_data['undergraduate_program']['vision'] else '✗'}")
        print(f"  • Mission Points: {len(all_data['undergraduate_program']['mission'])}")
        print(f"  • PEO Objectives: {len(all_data['undergraduate_program']['peo'])}")
        print(f"  • PO Outcomes: {len(all_data['undergraduate_program']['po'])}")
        print(f"  • Knowledge Profile (K1-K8): {len(all_data['undergraduate_program']['knowledge_profile'])}")
        print(f"  • Complex Problem Solving (EP1-EP7): {len(all_data['undergraduate_program']['complex_problem_solving'])}")
        print(f"  • Complex Activities (EA1-EA5): {len(all_data['undergraduate_program']['complex_activities'])}")
        print(f"  • Core CSE Courses: {len(all_data['undergraduate_program']['course_list']['core_cse'])}")
        print(f"  • Major Areas: {len(all_data['undergraduate_program']['course_list']['major_areas'])}")
        print(f"  • Non-Major Electives: {len(all_data['undergraduate_program']['non_major_electives'])}")
        
        print(f"\nGRADUATE PROGRAM:")
        print(f"  • Program Name: {all_data['graduate_program']['program_name']}")
        print(f"  • Major Areas: {len(all_data['graduate_program']['major_areas'])}")
        print(f"  • Study Tracks: {len(all_data['graduate_program']['study_tracks'])}")
        print(f"  • Admission Requirements: {len(all_data['graduate_program']['admission_requirements'])}")
        print(f"  • Compulsory Courses (All Majors): {len(all_data['graduate_program']['compulsory_courses_all_majors'])}")
        print(f"  • Major Specific Course Sets: {len(all_data['graduate_program']['major_specific_courses'])}")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()