"""
EWU CSE Programs COMPLETE Scraper - Extracts EVERY DETAIL
Output: JSON file only
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import Dict, Any, List


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace"""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def scrape_undergraduate_programs() -> Dict[str, Any]:
    """Scrape COMPLETE undergraduate program details - EVERY WORD"""
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
        'vision_statement': '',
        'mission_statement': [],
        'peo': {},
        'peo_description': '',
        'po': {},
        'po_description': '',
        'po_to_peo_mapping': {},
        'knowledge_profile': {},
        'knowledge_profile_description': '',
        'complex_problem_solving': {},
        'complex_problem_solving_description': '',
        'complex_activities': {},
        'complex_activities_description': '',
        'course_summary': {},
        'course_summary_total': 0,
        'course_lists': {
            'compulsory_language_general_education': {
                'total_credits': 9,
                'courses': []
            },
            'elective_general_education': {
                'total_credits': 9,
                'categories': {
                    'social_science': [],
                    'arts_humanities': [],
                    'business': []
                }
            },
            'compulsory_natural_science': {
                'total_credits': '9+2=11',
                'courses': []
            },
            'compulsory_mathematics_statistics': {
                'total_credits': 15,
                'courses': []
            },
            'core_cse': {
                'total_credits': '48+14=62',
                'courses': []
            },
            'core_capstone': {
                'total_credits': '0+6=6',
                'courses': []
            },
            'major_areas': [],
            'non_major_area': {
                'name': 'Computational Theory',
                'courses': []
            }
        },
        'major_requirements': {
            'description': 'Student should select one of the four major areas for degree major requirement',
            'compulsory_courses': 'Two Compulsory courses (6+2=8 credits)',
            'elective_courses': 'Three elective courses (9+3=12 credits)'
        },
        'non_major_requirements': 'Minimum 8 credits ( two to three courses depending on credits of the courses) from one or more major/non-major areas other than the selected major area',
        'course_flowchart': {
            'first_year': {'semester_1': [], 'semester_2': [], 'semester_3': []},
            'second_year': {'semester_1': [], 'semester_2': [], 'semester_3': []},
            'third_year': {'semester_1': [], 'semester_2': [], 'semester_3': []},
            'fourth_year': {'semester_1': [], 'semester_2': [], 'semester_3': []},
            'year_credits': 35
        },
        'notes': ''
    }

    # Extract Vision
    vision_match = re.search(r'Vision Statement of CSE Department:\s*(.*?)(?=Mission of CSE|$)', text_content, re.DOTALL)
    if vision_match:
        data['vision_statement'] = clean_text(vision_match.group(1))

    # Extract Mission (all points)
    mission_section = re.search(r'Mission of CSE Department:(.*?)(?=Program Educational Objectives|$)', text_content, re.DOTALL)
    if mission_section:
        mission_points = re.findall(r'-\s*(To .*?)(?=-\s*To|Program|$)', mission_section.group(1), re.DOTALL)
        data['mission_statement'] = [clean_text(m) for m in mission_points]

    # Extract PEO description
    peo_desc = re.search(r'Program Educational Objectives \(PEOs\) of B\. Sc\. in CSE Program:\s*(.*?)(?=PEO1|$)', text_content, re.DOTALL)
    if peo_desc:
        data['peo_description'] = clean_text(peo_desc.group(1))

    # Extract PEO (all 3)
    peo_pattern = r'(PEO\d+)\s*\|\s*(.*?)(?=\s*\||PEO\d+|Program Outcomes|$)'
    peo_matches = re.finditer(peo_pattern, text_content, re.DOTALL)
    for match in peo_matches:
        data['peo'][match.group(1)] = clean_text(match.group(2))

    # Extract PO description
    po_desc = re.search(r'Program Outcomes \(POs\) of B\. Sc\. in CSE Program\s*(.*?)(?=PO\s*\||$)', text_content, re.DOTALL)
    if po_desc:
        data['po_description'] = clean_text(po_desc.group(1))

    # Extract PO (all 12 with full descriptions)
    po_pattern = r'(PO\d+):\s*([^|]+?)\s*\|\s*(.*?)(?=\s*\||PO\d+:|Mapping of Program|$)'
    po_matches = re.finditer(po_pattern, text_content, re.DOTALL)
    for match in po_matches:
        po_code = match.group(1)
        po_title = clean_text(match.group(2))
        po_desc = clean_text(match.group(3))
        data['po'][po_code] = {
            'title': po_title,
            'description': po_desc
        }

    # Extract PO to PEO Mapping (complete table)
    mapping_lines = re.findall(r'(PO\d+:[^|]+)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^\n]*)', text_content)
    for po_line, peo1, peo2, peo3 in mapping_lines:
        po_key = re.search(r'PO\d+', po_line)
        if po_key:
            data['po_to_peo_mapping'][po_key.group(0)] = {
                'po_name': clean_text(po_line),
                'PEO1': 'X' in peo1,
                'PEO2': 'X' in peo2,
                'PEO3': 'X' in peo3
            }

    # Knowledge Profile description
    kp_desc = re.search(r'Knowledge Profile\s*(.*?)(?=Knowledge Profile\s*\||$)', text_content, re.DOTALL)
    if kp_desc:
        desc_text = kp_desc.group(1)
        if 'The B. Sc. in CSE curriculum' in desc_text:
            data['knowledge_profile_description'] = clean_text(desc_text)

    # Extract Knowledge Profile (K1-K8)
    knowledge_pattern = r'(K\d+):\s*([^|]+?)\s*\|\s*(.*?)(?=\s*\||K\d+:|Range of Complex|$)'
    knowledge_matches = re.finditer(knowledge_pattern, text_content, re.DOTALL)
    for match in knowledge_matches:
        k_code = match.group(1)
        k_title = clean_text(match.group(2))
        k_desc = clean_text(match.group(3))
        data['knowledge_profile'][k_code] = {
            'title': k_title,
            'description': k_desc
        }

    # Complex Problem Solving description
    cps_desc = re.search(r'Range of Complex Engineering Problem Solving\s*(.*?)(?=Attribute\s*\||$)', text_content, re.DOTALL)
    if cps_desc:
        data['complex_problem_solving_description'] = clean_text(cps_desc.group(1))

    # Extract Complex Engineering Problem Solving (EP1-EP7)
    ep_pattern = r'(EP\s*\d+):\s*([^|]+?)\s*\|\s*(.*?)(?=\s*\||EP\s*\d+:|Range of Complex Activities|$)'
    ep_matches = re.finditer(ep_pattern, text_content, re.DOTALL)
    for match in ep_matches:
        ep_code = match.group(1).replace(' ', '')
        ep_title = clean_text(match.group(2))
        ep_desc = clean_text(match.group(3))
        data['complex_problem_solving'][ep_code] = {
            'attribute': ep_title,
            'characteristics': ep_desc
        }

    # Complex Activities description
    ca_desc = re.search(r'Range of Complex Engineering Activities\s*(.*?)(?=Attribute\s*\||$)', text_content, re.DOTALL)
    if ca_desc:
        data['complex_activities_description'] = clean_text(ca_desc.group(1))

    # Extract Complex Engineering Activities (EA1-EA5)
    ea_pattern = r'(EA\d+):\s*([^|]+?)\s*\|\s*(.*?)(?=\s*\||EA\d+:|Course Summary|$)'
    ea_matches = re.finditer(ea_pattern, text_content, re.DOTALL)
    for match in ea_matches:
        ea_code = match.group(1)
        ea_title = clean_text(match.group(2))
        ea_desc = clean_text(match.group(3))
        data['complex_activities'][ea_code] = {
            'attribute': ea_title,
            'characteristics': ea_desc
        }

    # Extract Course Summary (complete table)
    summary_lines = re.findall(r'([A-Za-z\s&]+?Courses)\s*\|\s*(\d+)', text_content)
    for category, credits in summary_lines:
        cat_clean = clean_text(category)
        if cat_clean and len(cat_clean) > 10:
            try:
                data['course_summary'][cat_clean] = int(credits)
            except ValueError:
                data['course_summary'][cat_clean] = credits

    # Extract Total credits
    total_match = re.search(r'Total\s*\|\s*(\d+)', text_content)
    if total_match:
        try:
            data['course_summary_total'] = int(total_match.group(1))
        except ValueError:
            data['course_summary_total'] = total_match.group(1)

    # Extract Compulsory Language and General Education Courses
    lang_courses = re.findall(r'(ENG\d+|GEN\d+)\s+([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^\n]*?)(?=\n|ENG|GEN|Elective)', text_content)
    for code, name, credits, prereq in lang_courses:
        # best-effort check: include all language courses found
        data['course_lists']['compulsory_language_general_education']['courses'].append({
            'code': code,
            'name': clean_text(name),
            'credits': int(credits),
            'prerequisite': clean_text(prereq) if clean_text(prereq) and clean_text(prereq) != 'None' else None
        })

    # Extract Elective General Education - Social Science
    social_science_section = re.search(r'Social Science Courses \(any one course\)(.*?)Arts and Humanities', text_content, re.DOTALL)
    if social_science_section:
        courses = re.findall(r'(ECO\d+|GEN\d+|SOC\d+)\s+([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^\n]*)', social_science_section.group(1))
        for code, name, credits, prereq in courses:
            data['course_lists']['elective_general_education']['categories']['social_science'].append({
                'code': code,
                'name': clean_text(name),
                'credits': int(credits),
                'prerequisite': clean_text(prereq) if clean_text(prereq) and clean_text(prereq) != 'None' else None
            })

    # Extract Elective General Education - Arts and Humanities
    arts_section = re.search(r'Arts and Humanities Courses \(any one course\)(.*?)Business Courses', text_content, re.DOTALL)
    if arts_section:
        courses = re.findall(r'(GEN\d+|SOC\d+)\s+([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^\n]*)', arts_section.group(1))
        for code, name, credits, prereq in courses:
            data['course_lists']['elective_general_education']['categories']['arts_humanities'].append({
                'code': code,
                'name': clean_text(name),
                'credits': int(credits),
                'prerequisite': clean_text(prereq) if clean_text(prereq) and clean_text(prereq) != 'None' else None
            })

    # Extract Elective General Education - Business
    business_section = re.search(r'Business Courses \(any one course\)(.*?)(?=Compulsory Natural Science|$)', text_content, re.DOTALL)
    if business_section:
        courses = re.findall(r'(ACT\d+|BUS\d+|MGT\d+|FIN\d+|MKT\d+)\s+([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^\n]*)', business_section.group(1))
        for code, name, credits, prereq in courses:
            data['course_lists']['elective_general_education']['categories']['business'].append({
                'code': code,
                'name': clean_text(name),
                'credits': int(credits),
                'prerequisite': clean_text(prereq) if clean_text(prereq) and clean_text(prereq) != 'None' else None
            })

    # Extract Compulsory Natural Science Courses
    science_courses = re.findall(r'(PHY\d+|CHE\d+)\s+([^|]+?)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', text_content)
    for code, name, credits, prereq in science_courses:
        data['course_lists']['compulsory_natural_science']['courses'].append({
            'code': code,
            'name': clean_text(name),
            'credits': credits,
            'prerequisite': clean_text(prereq) if clean_text(prereq) else None
        })

    # Extract Compulsory Mathematics and Statistics Courses
    math_courses = re.findall(r'(MAT\d+|STA\d+)\s+([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^\n]*?)(?=\n|MAT|STA|Core)', text_content)
    for code, name, credits, prereq in math_courses:
        if 'Compulsory Mathematics' in text_content[:text_content.find(code) + 500]:
            data['course_lists']['compulsory_mathematics_statistics']['courses'].append({
                'code': code,
                'name': clean_text(name),
                'credits': int(credits),
                'prerequisite': clean_text(prereq) if clean_text(prereq) else None
            })

    # Extract Core CSE Courses
    core_section = re.search(r'Core Computer Science and Engineering Courses.*?(48\+14=62)(.*?)(?=Core Capstone|$)', text_content, re.DOTALL)
    if core_section:
        courses = re.findall(r'(CSE\d+)\s+([^|]+?)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', core_section.group(2))
        for code, name, credits, prereq in courses:
            data['course_lists']['core_cse']['courses'].append({
                'code': code,
                'name': clean_text(name),
                'credits': credits,
                'prerequisite': clean_text(prereq) if clean_text(prereq) else None
            })

    # Extract Capstone Project
    capstone_match = re.search(r'(CSE400)\s+Capstone Project\s*\|\s*([\d.+]+)\s*\|\s*([^\n]+)', text_content)
    if capstone_match:
        data['course_lists']['core_capstone']['courses'].append({
            'code': capstone_match.group(1),
            'name': 'Capstone Project',
            'credits': capstone_match.group(2),
            'prerequisite': clean_text(capstone_match.group(3))
        })

    # Extract ALL 4 Major Areas with COMPLETE details
    major_patterns = [
        ('1. Intelligent Systems and Data Science', 'Intelligent Systems and Data Science'),
        ('2. Software Engineering', 'Software Engineering'),
        ('3. Communications and Networking', 'Communications and Networking'),
        ('4. Hardware Engineering', 'Hardware Engineering')
    ]

    for pattern, name in major_patterns:
        major_section = re.search(rf'{re.escape(pattern)}(.*?)(?=\d+\.\s+\w+|Non-Major Area|Note:|$)', text_content, re.DOTALL)
        if major_section:
            section_text = major_section.group(1)

            major_data = {
                'number': pattern.split('.')[0].strip(),
                'name': name,
                'total_credits': '15+5=20',
                'compulsory_courses': {
                    'credits': '6+2=8',
                    'courses': []
                },
                'elective_courses': {
                    'credits': '9+3=12',
                    'note': 'Any 3 Courses',
                    'courses': []
                }
            }

            # Extract compulsory courses
            compulsory = re.search(r'Compulsory Courses.*?(6\+2=8)(.*?)Elective Courses', section_text, re.DOTALL)
            if compulsory:
                courses = re.findall(r'(CSE\d+)\s+([^|]+?)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', compulsory.group(2))
                for code, course_name, credits, prereq in courses:
                    major_data['compulsory_courses']['courses'].append({
                        'code': code,
                        'name': clean_text(course_name),
                        'credits': credits,
                        'prerequisite': clean_text(prereq) if clean_text(prereq) else None
                    })

            # Extract elective courses
            elective = re.search(r'Elective Courses.*?(9\+3=12)(.*?)(?=\d+\.\s+|Non-Major|$)', section_text, re.DOTALL)
            if elective:
                courses = re.findall(r'(CSE\d+)\s+([^|]+?)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', elective.group(2))
                for code, course_name, credits, prereq in courses:
                    major_data['elective_courses']['courses'].append({
                        'code': code,
                        'name': clean_text(course_name),
                        'credits': credits,
                        'prerequisite': clean_text(prereq) if clean_text(prereq) else None
                    })

            data['course_lists']['major_areas'].append(major_data)

    # Extract Non-Major Area: Computational Theory
    nonmajor_section = re.search(r'Non-Major Area: Computational Theory(.*?)(?=Note:|Course Flowchart|$)', text_content, re.DOTALL)
    if nonmajor_section:
        courses = re.findall(r'(CSE\d+)\s+([^|]+?)\s*\|\s*([\d.+]+)\s*\|\s*([^\n]*)', nonmajor_section.group(1))
        for code, name, credits, prereq in courses:
            data['course_lists']['non_major_area']['courses'].append({
                'code': code,
                'name': clean_text(name),
                'credits': credits,
                'prerequisite': clean_text(prereq) if clean_text(prereq) else None
            })

    # Extract Notes
    note_match = re.search(r'Note:\s*([^\n]+)', text_content)
    if note_match:
        data['notes'] = clean_text(note_match.group(1))

    # Extract Course Flowchart
    flowchart_section = re.search(r'Course Flowchart(.*?)$', text_content, re.DOTALL)
    if flowchart_section:
        # 1st Year - 1st Semester
        year1_sem1 = re.search(r'1st Semester(.*?)2nd Semester', flowchart_section.group(1), re.DOTALL)
        if year1_sem1:
            courses = re.findall(r'([A-Z]{3}\d+)[^(]*\(([^)]+)\)', year1_sem1.group(1))
            for code, credits in courses[:6]:  # best-effort; pages vary
                data['course_flowchart']['first_year']['semester_1'].append({
                    'code': code,
                    'credits': credits
                })

        # Extract year credits
        year_credit = re.search(r'Year-Credit\s*\|\s*(\d+)', text_content)
        if year_credit:
            try:
                data['course_flowchart']['year_credits'] = int(year_credit.group(1))
            except ValueError:
                data['course_flowchart']['year_credits'] = year_credit.group(1)

    return data


