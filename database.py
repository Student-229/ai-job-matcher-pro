import sqlite3
import os
from datetime import datetime, timedelta
import json

DB_PATH = 'users.db'

def init_database():
    """Database aur tables banao"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            subscription_status TEXT DEFAULT 'free',
            subscription_end_date TEXT,
            free_analyses_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            login_count INTEGER DEFAULT 0
        )
    ''')
    
    # Resume usage table
    c.execute('''
        CREATE TABLE IF NOT EXISTS resume_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            analysis_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Subscription plans table
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_type TEXT NOT NULL,
            razorpay_order_id TEXT,
            razorpay_payment_id TEXT,
            amount INTEGER,
            currency TEXT DEFAULT 'INR',
            status TEXT DEFAULT 'pending',
            start_date TEXT,
            end_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Payments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            razorpay_order_id TEXT,
            razorpay_payment_id TEXT,
            razorpay_signature TEXT,
            amount INTEGER,
            currency TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Resume history table
    c.execute('''
        CREATE TABLE IF NOT EXISTS resume_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_email TEXT,
            resume_text TEXT,
            skills TEXT,
            education TEXT,
            experience TEXT,
            top_job TEXT,
            match_percent INTEGER,
            analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ─── User Functions ───

def create_user(full_name, email, password, phone=""):
    """Naya user banao"""
    import hashlib
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO users (full_name, email, password, phone, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (full_name, email, hashed_password, phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Email already registered!"
    except Exception as e:
        return False, str(e)

def verify_user(email, password):
    """User login verify karo"""
    import hashlib
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=? AND password=?', (email, hashed_password))
        user = c.fetchone()
        
        if user:
            # Update login count and last login
            c.execute('''
                UPDATE users 
                SET last_login=?, login_count=login_count+1 
                WHERE email=?
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email))
            conn.commit()
            conn.close()
            return True, {
                'id': user[0],
                'full_name': user[1],
                'email': user[2],
                'phone': user[4],
                'subscription_status': user[6],
                'subscription_end_date': user[7],
                'free_analyses_used': user[8],
                'created_at': user[5],
                'last_login': user[9],
                'login_count': user[10] + 1
            }
        else:
            conn.close()
            return False, "Invalid email or password!"
    except Exception as e:
        return False, str(e)

def get_user_by_email(email):
    """User ko email se find karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email=?', (email,))
        user = c.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'full_name': user[1],
                'email': user[2],
                'phone': user[4],
                'subscription_status': user[6],
                'subscription_end_date': user[7],
                'free_analyses_used': user[8]
            }
        return None
    except Exception as e:
        print(f"Get user error: {e}")
        return None

def update_user_subscription(email, plan_type, end_date):
    """User subscription update karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE users 
            SET subscription_status=?, subscription_end_date=?, free_analyses_used=0 
            WHERE email=?
        ''', (plan_type, end_date, email))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Update subscription error: {e}")
        return False

def can_user_analyze(user_id, email):
    """Check karo user analysis kar sakta hai ya nahi"""
    
    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        return False, "User not found"
    
    # Agar subscription active hai
    if user['subscription_status'] != 'free':
        end_date = user.get('subscription_end_date')
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                if end_dt > datetime.now():
                    return True, "Subscribed", 'subscribed'
            except:
                pass
    
    # Free users ke liye 3 analyses allowed
    if user['free_analyses_used'] < 3:
        # Increment counter
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE users 
            SET free_analyses_used = free_analyses_used + 1 
            WHERE email=?
        ''', (email,))
        conn.commit()
        conn.close()
        
        # Log usage
        log_resume_usage(user_id, email)
        
        return True, f"Free analysis {user['free_analyses_used'] + 1}/3", 'free'
    
    return False, "Subscription required", 'limit_reached'

def log_resume_usage(user_id, email):
    """Resume analysis usage log karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO resume_usage (user_id, user_email, analysis_date)
            VALUES (?, ?, ?)
        ''', (user_id, email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Log usage error: {e}")
        return False

def save_resume_history(user_id, user_email, resume_text, resume_data, matched_jobs):
    """Resume analysis history save karo"""
    try:
        import json
        top_job = matched_jobs[0]['job_title'] if matched_jobs else "N/A"
        top_match = matched_jobs[0]['match_percent'] if matched_jobs else 0
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO resume_history 
            (user_id, user_email, resume_text, skills, education, experience, top_job, match_percent, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_email,
            resume_text[:2000],
            json.dumps(resume_data.get('skills', [])),
            resume_data.get('education', ''),
            resume_data.get('experience_years', ''),
            top_job,
            top_match,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Save history error: {e}")
        return False

# ─── Payment Functions ───

def save_payment(user_id, order_id, payment_id, signature, amount, currency='INR'):
    """Payment record save karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO payments (user_id, razorpay_order_id, razorpay_payment_id, 
                                  razorpay_signature, amount, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, order_id, payment_id, signature, amount, currency, 'success', 
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Save payment error: {e}")
        return False

def save_subscription(user_id, plan_type, order_id, payment_id, amount, end_date):
    """Subscription record save karo"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO subscriptions (user_id, plan_type, razorpay_order_id, 
                                       razorpay_payment_id, amount, status, start_date, end_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, plan_type, order_id, payment_id, amount, 'active',
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end_date,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Save subscription error: {e}")
        return False

# ─── Admin Functions ───

def get_all_users():
    """Admin ke liye sab users"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, full_name, email, phone, subscription_status, free_analyses_used, created_at, last_login FROM users ORDER BY created_at DESC')
        users = c.fetchall()
        conn.close()
        return users
    except Exception as e:
        print(f"Get users error: {e}")
        return []

def get_all_resumes():
    """Admin ke liye sab resume history"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT r.id, r.user_email, r.skills, r.education, 
                   r.experience, r.top_job, r.match_percent, r.analyzed_at
            FROM resume_history r
            ORDER BY r.analyzed_at DESC
            LIMIT 100
        ''')
        resumes = c.fetchall()
        conn.close()
        return resumes
    except Exception as e:
        print(f"Get resumes error: {e}")
        return []

def get_subscriptions():
    """Admin ke liye sab subscriptions"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            SELECT s.id, u.email, s.plan_type, s.amount, s.status, s.start_date, s.end_date
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC
        ''')
        subs = c.fetchall()
        conn.close()
        return subs
    except Exception as e:
        print(f"Get subscriptions error: {e}")
        return []

def get_stats():
    """Dashboard stats"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM resume_history')
        total_resumes = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM users WHERE subscription_status != "free"')
        paid_users = c.fetchone()[0]
        
        c.execute('SELECT SUM(amount) FROM payments WHERE status="success"')
        total_revenue = c.fetchone()[0] or 0
        
        c.execute('SELECT COUNT(*) FROM users WHERE date(created_at) = date("now")')
        today_users = c.fetchone()[0]
        
        conn.close()
        return {
            'total_users': total_users,
            'total_resumes': total_resumes,
            'paid_users': paid_users,
            'total_revenue': total_revenue,
            'today_users': today_users
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {'total_users': 0, 'total_resumes': 0, 'paid_users': 0, 'total_revenue': 0, 'today_users': 0}