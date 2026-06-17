import sqlite3
import os
from datetime import datetime

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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            login_count INTEGER DEFAULT 0
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
    print("Database initialized!")

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
                'created_at': user[5],
                'last_login': user[6],
                'login_count': user[7] + 1
            }
        else:
            conn.close()
            return False, "Invalid email or password!"
    except Exception as e:
        return False, str(e)

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

def get_all_users():
    """Admin ke liye sab users"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, full_name, email, phone, created_at, last_login, login_count FROM users ORDER BY created_at DESC')
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
        ''')
        resumes = c.fetchall()
        conn.close()
        return resumes
    except Exception as e:
        print(f"Get resumes error: {e}")
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
        
        c.execute('SELECT COUNT(*) FROM users WHERE date(created_at) = date("now")')
        today_users = c.fetchone()[0]
        
        c.execute('SELECT AVG(match_percent) FROM resume_history')
        avg_match = c.fetchone()[0] or 0
        
        conn.close()
        return {
            'total_users': total_users,
            'total_resumes': total_resumes,
            'today_users': today_users,
            'avg_match': round(avg_match, 1)
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {'total_users': 0, 'total_resumes': 0, 'today_users': 0, 'avg_match': 0}