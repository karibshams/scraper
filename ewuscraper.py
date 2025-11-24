"""
EWU CSE Department Complete Web Scraper
Extracts all information from East West University's CSE department website
Outputs: JSON, CSV, PDF, and Markdown formats for RAG systems
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import time
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Any

# PDF generation
try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'fpdf2'])
    from fpdf import FPDF


class EWUCSEScraper:
    """Complete scraper for EWU CSE Department website"""
    
    def __init__(self):
        self.base_url = "https://fse.ewubd.edu/computer-science-engineering"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.data = {
            'department_info': {},
            'faculty_members': [],
            'courses': {'core_courses': [], 'elective_courses': []},
            'programs': {'undergraduate': {}, 'graduate': {}},
            'lab_facilities': [],
            'administrative_officials': [],
            'metadata': {
                'scraped_at': datetime.now().isoformat(),
                'source': 'East West University CSE Department'
            }
        }
    
    def fetch_page(self, url: str, retries: int = 3) -> BeautifulSoup:
        """Fetch and parse a webpage with retry logic"""
        for attempt in range(retries):
            try:
                print(f"Fetching: {url} (Attempt {attempt + 1}/{retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                time.sleep(1)  # Be polite to the server
                return BeautifulSoup(response.content, 'html.parser')
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                if attempt == retries - 1:
                    print(f"Failed to fetch {url} after {retries} attempts")
                    return None
                time.sleep(2)
        return None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def scrape_department_info(self):
        """Scrape main department page information"""
        print("\n=== Scraping Department Info ===")
        soup = self.fetch_page(self.base_url)
        if not soup:
            return
        
        # Extract chairperson message
        chairperson_section = soup.find('div', class_=re.compile('chairperson|message', re.I))
        if chairperson_section:
            name = chairperson_section.find('h3', class_=re.compile('name|title'))
            if name:
                self.data['department_info']['chairperson_name'] = self.clean_text(name.get_text())
            
            designation = chairperson_section.find('p', class_=re.compile('designation|position'))
            if designation:
                self.data['department_info']['chairperson_designation'] = self.clean_text(designation.get_text())
            
            message = chairperson_section.find('div', class_=re.compile('message|content'))
            if message:
                self.data['department_info']['chairperson_message'] = self.clean_text(message.get_text())
        
        # Extract department description
        description = soup.find('div', class_=re.compile('description|about|intro'))
        if description:
            self.data['department_info']['description'] = self.clean_text(description.get_text())
        
        print(f"Department info extracted: {len(self.data['department_info'])} items")
    
    def scrape_faculty_members(self):
        """Scrape all faculty members"""
        print("\n=== Scraping Faculty Members ===")
        url = f"{self.base_url}/faculty-members"
        soup = self.fetch_page(url)
        if not soup:
            return
        
        # Find all faculty member links or cards
        faculty_elements = soup.find_all(['a', 'div'], href=re.compile(r'faculty-view'))
        
        for element in faculty_elements:
            faculty = {}
            
            # Extract name
            name_elem = element.find(['h3', 'h4', 'h5', 'strong'])
            if not name_elem:
                name_elem = element
            faculty['name'] = self.clean_text(name_elem.get_text())
            
            # Extract designation
            designation_elem = element.find_next(['p', 'span', 'div'])
            if designation_elem:
                designation_text = self.clean_text(designation_elem.get_text())
                if designation_text and len(designation_text) < 100:
                    faculty['designation'] = designation_text
            
            # Extract profile link
            if element.name == 'a' and element.get('href'):
                faculty['profile_url'] = f"https://fse.ewubd.edu{element['href']}"
            
            # Try to get detailed info from profile page
            if faculty.get('profile_url'):
                faculty.update(self.scrape_faculty_profile(faculty['profile_url']))
            
            if faculty.get('name'):
                self.data['faculty_members'].append(faculty)
        
        print(f"Scraped {len(self.data['faculty_members'])} faculty members")
    
    def scrape_faculty_profile(self, url: str) -> Dict:
        """Scrape individual faculty profile"""
        soup = self.fetch_page(url)
        if not soup:
            return {}
        
        profile = {}
        
        # Extract email
        email = soup.find('a', href=re.compile(r'mailto:'))
        if email:
            profile['email'] = email.get('href').replace('mailto:', '')
        
        # Extract phone
        phone = soup.find(text=re.compile(r'\d{3,}'))
        if phone:
            profile['phone'] = self.clean_text(phone)
        
        # Extract research interests
        research = soup.find(['div', 'section'], class_=re.compile(r'research|interest'))
        if research:
            profile['research_interests'] = self.clean_text(research.get_text())
        
        # Extract education
        education = soup.find(['div', 'section'], class_=re.compile(r'education|qualification'))
        if education:
            profile['education'] = self.clean_text(education.get_text())
        
        # Extract publications
        publications = soup.find(['div', 'section'], class_=re.compile(r'publication'))
        if publications:
            pub_list = []
            for pub in publications.find_all(['li', 'p']):
                pub_text = self.clean_text(pub.get_text())
                if pub_text:
                    pub_list.append(pub_text)
            profile['publications'] = pub_list
        
        time.sleep(0.5)  # Be nice to the server
        return profile
    
    def scrape_courses(self, course_type: str):
        """Scrape core or elective courses"""
        print(f"\n=== Scraping {course_type.title()} Courses ===")
        url = f"{self.base_url}/{course_type}"
        soup = self.fetch_page(url)
        if not soup:
            return
        
        # Find all course sections (usually by course code like CSE400, CSE487, etc.)
        course_codes = soup.find_all(['h2', 'h3', 'h4'], text=re.compile(r'^CSE\d+'))
        
        for code_elem in course_codes:
            course = {'course_code': self.clean_text(code_elem.get_text())}
            
            # Get the parent section containing all course info
            course_section = code_elem.find_parent(['div', 'section'])
            if not course_section:
                course_section = code_elem.find_next_siblings()
            
            # Extract credit hours
            credit_table = code_elem.find_next('table')
            if credit_table:
                course['credits'] = self.extract_table_data(credit_table)
            
            # Extract prerequisites
            prereq = code_elem.find_next(text=re.compile(r'Prerequisite', re.I))
            if prereq:
                course['prerequisite'] = self.clean_text(prereq.parent.get_text())
            
            # Extract course objective
            objective = code_elem.find_next(text=re.compile(r'Course Objective', re.I))
            if objective:
                obj_parent = objective.find_parent(['p', 'div'])
                if obj_parent:
                    course['objective'] = self.clean_text(obj_parent.get_text())
            
            # Extract course outcomes
            outcomes_header = code_elem.find_next(text=re.compile(r'Course Outcomes', re.I))
            if outcomes_header:
                outcomes = []
                outcomes_section = outcomes_header.find_parent(['div', 'section'])
                if outcomes_section:
                    outcome_table = outcomes_section.find('table')
                    if outcome_table:
                        for row in outcome_table.find_all('tr')[1:]:  # Skip header
                            cols = row.find_all(['td', 'th'])
                            if len(cols) >= 2:
                                outcomes.append({
                                    'code': self.clean_text(cols[0].get_text()),
                                    'description': self.clean_text(cols[1].get_text())
                                })
                course['outcomes'] = outcomes
            
            # Extract course contents
            contents_header = code_elem.find_next(text=re.compile(r'Course Contents', re.I))
            if contents_header:
                contents = []
                contents_table = contents_header.find_next('table')
                if contents_table:
                    for row in contents_table.find_all('tr')[1:]:  # Skip header
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 2:
                            contents.append({
                                'topic': self.clean_text(cols[0].get_text()),
                                'outcome': self.clean_text(cols[1].get_text())
                            })
                course['contents'] = contents
            
            if course_type == 'core-courses':
                self.data['courses']['core_courses'].append(course)
            else:
                self.data['courses']['elective_courses'].append(course)
        
        course_key = 'core_courses' if course_type == 'core-courses' else 'elective_courses'
        print(f"Scraped {len(self.data['courses'][course_key])} {course_type}")
    
    def extract_table_data(self, table) -> List[Dict]:
        """Extract data from HTML table"""
        data = []
        rows = table.find_all('tr')
        
        if len(rows) < 2:
            return data
        
        headers = [self.clean_text(th.get_text()) for th in rows[0].find_all(['th', 'td'])]
        
        for row in rows[1:]:
            cols = row.find_all(['td', 'th'])
            row_data = {}
            for i, col in enumerate(cols):
                if i < len(headers):
                    row_data[headers[i]] = self.clean_text(col.get_text())
            if row_data:
                data.append(row_data)
        
        return data
    
    def scrape_programs(self, program_type: str):
        """Scrape undergraduate or graduate programs"""
        print(f"\n=== Scraping {program_type.title()} Programs ===")
        url = f"{self.base_url}/{program_type}-programs"
        soup = self.fetch_page(url)
        if not soup:
            return
        
        program_data = {
            'description': '',
            'curriculum': [],
            'requirements': [],
            'structure': []
        }
        
        # Extract program description
        description = soup.find(['div', 'section'], class_=re.compile(r'description|overview'))
        if description:
            program_data['description'] = self.clean_text(description.get_text())
        
        # Extract curriculum tables
        tables = soup.find_all('table')
        for table in tables:
            table_data = self.extract_table_data(table)
            if table_data:
                program_data['curriculum'].extend(table_data)
        
        # Extract requirements
        req_section = soup.find(['div', 'section'], class_=re.compile(r'requirement'))
        if req_section:
            req_list = req_section.find_all(['li', 'p'])
            program_data['requirements'] = [self.clean_text(req.get_text()) for req in req_list if req.get_text()]
        
        if program_type == 'undergraduate':
            self.data['programs']['undergraduate'] = program_data
        else:
            self.data['programs']['graduate'] = program_data
        
        print(f"{program_type.title()} program data extracted")
    
    def scrape_lab_facilities(self):
        """Scrape lab facilities information"""
        print("\n=== Scraping Lab Facilities ===")
        url = f"{self.base_url}/lab-facilities"
        soup = self.fetch_page(url)
        if not soup:
            return
        
        # Find lab sections
        lab_sections = soup.find_all(['div', 'section'], class_=re.compile(r'lab|facility'))
        
        for lab in lab_sections:
            lab_data = {}
            
            # Extract lab name
            name = lab.find(['h2', 'h3', 'h4'])
            if name:
                lab_data['name'] = self.clean_text(name.get_text())
            
            # Extract description
            description = lab.find(['p', 'div'], class_=re.compile(r'description|content'))
            if description:
                lab_data['description'] = self.clean_text(description.get_text())
            
            # Extract equipment list
            equipment = lab.find('ul')
            if equipment:
                lab_data['equipment'] = [self.clean_text(li.get_text()) for li in equipment.find_all('li')]
            
            if lab_data:
                self.data['lab_facilities'].append(lab_data)
        
        print(f"Scraped {len(self.data['lab_facilities'])} lab facilities")
    
    def scrape_administrative_officials(self):
        """Scrape administrative officials"""
        print("\n=== Scraping Administrative Officials ===")
        url = f"{self.base_url}/administrative-officials"
        soup = self.fetch_page(url)
        if not soup:
            return
        
        # Find official cards or list items
        officials = soup.find_all(['div', 'li'], class_=re.compile(r'official|staff|member'))
        
        for official in officials:
            official_data = {}
            
            # Extract name
            name = official.find(['h3', 'h4', 'h5', 'strong'])
            if name:
                official_data['name'] = self.clean_text(name.get_text())
            
            # Extract designation
            designation = official.find(['p', 'span'], class_=re.compile(r'designation|position'))
            if designation:
                official_data['designation'] = self.clean_text(designation.get_text())
            
            # Extract contact
            email = official.find('a', href=re.compile(r'mailto:'))
            if email:
                official_data['email'] = email.get('href').replace('mailto:', '')
            
            if official_data.get('name'):
                self.data['administrative_officials'].append(official_data)
        
        print(f"Scraped {len(self.data['administrative_officials'])} administrative officials")
    
    def scrape_all(self):
        """Scrape all sections"""
        print("="*60)
        print("Starting EWU CSE Department Scraping")
        print("="*60)
        
        try:
            self.scrape_department_info()
            self.scrape_faculty_members()
            self.scrape_courses('core-courses')
            self.scrape_courses('elective-courses')
            self.scrape_programs('undergraduate')
            self.scrape_programs('graduate')
            self.scrape_lab_facilities()
            self.scrape_administrative_officials()
            
            print("\n" + "="*60)
            print("Scraping completed successfully!")
            print("="*60)
            
        except Exception as e:
            print(f"\nError during scraping: {e}")
            import traceback
            traceback.print_exc()
    
    def export_json(self, filename: str = 'ewu_cse_data.json'):
        """Export data to JSON"""
        print(f"\nExporting to JSON: {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print(f"✓ JSON export completed: {filename}")
    
    def export_csv(self, base_filename: str = 'ewu_cse'):
        """Export data to CSV files (one per section)"""
        print(f"\nExporting to CSV files...")
        
        # Export faculty members
        if self.data['faculty_members']:
            filename = f'{base_filename}_faculty.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'designation', 'email', 'phone', 
                                                       'research_interests', 'education', 'profile_url'])
                writer.writeheader()
                for faculty in self.data['faculty_members']:
                    writer.writerow(faculty)
            print(f"✓ Faculty CSV: {filename}")
        
        # Export core courses
        if self.data['courses']['core_courses']:
            filename = f'{base_filename}_core_courses.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['course_code', 'prerequisite', 'objective'])
                writer.writeheader()
                for course in self.data['courses']['core_courses']:
                    row = {k: str(v) for k, v in course.items() if k in ['course_code', 'prerequisite', 'objective']}
                    writer.writerow(row)
            print(f"✓ Core Courses CSV: {filename}")
        
        # Export elective courses
        if self.data['courses']['elective_courses']:
            filename = f'{base_filename}_elective_courses.csv'
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['course_code', 'prerequisite', 'objective'])
                writer.writeheader()
                for course in self.data['courses']['elective_courses']:
                    row = {k: str(v) for k, v in course.items() if k in ['course_code', 'prerequisite', 'objective']}
                    writer.writerow(row)
            print(f"✓ Elective Courses CSV: {filename}")
    
    def export_markdown(self, filename: str = 'ewu_cse_data.md'):
        """Export data to Markdown (ideal for RAG systems)"""
        print(f"\nExporting to Markdown: {filename}")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# East West University - Department of Computer Science & Engineering\n\n")
            f.write(f"*Data scraped on: {self.data['metadata']['scraped_at']}*\n\n")
            f.write("---\n\n")
            
            # Department Info
            if self.data['department_info']:
                f.write("## Department Information\n\n")
                for key, value in self.data['department_info'].items():
                    f.write(f"**{key.replace('_', ' ').title()}:** {value}\n\n")
            
            # Faculty Members
            if self.data['faculty_members']:
                f.write("## Faculty Members\n\n")
                for faculty in self.data['faculty_members']:
                    f.write(f"### {faculty.get('name', 'N/A')}\n\n")
                    f.write(f"- **Designation:** {faculty.get('designation', 'N/A')}\n")
                    if faculty.get('email'):
                        f.write(f"- **Email:** {faculty['email']}\n")
                    if faculty.get('phone'):
                        f.write(f"- **Phone:** {faculty['phone']}\n")
                    if faculty.get('research_interests'):
                        f.write(f"- **Research Interests:** {faculty['research_interests']}\n")
                    if faculty.get('education'):
                        f.write(f"- **Education:** {faculty['education']}\n")
                    f.write("\n")
            
            # Core Courses
            if self.data['courses']['core_courses']:
                f.write("## Core Courses\n\n")
                for course in self.data['courses']['core_courses']:
                    f.write(f"### {course.get('course_code', 'N/A')}\n\n")
                    if course.get('prerequisite'):
                        f.write(f"**Prerequisite:** {course['prerequisite']}\n\n")
                    if course.get('objective'):
                        f.write(f"**Objective:** {course['objective']}\n\n")
                    if course.get('outcomes'):
                        f.write("**Course Outcomes:**\n\n")
                        for outcome in course['outcomes']:
                            f.write(f"- **{outcome.get('code')}:** {outcome.get('description')}\n")
                        f.write("\n")
            
            # Elective Courses
            if self.data['courses']['elective_courses']:
                f.write("## Elective Courses\n\n")
                for course in self.data['courses']['elective_courses']:
                    f.write(f"### {course.get('course_code', 'N/A')}\n\n")
                    if course.get('prerequisite'):
                        f.write(f"**Prerequisite:** {course['prerequisite']}\n\n")
                    if course.get('objective'):
                        f.write(f"**Objective:** {course['objective']}\n\n")
            
            # Programs
            if self.data['programs']['undergraduate']:
                f.write("## Undergraduate Program\n\n")
                prog = self.data['programs']['undergraduate']
                if prog.get('description'):
                    f.write(f"{prog['description']}\n\n")
            
            if self.data['programs']['graduate']:
                f.write("## Graduate Program\n\n")
                prog = self.data['programs']['graduate']
                if prog.get('description'):
                    f.write(f"{prog['description']}\n\n")
            
            # Lab Facilities
            if self.data['lab_facilities']:
                f.write("## Lab Facilities\n\n")
                for lab in self.data['lab_facilities']:
                    f.write(f"### {lab.get('name', 'N/A')}\n\n")
                    if lab.get('description'):
                        f.write(f"{lab['description']}\n\n")
                    if lab.get('equipment'):
                        f.write("**Equipment:**\n\n")
                        for eq in lab['equipment']:
                            f.write(f"- {eq}\n")
                        f.write("\n")
            
            # Administrative Officials
            if self.data['administrative_officials']:
                f.write("## Administrative Officials\n\n")
                for official in self.data['administrative_officials']:
                    f.write(f"### {official.get('name', 'N/A')}\n\n")
                    f.write(f"- **Designation:** {official.get('designation', 'N/A')}\n")
                    if official.get('email'):
                        f.write(f"- **Email:** {official['email']}\n")
                    f.write("\n")
        
        print(f"✓ Markdown export completed: {filename}")
    
    def export_pdf(self, filename: str = 'ewu_cse_data.pdf'):
        """Export data to PDF"""
        print(f"\nExporting to PDF: {filename}")
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'East West University', 0, 1, 'C')
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Department of Computer Science & Engineering', 0, 1, 'C')
        pdf.ln(5)
        
        # Metadata
        pdf.set_font('Arial', 'I', 10)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
        pdf.ln(10)
        
        # Department Info
        if self.data['department_info']:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'Department Information', 0, 1)
            pdf.set_font('Arial', '', 10)
            for key, value in self.data['department_info'].items():
                pdf.multi_cell(0, 6, f"{key.replace('_', ' ').title()}: {str(value)[:500]}")
                pdf.ln(2)
        
        # Faculty Members Summary
        if self.data['faculty_members']:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f"Faculty Members ({len(self.data['faculty_members'])})", 0, 1)
            pdf.set_font('Arial', '', 9)
            for faculty in self.data['faculty_members'][:50]:  # Limit to first 50
                pdf.multi_cell(0, 5, f"• {faculty.get('name', 'N/A')} - {faculty.get('designation', 'N/A')}")
        
        # Core Courses Summary
        if self.data['courses']['core_courses']:
            pdf.add_page()
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, f"Core Courses ({len(self.data['courses']['core_courses'])})", 0, 1)
            pdf.set_font('Arial', '', 9)
            for course in self.data['courses']['core_courses'][:30]:  # Limit to first 30
                pdf.multi_cell(0, 5, f"• {course.get('course_code', 'N/A')}")
                if course.get('objective'):
                    pdf.multi_cell(0, 5, f"  {course['objective'][:200]}...")
                pdf.ln(2)
        
        pdf.output(filename)
        print(f"✓ PDF export completed: {filename}")


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("EWU CSE Department Complete Web Scraper")
    print("="*60 + "\n")
    
    # Initialize scraper
    scraper = EWUCSEScraper()
    
    # Scrape all data
    scraper.scrape_all()
    
    # Export to all formats
    print("\n" + "="*60)
    print("Exporting Data to Multiple Formats")
    print("="*60)
    
    scraper.export_json('ewu_cse_complete_data.json')
    scraper.export_csv('ewu_cse')
    scraper.export_markdown('ewu_cse_rag_ready.md')
    scraper.export_pdf('ewu_cse_report.pdf')
    
    # Summary
    print("\n" + "="*60)
    print("Scraping Summary")
    print("="*60)
    print(f"Faculty Members: {len(scraper.data['faculty_members'])}")
    print(f"Core Courses: {len(scraper.data['courses']['core_courses'])}")
    print(f"Elective Courses: {len(scraper.data['courses']['elective_courses'])}")
    print(f"Lab Facilities: {len(scraper.data['lab_facilities'])}")
    print(f"Administrative Officials: {len(scraper.data['administrative_officials'])}")
    print("\n" + "="*60)
    print("All files generated successfully!")
    print("="*60 + "\n")
    
    print("Files created:")
    print("  1. ewu_cse_complete_data.json     - Complete JSON data")
    print("  2. ewu_cse_faculty.csv            - Faculty members CSV")
    print("  3. ewu_cse_core_courses.csv       - Core courses CSV")
    print("  4. ewu_cse_elective_courses.csv   - Elective courses CSV")
    print("  5. ewu_cse_rag_ready.md           - Markdown for RAG system")
    print("  6. ewu_cse_report.pdf             - PDF report")
    print("\nReady for your RAG-based AI system! 🎓🤖")


if __name__ == "__main__":
    main()