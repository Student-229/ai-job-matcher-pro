from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import io
import razorpay
from datetime import datetime
from resume_parser import extract_text_from_pdf, extract_skills_from_resume, get_resume_feedback
from job_matcher import match_jobs, get_skill_gap_advice, get_career_roadmap
from database import (
    init_database, create_user, verify_user, save_resume_history, 
    get_all_users, get_all_resumes, get_stats, 
    increment_analysis_count, get_user_by_id, activate_subscription, 
    check_plan_expiry
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'aijobmatcher2026')

# Admin emails
ADMIN_EMAILS = ['rhtvs32@gmail.com', 'admin@aijobmatcher.com']

# Subscription Plans
SUBSCRIPTION_PLANS = {
    'plan_1month': {
        'name': '1 Month Plan',
        'price': 199,
        'duration_days': 30,
        'features': [
            'Unlimited Resume Analysis',
            'Advanced Job Matching',
            'Priority Support',
            'Download Reports'
        ]
    },
    'plan_3month': {
        'name': '3 Month Plan',
        'price': 499,
        'duration_days': 90,
        'features': [
            'Unlimited Resume Analysis',
            'Advanced Job Matching',
            'Priority Support',
            'Download Reports',
            'Career Coaching'
        ]
    },
    'plan_yearly': {
        'name': 'Yearly Plan',
        'price': 1499,
        'duration_days': 365,
        'features': [
            'Unlimited Resume Analysis',
            'Advanced Job Matching',
            'Priority Support',
            'Download Reports',
            'Career Coaching',
            'Resume Templates'
        ]
    }
}

# Razorpay Setup
razorpay_client = razorpay.Client(
    auth=(os.getenv('RAZORPAY_KEY_ID', ''), os.getenv('RAZORPAY_KEY_SECRET', ''))
)

# Database initialize
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


# ── Subscription Routes ──

@app.route('/get-plans', methods=['GET'])
def get_plans():
    """Get subscription plans"""
    return jsonify(SUBSCRIPTION_PLANS)


@app.route('/create-order', methods=['POST'])
def create_order():
    """Create Razorpay order"""
    if 'user_id' not in session.get('user', {}):
        return jsonify({'status': 'error', 'message': 'Please login first'}), 401
    
    data = request.get_json()
    plan_id = data.get('plan_id')
    
    if plan_id not in SUBSCRIPTION_PLANS:
        return jsonify({'status': 'error', 'message': 'Invalid plan'})
    
    plan = SUBSCRIPTION_PLANS[plan_id]
    amount_in_paise = plan['price'] * 100
    
    try:
        razorpay_order = razorpay_client.order.create(
            amount=amount_in_paise,
            currency='INR',
            receipt=f"order_{session['user']['id']}_{plan_id}",
            notes={
                'user_id': session['user']['id'],
                'plan_id': plan_id
            }
        )
        
        return jsonify({
            'status': 'success',
            'order_id': razorpay_order['id'],
            'amount': amount_in_paise,
            'key': os.getenv('RAZORPAY_KEY_ID'),
            'plan_name': plan['name'],
            'plan_price': plan['price']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment"""
    if 'user_id' not in session.get('user', {}):
        return jsonify({'status': 'error', 'message': 'Please login first'}), 401
    
    data = request.get_json()
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    plan_id = data.get('plan_id')
    
    try:
        # Verify signature
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        
        # Activate subscription
        user_id = session['user']['id']
        success, result = activate_subscription(user_id, plan_id, razorpay_payment_id)
        
        if success:
            # Update session
            session['user']['is_premium'] = True
            session['user']['plan_type'] = plan_id
            session['user']['plan_expiry'] = result['expiry']
            return jsonify({'status': 'success', 'message': 'Payment successful!', 'data': result})
        else:
            return jsonify({'status': 'error', 'message': result})
    
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'status': 'error', 'message': 'Payment verification failed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


# ── Analysis Routes ──

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user_id' not in session.get('user', {}):
        return jsonify({'success': False, 'error': 'Please login first!'}), 401
    
    try:
        user = session.get('user')
        user_id = user['id']
        
        # Check plan expiry
        check_plan_expiry(user_id)
        user_obj = get_user_by_id(user_id)
        
        # FREE PLAN: Check analysis count
        if not user_obj.is_premium and user_obj.resume_analysis_count >= 3:
            return jsonify({
                'status': 'upgrade_required',
                'message': 'You have exhausted your free analyses. Please upgrade!',
                'analyses_left': 0
            })
        
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
        save_resume_history(user_id, user['email'], resume_text, resume_data, matched_jobs)
        
        # Increment counter
        increment_analysis_count(user_id)
        
        # Get updated user
        updated_user = get_user_by_id(user_id)
        analyses_left = 3 - updated_user.resume_analysis_count if not updated_user.is_premium else -1
        
        return jsonify({
            'success': True,
            'resume_data': resume_data,
            'matched_jobs': matched_jobs,
            'feedback': feedback,
            'skill_advice': skill_advice,
            'roadmap': roadmap,
            'analyses_left': analyses_left,
            'is_premium': updated_user.is_premium
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/job-advice', methods=['POST'])
def job_advice():
    if 'user_id' not in session.get('user', {}):
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