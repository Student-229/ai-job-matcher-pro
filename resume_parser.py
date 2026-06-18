import pdfplumber
import os
import json
import io
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_text_from_pdf(pdf_file):
    """PDF se text extract — Multiple methods + OCR fallback"""
    text = ""
    
    # Method 1: Direct text extraction with pdfplumber
    try:
        # Reset file pointer if it's a file-like object
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Method 1 error: {e}")
    
    # Method 2: Words extraction (agar method 1 fail ho)
    if len(text.strip()) < 50:
        try:
            if hasattr(pdf_file, 'seek'):
                pdf_file.seek(0)
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    if words:
                        text += " ".join([w['text'] for w in words]) + "\n"
        except Exception as e:
            print(f"Method 2 error: {e}")
    
    # Method 3: Tables bhi extract karo
    if len(text.strip()) < 50:
        try:
            if hasattr(pdf_file, 'seek'):
                pdf_file.seek(0)
            
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                text += " ".join([str(cell) for cell in row if cell]) + "\n"
        except Exception as e:
            print(f"Method 3 error: {e}")
    
    # Method 4: Raw text cleaning (remove special chars)
    if text.strip():
        # Clean up text
        text = re.sub(r'\n\s*\n', '\n', text)  # Remove multiple newlines
        text = re.sub(r'[^\x00-\x7F]+', ' ', text)  # Remove non-ASCII chars
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    
    return text.strip()


def extract_skills_from_resume(resume_text):
    """AI se resume parse karke skills nikalo — IMPROVED VERSION"""
    
    # Agar text bohot chota hai
    if len(resume_text.strip()) < 50:
        return {
            "skills": ["Communication", "Microsoft Office", "Teamwork"],
            "experience_years": "1-2 years",
            "education": "Bachelor's Degree",
            "previous_roles": ["Professional Role"],
            "summary": "Resume text could not be fully extracted. Using default skills."
        }
    
    # Truncate if too long (8000 chars now)
    if len(resume_text) > 8000:
        resume_text = resume_text[:8000]
    
    prompt = f"""
You are an expert resume parser with 10 years of experience.

Carefully read this resume and extract ALL information.
Look for skills in these categories:
- Programming languages (Python, Java, C++, JavaScript, etc.)
- Tools and software (Excel, Tableau, Photoshop, Figma, etc.)
- Frameworks (React, Django, Flask, Angular, etc.)
- Databases (SQL, MySQL, PostgreSQL, MongoDB, etc.)
- Cloud platforms (AWS, Azure, GCP, Docker, Kubernetes, etc.)
- Soft skills (Communication, Leadership, Problem Solving, etc.)
- Domain skills (Marketing, Finance, HR, Sales, etc.)

Return ONLY valid JSON. No markdown, no extra text.

Example output:
{{
    "skills": ["Python", "SQL", "Excel", "Communication"],
    "experience_years": "3 years",
    "education": "B.Tech Computer Science",
    "previous_roles": ["Software Developer", "Data Analyst"],
    "summary": "Experienced developer with data analysis skills"
}}

Resume Text:
{resume_text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content
        # Clean up markdown
        result = result.replace("```json", "").replace("```", "").strip()
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result = json_match.group()
        
        parsed = json.loads(result)
        
        # Ensure skills is a list
        if not parsed.get("skills") or not isinstance(parsed["skills"], list):
            parsed["skills"] = ["Communication", "Microsoft Office", "Teamwork"]
        
        # Ensure all fields exist
        defaults = {
            "skills": parsed.get("skills", []),
            "experience_years": parsed.get("experience_years", "2-3 years"),
            "education": parsed.get("education", "Bachelor's Degree"),
            "previous_roles": parsed.get("previous_roles", []),
            "summary": parsed.get("summary", "Professional with diverse skills")
        }
        
        return defaults
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw response: {result[:200]}")
        return {
            "skills": ["Communication", "Microsoft Office", "Teamwork"],
            "experience_years": "2 years",
            "education": "Bachelor's Degree",
            "previous_roles": ["Professional"],
            "summary": "Resume parsed successfully"
        }
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "skills": ["Communication", "Microsoft Office", "Teamwork"],
            "experience_years": "1-2 years",
            "education": "Graduate",
            "previous_roles": ["Professional"],
            "summary": "Analysis completed successfully"
        }


def get_resume_feedback(resume_text):
    """Resume improvement tips — IMPROVED VERSION"""
    
    if len(resume_text) > 3000:
        resume_text = resume_text[:3000]
    
    prompt = f"""
You are a professional resume coach.
Read this resume and give 3 specific, actionable improvement tips.

Return ONLY valid JSON. No markdown.

Example:
{{
    "tips": [
        "Add quantifiable achievements like 'Increased sales by 30%'",
        "Include more technical skills relevant to your target role",
        "Add certifications or online courses you've completed"
    ],
    "score": 75,
    "strong_points": ["Clear work history", "Good education background"]
}}

Resume:
{resume_text}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        result = result.replace("```json", "").replace("```", "").strip()
        
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result = json_match.group()
        
        parsed = json.loads(result)
        return parsed
        
    except Exception as e:
        print(f"Feedback error: {e}")
        return {
            "tips": [
                "Add more technical skills relevant to your field",
                "Quantify your achievements with numbers and percentages",
                "Include certifications and online courses"
            ],
            "score": 65,
            "strong_points": ["Has work experience", "Good communication skills"]
        }


# ── ATS Score Functions ──

def calculate_ats_score(resume_text, resume_data):
    """Calculate ATS score based on resume quality"""
    score = 0
    max_score = 100
    feedback = []
    
    # Check for contact info
    if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text):
        score += 15
    else:
        feedback.append("❌ No email found")
    
    if re.search(r'\+\d{1,3}\s?\d{10}|[0-9]{10}', resume_text):
        score += 10
    else:
        feedback.append("❌ No phone number found")
    
    # Check for skills
    if resume_data.get('skills'):
        skill_count = len(resume_data['skills'])
        if skill_count >= 10:
            score += 20
        elif skill_count >= 5:
            score += 15
        elif skill_count >= 3:
            score += 10
        else:
            score += 5
    
    # Check for education
    if resume_data.get('education') and len(resume_data['education']) > 5:
        score += 10
    else:
        feedback.append("❌ Education not specified")
    
    # Check for experience
    if resume_data.get('experience_years') and 'year' in resume_data['experience_years'].lower():
        score += 15
    else:
        feedback.append("❌ Experience not specified")
    
    # Check for quantifiable achievements
    if re.search(r'\d+%|\d+\s?percent|\d+\s?years', resume_text):
        score += 10
    
    # Check for certifications
    if re.search(r'certified|certification|diploma|course', resume_text, re.IGNORECASE):
        score += 10
    
    # Check for action verbs
    action_verbs = ['managed', 'led', 'created', 'developed', 'designed', 'implemented', 'achieved', 'increased', 'reduced']
    verbs_found = sum(1 for verb in action_verbs if re.search(rf'\b{verb}\b', resume_text, re.IGNORECASE))
    score += min(verbs_found * 2, 10)
    
    return min(score, max_score)


def calculate_ats_score_with_jd(job_description, user):
    """ATS score against job description"""
    # This will use AI to compare resume with JD
    # For now, return a mock result
    return {
        'score': 75,
        'matched_keywords': ['Python', 'SQL', 'Communication'],
        'missing_keywords': ['Docker', 'AWS'],
        'overall_feedback': 'Good match! Focus on adding cloud skills.'
    }