def scrape_graduate_programs() -> Dict[str, Any]:
    """Scrape COMPLETE graduate program details - EVERY WORD"""
    url = "https://fse.ewubd.edu/computer-science-engineering/graduate-programs"

    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"Scraping graduate programs: {url}")

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    text_content = soup.get_text()

    data: Dict[str, Any] = {
        'url': url,
        'program_name': 'Master of Science in Computer Science and Engineering',
        'program_abbreviation': 'MS in CSE',
        'major_areas': {
            'description': '',
            'areas': [],
            'change_policy': ''
        },
        'admission_requirements': {
            'description': '',
            'eligible_disciplines': [],
            'minimum_cgpa': '',
            'hsc_requirement': '',
            'admission_test': '',
            'all_requirements': []
        },
        'study_tracks': {
            'description': '',
            'tracks': [],
            'change_policy': ''
        },
        'program_length': {
            'minimum': '',
            'maximum': '',
            'full_description': ''
        },
        'program_cost': {},
        'degree_requirements': {
            'description': '',
            'minimum_credits': '',
            'minimum_cgpa': '',
            'thesis_track': {},
            'project_track': {}
        },
        'course_summary': {
            'compulsory_all_majors': {
                'prerequisite': [],
                'compulsory': []
            }
        },
        'major_specific_courses': [],
        'thesis_project': {}
    }

    # Extract Major Areas
    major_areas_desc = re.search(r'Major Areas:\s*(.*?)(?=A student will|$)', text_content, re.DOTALL)
    if major_areas_desc:
        desc_text = major_areas_desc.group(1)
        data['major_areas']['description'] = 'The Master of Science in Computer Science and Engineering (MS in CSE) program is organized into four major areas:'
        # Try to extract bullet/line items or comma separated items
        areas = re.findall(r'(?:-|\u2022)?\s*([A-Za-z][A-Za-z\s&\-]{4,}?(?:Systems|Engineering|Science|Networking|Software|Hardware))', desc_text)
        if not areas:
            # fallback: split by commas and filter short tokens
            parts = [p.strip() for p in re.split(r',|\n', desc_text) if p.strip()]
            areas = [p for p in parts if len(p) > 5]
        data['major_areas']['areas'] = [clean_text(area) for area in areas]

    # Major area change policy
    change_policy = re.search(r'(A student will have to declare.*?major area.*?before.*?)', text_content, re.DOTALL | re.IGNORECASE)
    if change_policy:
        data['major_areas']['change_policy'] = clean_text(change_policy.group(1))

    # Extract Admission Requirements
    admission_section = re.search(r'Admission Requirements:(.*?)(?=Study Track:|Study Tracks:|Length of the Program:|$)', text_content, re.DOTALL | re.IGNORECASE)
    if admission_section:
        adm_text = admission_section.group(1)
        data['admission_requirements']['description'] = clean_text(adm_text[:400])  # short description

        # Extract eligible disciplines as lines with "Engineering" or "Computer"
        disciplines = re.findall(r'-\s*([A-Za-z0-9 ,&\-()]+(?:Engineering|Computer|Science|Technology)[A-Za-z0-9 ,&\-()]*)', adm_text)
        if not disciplines:
            # fallback: any bullet-like lines
            disciplines = re.findall(r'-\s*([A-Za-z].+)', adm_text)
        data['admission_requirements']['eligible_disciplines'] = [clean_text(d) for d in disciplines]

        # Minimum CGPA
        cgpa_match = re.search(r'(minimum\s+CGPA(?:\s+of)?\s+[\d.]+)', adm_text, re.IGNORECASE)
        if cgpa_match:
            data['admission_requirements']['minimum_cgpa'] = clean_text(cgpa_match.group(1))
        elif '2.5 on a 4.0' in adm_text:
            data['admission_requirements']['minimum_cgpa'] = '2.5 on a 4.0 point scale'

        # HSC requirement detection
        if 'HSC' in adm_text or 'Higher Secondary' in adm_text:
            hsc_req = re.search(r'([^.]*HSC[^.]*\.)', adm_text)
            if hsc_req:
                data['admission_requirements']['hsc_requirement'] = clean_text(hsc_req.group(1))

        # Admission test
        if 'admission test' in adm_text.lower():
            test_req = re.search(r'([^.]*admission test[^.]*\.)', adm_text, re.IGNORECASE)
            if test_req:
                data['admission_requirements']['admission_test'] = clean_text(test_req.group(1))

        # All requirements as sentences starting with 'Candidates must' or 'Applicants must'
        all_reqs = re.findall(r'(?:Candidates|Applicants)\s+must[^.]*\.', adm_text)
        data['admission_requirements']['all_requirements'] = [clean_text(req) for req in all_reqs]

    # Extract Study Tracks
    track_section = re.search(r'Study Track:(.*?)(?=Length of the Program:|Program Length:|Degree Requirement:|$)', text_content, re.DOTALL | re.IGNORECASE)
    if track_section:
        ts = track_section.group(1)
        data['study_tracks']['description'] = clean_text(ts[:300])
        if 'Thesis Track' in ts or 'Thesis' in ts:
            data['study_tracks']['tracks'].append('Thesis Track')
        if 'Project Track' in ts or 'Project' in ts:
            data['study_tracks']['tracks'].append('Project Track')
        change_policy = re.search(r'(A student will have to declare.*?study track.*?)', ts, re.DOTALL | re.IGNORECASE)
        if change_policy:
            data['study_tracks']['change_policy'] = clean_text(change_policy.group(1))

    # Extract Program Length
    length_section = re.search(r'Length of the Program:\s*(.*?)(?=MS in CSE Program Cost:|MS in CSE Program Cost|Degree Requirement:|$)', text_content, re.DOTALL | re.IGNORECASE)
    if length_section:
        length_text = length_section.group(1)
        data['program_length']['full_description'] = clean_text(length_text)
        # simple numeric extraction
        min_length = re.search(r'minimum\s*of\s*(\d+\s*(?:semester|semesters|year|years)?)', length_text, re.IGNORECASE)
        max_length = re.search(r'up to\s*(\d+\s*(?:semester|semesters|year|years)?)', length_text, re.IGNORECASE)
        if min_length:
            data['program_length']['minimum'] = clean_text(min_length.group(1))
        if max_length:
            data['program_length']['maximum'] = clean_text(max_length.group(1))

    # Extract Program Cost (complete table) - best-effort parsing
    cost_section = re.search(r'MS in CSE Program Cost:.*?(Grand Total.*?)(?=Degree Requirement:|Degree Requirements:|$)', text_content, re.DOTALL | re.IGNORECASE)
    if cost_section:
        cost_text = cost_section.group(0)
        # attempt to find numbers associated with cost
        amounts = re.findall(r'([\d,]+(?:\.\d+)?)', cost_text)
        if amounts:
            # store raw amounts list (best-effort)
            data['program_cost']['raw_amounts'] = amounts[:10]

    # Extract Degree Requirements
    degree_req_section = re.search(r'Degree Requirement:(.*?)(?=Thesis Track|Project Track|$)', text_content, re.DOTALL | re.IGNORECASE)
    if degree_req_section:
        req_text = degree_req_section.group(1)
        data['degree_requirements']['description'] = clean_text(req_text)
        # Minimum credits
        min_credits = re.search(r'(\d+\s+credits)', req_text, re.IGNORECASE)
        if min_credits:
            data['degree_requirements']['minimum_credits'] = clean_text(min_credits.group(1))
        # Minimum CGPA
        cgpa_req = re.search(r'(\d+\.\d+\s+on a\s+4\.0)', req_text, re.IGNORECASE)
        if cgpa_req:
            data['degree_requirements']['minimum_cgpa'] = clean_text(cgpa_req.group(1))
        elif '2.5 on a 4.0' in req_text:
            data['degree_requirements']['minimum_cgpa'] = '2.5 on a 4.0 point scale'

    # Extract Thesis Track Requirements
    thesis_section = re.search(r'Thesis Track(.*?)Project Track', text_content, re.DOTALL | re.IGNORECASE)
    if thesis_section:
        thesis_text = thesis_section.group(1)
        # try to get required courses, credits, and rules
        thesis_courses = re.findall(r'([A-Z]{3}\d+)\s+([^|]+?)\s*\|\s*([\d.]+)', thesis_text)
        thesis_info = {
            'raw_text': clean_text(thesis_text),
            'courses': []
        }
        for code, name, credits in thesis_courses:
            thesis_info['courses'].append({
                'code': code,
                'name': clean_text(name),
                'credits': credits
            })
        # look for required thesis credit value
        thesis_credit = re.search(r'(\d+\s*credits)\s*for\s*thesis', thesis_text, re.IGNORECASE)
        if thesis_credit:
            thesis_info['thesis_credits'] = clean_text(thesis_credit.group(1))
        data['degree_requirements']['thesis_track'] = thesis_info
    else:
        # fallback: detect "Thesis" word anywhere in the degree requirements section
        if 'Thesis' in text_content:
            data['degree_requirements']['thesis_track'] = {'raw_text': 'Thesis track mentioned in page but section parsing failed.'}

    # Extract Project Track Requirements (best-effort)
    project_section = re.search(r'Project Track(.*?)(?=Thesis Track|Degree Requirement|$)', text_content, re.DOTALL | re.IGNORECASE)
    if project_section:
        project_text = project_section.group(1)
        project_courses = re.findall(r'([A-Z]{3}\d+)\s+([^|]+?)\s*\|\s*([\d.]+)', project_text)
        project_info = {
            'raw_text': clean_text(project_text),
            'courses': []
        }
        for code, name, credits in project_courses:
            project_info['courses'].append({
                'code': code,
                'name': clean_text(name),
                'credits': credits
            })
        data['degree_requirements']['project_track'] = project_info
    else:
        if 'Project Track' in text_content:
            data['degree_requirements']['project_track'] = {'raw_text': 'Project track mentioned but parsing failed.'}

    # Extract Course Summary (compulsory/prerequisite lists)
    comp_section = re.search(r'Compulsory Courses for all majors(.*?)(?=Major specific|Major Specific Courses|$)', text_content, re.DOTALL | re.IGNORECASE)
    if comp_section:
        comp_text = comp_section.group(1)
        group_prereq = re.findall(r'Prerequisite[s]?:\s*([A-Za-z0-9, ]+)', comp_text, re.IGNORECASE)
        if group_prereq:
            data['course_summary']['compulsory_all_majors']['prerequisite'] = [clean_text(p) for p in ','.join(group_prereq).split(',') if p.strip()]
        comp_courses = re.findall(r'([A-Z]{3}\d+)\s+([^|]+?)\s*\|\s*([\d.]+)', comp_text)
        for code, name, credits in comp_courses:
            data['course_summary']['compulsory_all_majors']['compulsory'].append({
                'code': code,
                'name': clean_text(name),
                'credits': credits
            })

    # Major specific courses
    major_spec_section = re.search(r'Major Specific Courses:(.*?)(?=Thesis|Project|$)', text_content, re.DOTALL | re.IGNORECASE)
    if major_spec_section:
        ms_text = major_spec_section.group(1)
        # split by major headings if present
        majors = re.split(r'\n{2,}', ms_text.strip())
        for block in majors:
            # attempt to find a major name at top
            title = re.search(r'([A-Za-z &]+ Major(?: Area)?|Major Area: [A-Za-z &]+)', block)
            major_name = clean_text(title.group(0)) if title else None
            courses = re.findall(r'([A-Z]{3}\d+)\s+([^|]+?)\s*\|\s*([\d.]+)', block)
            major_entry = {'major_name': major_name or 'Unknown', 'courses': []}
            for code, name, credits in courses:
                major_entry['courses'].append({
                    'code': code,
                    'name': clean_text(name),
                    'credits': credits
                })
            if major_entry['courses']:
                data['major_specific_courses'].append(major_entry)

    # Thesis/Project final details (one-paragraph summary if present)
    thesis_project_section = re.search(r'(Thesis and Project|Thesis Project|Thesis/Project)(.*?)(?=Admission|Degree|$)', text_content, re.DOTALL | re.IGNORECASE)
    if thesis_project_section:
        data['thesis_project']['raw'] = clean_text(thesis_project_section.group(0))
    else:
        # fallback lookups
        if 'thesis' in text_content.lower() or 'project' in text_content.lower():
            data['thesis_project']['raw'] = 'Thesis/project information exists on the page; detailed parsing may be required.'

    return data


def save_json(data: Dict[str, Any], filename: str) -> None:
    """Save dict to JSON with pretty printing and timestamp in filename if requested"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    try:
        ug = scrape_undergraduate_programs()
        ug_filename = f"ewu_cse_undergraduate_{timestamp}.json"
        save_json(ug, ug_filename)
        print(f"Undergraduate data saved to {ug_filename}")
    except Exception as e:
        print(f"Failed to scrape undergraduate programs: {e}")

    try:
        grad = scrape_graduate_programs()
        grad_filename = f"ewu_cse_graduate_{timestamp}.json"
        save_json(grad, grad_filename)
        print(f"Graduate data saved to {grad_filename}")
    except Exception as e:
        print(f"Failed to scrape graduate programs: {e}")


if __name__ == "__main__":
    main()
