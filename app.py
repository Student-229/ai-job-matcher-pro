from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import io
from resume_parser import extract_text_from_pdf, extract_skills_from_resume, get_resume_feedback
from job_matcher import match_jobs, get_skill_gap_advice, get_career_roadmap
from database import init_database, create_user, verify_user, save_resume_history, get_all_users, get_all_resumes, get_stats
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'aijobmatcher2026')

# Admin emails
ADMIN_EMAILS = ['rhtvs32@gmail.com', 'admin@aijobmatcher.com']

# Database initialize karo
init_database()


# ── Auth Routes ──

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.get_json()
    email = data.get('email', '')
    password = data.get('password', '')
    
    success, result = verify_user(email, password)
    
    if success:
        session['user'] = result
        session['logged_in'] = True
        return jsonify({'success': True, 'user': result})
    else:
        return jsonify({'success': False, 'error': result})


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    data = request.get_json()
    full_name = data.get('full_name', '')
    email = data.get('email', '')
    password = data.get('password', '')
    phone = data.get('phone', '')
    
    if not full_name or not email or not password:
        return jsonify({'success': False, 'error': 'All fields required!'})
    
    success, message = create_user(full_name, email, password, phone)
    return jsonify({'success': success, 'message': message})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── Main Routes ──

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html', user=session.get('user'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user = session.get('user')
    if user['email'] not in ADMIN_EMAILS:
        return redirect(url_for('index'))
    
    users = get_all_users()
    resumes = get_all_resumes()
    stats = get_stats()
    return render_template('admin.html', users=users, resumes=resumes, stats=stats)


# ── API Routes ──

@app.route('/analyze', methods=['POST'])
def analyze():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Please login first!'}), 401
    
    try:
        if 'resume' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['resume']
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files allowed'}), 400
        
        file_bytes = file.read()
        resume_text = extract_text_from_pdf(io.BytesIO(file_bytes))
        
        if len(resume_text.strip()) < 50:
            return jsonify({'success': False, 'error': 'Could not read PDF. Please try another file.'}), 400
        
        resume_data = extract_skills_from_resume(resume_text)
        
        if not resume_data.get('skills'):
            resume_data['skills'] = ["Communication", "Microsoft Office", "Teamwork"]
        
        matched_jobs = match_jobs(resume_data)
        feedback = get_resume_feedback(resume_text)
        
        skill_advice = ""
        roadmap = {}
        
        if matched_jobs:
            top_job = matched_jobs[0]
            if top_job.get('missing_skills'):
                skill_advice = get_skill_gap_advice(top_job['job_title'], top_job['missing_skills'][:5])
                roadmap = get_career_roadmap(top_job['job_title'], resume_data.get('skills', [])[:5], top_job['missing_skills'][:5])
        
        # Save to database
        user = session.get('user')
        if user:
            save_resume_history(user['id'], user['email'], resume_text, resume_data, matched_jobs)
        
        return jsonify({
            'success': True,
            'resume_data': resume_data,
            'matched_jobs': matched_jobs,
            'feedback': feedback,
            'skill_advice': skill_advice,
            'roadmap': roadmap
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/job-advice', methods=['POST'])
def job_advice():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Please login first!'}), 401
    
    try:
        data = request.get_json()
        advice = get_skill_gap_advice(data.get('job_title', ''), data.get('missing_skills', []))
        roadmap = get_career_roadmap(data.get('job_title', ''), data.get('current_skills', []), data.get('missing_skills', []))
        return jsonify({'success': True, 'advice': advice, 'roadmap': roadmap})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)