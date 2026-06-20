import pandas as pd
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# IMPORTANT: Use environment variable, NOT hardcoded key
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def load_jobs():
    """Jobs database load karo"""
    try:
        # Try multiple paths
        paths = ["jobs_data.csv", "../jobs_data.csv", "./jobs_data.csv"]
        for path in paths:
            if os.path.exists(path):
                df = pd.read_csv(path)
                print(f"Jobs loaded from {path}: {len(df)} jobs found")
                return df
        
        # If no file found, create default jobs
        print("No jobs_data.csv found, using default job list")
        return create_default_jobs()
    except Exception as e:
        print(f"Jobs load error: {e}")
        return create_default_jobs()


def create_default_jobs():
    """Create default job list if CSV not found"""
    default_jobs = pd.DataFrame([
        {"job_title": "Data Analyst", "required_skills": "Python SQL Excel Tableau", "description": "Analyze data and create reports", "salary_range": "₹4L-₹12L", "category": "Technology"},
        {"job_title": "Python Developer", "required_skills": "Python Django Flask REST API", "description": "Build web applications", "salary_range": "₹5L-₹15L", "category": "Technology"},
        {"job_title": "Machine Learning Engineer", "required_skills": "Python Machine Learning TensorFlow", "description": "Build ML models", "salary_range": "₹8L-₹25L", "category": "Technology"},
        {"job_title": "Web Developer", "required_skills": "HTML CSS JavaScript React", "description": "Build websites", "salary_range": "₹3L-₹12L", "category": "Technology"},
        {"job_title": "Data Scientist", "required_skills": "Python R Statistics MachineLearning", "description": "Extract insights from data", "salary_range": "₹6L-₹20L", "category": "Technology"},
        {"job_title": "Business Analyst", "required_skills": "Excel SQL PowerBI Communication", "description": "Bridge business and technology", "salary_range": "₹4L-₹14L", "category": "Business"},
        {"job_title": "DevOps Engineer", "required_skills": "Linux Docker Kubernetes AWS", "description": "Manage infrastructure", "salary_range": "₹6L-₹20L", "category": "Technology"},
        {"job_title": "UI UX Designer", "required_skills": "Figma AdobeXD Prototyping", "description": "Design user interfaces", "salary_range": "₹3L-₹12L", "category": "Design"},
        {"job_title": "Project Manager", "required_skills": "Agile Scrum JIRA Leadership", "description": "Manage projects", "salary_range": "₹6L-₹20L", "category": "Management"},
        {"job_title": "Cloud Engineer", "required_skills": "AWS Azure GCP Terraform", "description": "Build cloud infrastructure", "salary_range": "₹7L-₹22L", "category": "Technology"}
    ])
    return default_jobs


def match_jobs(resume_data):
    """Resume ke basis pe best jobs dhundho — IMPROVED MATCHING"""
    
    jobs_df = load_jobs()
    
    if jobs_df.empty:
        return []
    
    # User skills lowercase mein aur clean
    user_skills = set()
    for s in resume_data.get("skills", []):
        # Clean each skill
        clean_s = str(s).lower().strip().replace(" ", "").replace("-", "")
        user_skills.add(clean_s)
        # Also add original for partial matching
        user_skills.add(str(s).lower().strip())
    
    if not user_skills:
        user_skills = {"python", "excel", "communication"}  # Default skills
    
    results = []
    
    for _, job in jobs_df.iterrows():
        # Job required skills
        required_skills_raw = str(job["required_skills"]).lower().split()
        required = set()
        for s in required_skills_raw:
            clean_s = s.replace(",", "").replace(" ", "").strip()
            required.add(clean_s)
        
        # Match calculate karo
        matched = set()
        for user_skill in user_skills:
            for req_skill in required:
                # Exact match
                if user_skill == req_skill:
                    matched.add(req_skill)
                # Partial match (e.g., "machinelearning" vs "machine learning")
                elif req_skill in user_skill or user_skill in req_skill:
                    if len(req_skill) > 3:  # Avoid short matches
                        matched.add(req_skill)
        
        missing = required - matched
        
        # Score calculate karo
        if len(required) > 0:
            score = int((len(matched) / len(required)) * 100)
        else:
            score = 0
        
        # Boost score if we have any matches
        if matched and score < 30:
            score = 30
        
        results.append({
            "job_title": job["job_title"],
            "match_percent": score,
            "matched_skills": list(matched)[:10],
            "missing_skills": list(missing)[:10],
            "description": job["description"],
            "salary_range": job.get("salary_range", "Competitive"),
            "category": job.get("category", "General")
        })
    
    # Score ke hisaab se sort karo
    results.sort(key=lambda x: x["match_percent"], reverse=True)
    
    return results[:10]


def get_skill_gap_advice(job_title, missing_skills):
    """Skill gap ke liye AI advice"""
    
    if not missing_skills:
        return "🎉 Great news! You have all the required skills for this role. Start applying today!"
    
    missing_str = ', '.join(missing_skills[:5])
    
    prompt = f"""
You are a career counselor. Help someone become a {job_title}.

They need to learn: {missing_str}

Give practical advice in 2-3 sentences:
1. What to learn first
2. Best free resource (YouTube, Coursera, etc.)

Keep it short and actionable.
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Advice error: {e}")
        top_skill = missing_skills[0] if missing_skills else "core skills"
        return f"Start by learning {top_skill} on YouTube or Coursera. Practice daily for 30 days!"


def get_career_roadmap(job_title, current_skills, missing_skills):
    """Career roadmap generate karo"""
    
    if not missing_skills:
        missing_skills = ["advanced skills"]
    
    prompt = f"""
Create a simple 3-month roadmap for {job_title}.

Current skills: {', '.join(current_skills[:5])}
Skills to learn: {', '.join(missing_skills[:5])}

Return ONLY valid JSON:
{{
    "month1": {{
        "focus": "Main focus",
        "tasks": ["Task 1", "Task 2", "Task 3"],
        "resource": "YouTube/Coursera"
    }},
    "month2": {{
        "focus": "Main focus", 
        "tasks": ["Task 1", "Task 2", "Task 3"],
        "resource": "Free resource"
    }},
    "month3": {{
        "focus": "Main focus",
        "tasks": ["Task 1", "Task 2", "Task 3"],
        "resource": "Resource name"
    }},
    "final_goal": "What you'll achieve"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=600
        )
        
        result = response.choices[0].message.content
        result = result.replace("```json", "").replace("```", "").strip()
        
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            result = json_match.group()
        
        return json.loads(result)
        
    except Exception as e:
        print(f"Roadmap error: {e}")
        return {
            "month1": {
                "focus": f"Learn {missing_skills[0] if missing_skills else 'basics'}",
                "tasks": ["Watch tutorials", "Practice daily", "Build projects"],
                "resource": "YouTube / Coursera"
            },
            "month2": {
                "focus": "Build portfolio",
                "tasks": ["Create projects", "Join communities", "Practice problems"],
                "resource": "GitHub / FreeCodeCamp"
            },
            "month3": {
                "focus": "Job preparation",
                "tasks": ["Update resume", "Apply for jobs", "Prepare interviews"],
                "resource": "LinkedIn / Indeed"
            },
            "final_goal": f"Ready to apply for {job_title} positions!"
        }