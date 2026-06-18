from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import io
import json
import hashlib
import razorpay
from datetime import datetime, timedelta
from resume_parser import extract_text_from_pdf, extract_skills_from_resume, get_resume_feedback
from job_matcher import match_jobs, get_skill_gap_advice, get_career_roadmap
from database import init_database, create_user, verify_user, get_user_by_email, update_user_subscription, can_user_analyze, save_resume_history, save_payment, save_subscription, get_all_users, get_all_resumes, get_subscriptions, get_stats
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'aijobmatcher2026')

# Razorpay init
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if RAZORPAY_KEY_ID else None

# Admin emails
ADMIN_EMAILS = ['rhtvs32@gmail.com', 'admin@aijobmatcher.com']

# Database initialize karo
init_database()

# ─── Routes ───

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
    subscriptions = get_subscriptions()
    stats = get_stats()
    return render_template('admin.html', users=users, resumes=resumes, subscriptions=subscriptions, stats=stats)

# ─── API Routes ───

@app.route('/check-user-status', methods=['POST'])
def check_user_status():
    """Check karo user kitne free analyses use kar chuka hai"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Please login!'}), 401
    
    data = request.get_json()
    email = data.get('email', session.get('user', {}).get('email'))
    
    user = get_user_by_email(email)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Check subscription
    is_subscribed = False
    if user['subscription_status'] != 'free':
        end_date = user.get('subscription_end_date')
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                if end_dt > datetime.now():
                    is_subscribed = True
            except:
                pass
    
    return jsonify({
        'success': True,
        'free_analyses_used': user['free_analyses_used'],
        'free_analyses_limit': 3,
        'is_subscribed': is_subscribed,
        'subscription_status': user['subscription_status'],
        'subscription_end_date': user.get('subscription_end_date')
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Please login first!'}), 401
    
    try:
        user = session.get('user')
        user_id = user['id']
        email = user['email']
        
        # Check if user can analyze
        can_analyze, message, status = can_user_analyze(user_id, email)
        
        if not can_analyze:
            return jsonify({
                'success': False, 
                'error': message,
                'limit_reached': True,
                'need_subscription': True
            }), 403
        
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
        save_resume_history(user_id, email, resume_text, resume_data, matched_jobs)
        
        return jsonify({
            'success': True,
            'resume_data': resume_data,
            'matched_jobs': matched_jobs,
            'feedback': feedback,
            'skill_advice': skill_advice,
            'roadmap': roadmap,
            'free_analyses_left': 3 - get_user_by_email(email)['free_analyses_used']
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

# ─── Subscription API Routes ───

@app.route('/create-subscription', methods=['POST'])
def create_subscription():
    """Subscription create karo"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Please login first!'}), 401
    
    try:
        data = request.get_json()
        plan = data.get('plan')  # 'monthly', 'quarterly', 'yearly'
        email = data.get('email', session.get('user', {}).get('email'))
        
        if not razorpay_client:
            return jsonify({'success': False, 'error': 'Payment system not configured'}), 500
        
        # Plan prices and durations
        plans = {
            'monthly': {'amount': 29900, 'days': 30, 'name': 'Monthly'},
            'quarterly': {'amount': 69900, 'days': 90, 'name': 'Quarterly'},
            'yearly': {'amount': 199900, 'days': 365, 'name': 'Yearly'}
        }
        
        if plan not in plans:
            return jsonify({'success': False, 'error': 'Invalid plan'}), 400
        
        # Razorpay order create karo
        order_data = {
            'amount': plans[plan]['amount'],
            'currency': 'INR',
            'receipt': f'receipt_{email}_{plan}_{datetime.now().timestamp()}',
            'notes': {
                'email': email,
                'plan': plan
            }
        }
        
        order = razorpay_client.order.create(data=order_data)
        
        return jsonify({
            'success': True,
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'key': RAZORPAY_KEY_ID,
            'plan': plan,
            'plan_name': plans[plan]['name']
        })
        
    except Exception as e:
        print(f"Create subscription error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/verify-payment', methods=['POST'])
def verify_payment():
    """Payment verification"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'Please login first!'}), 401
    
    try:
        data = request.get_json()
        user = session.get('user')
        
        if not razorpay_client:
            return jsonify({'success': False, 'error': 'Payment system not configured'}), 500
        
        # Razorpay signature verify karo
        params = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }
        
        razorpay_client.utility.verify_payment_signature(params)
        
        # Payment successful → User ka subscription activate karo
        email = data.get('email', user['email'])
        plan = data.get('plan', 'monthly')
        
        days_map = {'monthly': 30, 'quarterly': 90, 'yearly': 365}
        amount_map = {'monthly': 29900, 'quarterly': 69900, 'yearly': 199900}
        
        end_date = (datetime.now() + timedelta(days=days_map[plan])).isoformat()
        
        # Update user subscription
        update_user_subscription(email, plan, end_date)
        
        # Save payment record
        save_payment(
            user['id'], 
            data['razorpay_order_id'],
            data['razorpay_payment_id'],
            data['razorpay_signature'],
            amount_map[plan],
            'INR'
        )
        
        # Save subscription record
        save_subscription(
            user['id'],
            plan,
            data['razorpay_order_id'],
            data['razorpay_payment_id'],
            amount_map[plan],
            end_date
        )
        
        # Update session
        user['subscription_status'] = plan
        user['subscription_end_date'] = end_date
        session['user'] = user
        
        return jsonify({'success': True, 'message': 'Payment verified successfully!'})
        
    except Exception as e:
        print(f"Verify payment error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)