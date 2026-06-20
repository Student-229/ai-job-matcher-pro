import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import hashlib

# PostgreSQL URL (fallback to SQLite locally)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///users.db')

# Fix PostgreSQL URL format for SQLAlchemy
if DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ── User Model ──
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    phone = Column(String(20))
    
    # ✨ NEW: Subscription Fields
    resume_analysis_count = Column(Integer, default=0)  # Counter for free tier
    is_premium = Column(Boolean, default=False)  # Premium status
    plan_type = Column(String(20), default="free")  # free, plan_1month, plan_3month, plan_yearly
    plan_expiry = Column(DateTime, nullable=True)  # When plan expires
    payment_id = Column(String(100), nullable=True)  # Razorpay payment ID
    subscription_date = Column(DateTime, nullable=True)  # When user subscribed
    
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)

# ── Resume History Model ──
class ResumeHistory(Base):
    __tablename__ = 'resume_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    user_email = Column(String(100))
    resume_text = Column(Text)
    skills = Column(Text)
    education = Column(String(200))
    experience = Column(String(100))
    top_job = Column(String(100))
    match_percent = Column(Integer)
    analyzed_at = Column(DateTime, default=datetime.now)

# Create all tables
Base.metadata.create_all(bind=engine)

def init_database():
    """Database initialize karo"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized!")

def create_user(full_name, email, password, phone=""):
    """Naya user banao"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        session = SessionLocal()
        new_user = User(
            full_name=full_name,
            email=email,
            password=hashed_password,
            phone=phone,
            created_at=datetime.now(),
            is_premium=False,
            plan_type="free",
            resume_analysis_count=0
        )
        session.add(new_user)
        session.commit()
        session.close()
        return True, "Account created successfully!"
    except Exception as e:
        return False, str(e)

def verify_user(email, password):
    """User login verify karo"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        session = SessionLocal()
        user = session.query(User).filter(
            User.email == email, 
            User.password == hashed_password
        ).first()
        
        if user:
            user.last_login = datetime.now()
            user.login_count += 1
            session.commit()
            result = {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'phone': user.phone,
                'is_premium': user.is_premium,
                'plan_type': user.plan_type,
                'resume_analysis_count': user.resume_analysis_count,
                'plan_expiry': str(user.plan_expiry) if user.plan_expiry else None,
                'created_at': str(user.created_at),
                'last_login': str(user.last_login),
                'login_count': user.login_count
            }
            session.close()
            return True, result
        else:
            session.close()
            return False, "Invalid email or password!"
    except Exception as e:
        return False, str(e)

def get_user_by_id(user_id):
    """User ID se user dhundho"""
    try:
        session = SessionLocal()
        user = session.query(User).filter(User.id == user_id).first()
        session.close()
        return user
    except Exception as e:
        print(f"Get user error: {e}")
        return None

def increment_analysis_count(user_id):
    """Analysis counter badhao"""
    try:
        session = SessionLocal()
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            user.resume_analysis_count += 1
            session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"Increment count error: {e}")
        return False

def activate_subscription(user_id, plan_type, payment_id):
    """Subscription activate karo"""
    try:
        session = SessionLocal()
        user = session.query(User).filter(User.id == user_id).first()
        
        if user:
            # Plan duration determine karo
            plan_durations = {
                'plan_1month': 30,
                'plan_3month': 90,
                'plan_yearly': 365
            }
            
            days = plan_durations.get(plan_type, 30)
            
            user.is_premium = True
            user.plan_type = plan_type
            user.payment_id = payment_id
            user.subscription_date = datetime.now()
            user.plan_expiry = datetime.now() + timedelta(days=days)
            user.resume_analysis_count = 0  # Reset counter for premium
            
            session.commit()
            session.close()
            return True, {
                'plan': plan_type,
                'expiry': str(user.plan_expiry),
                'message': 'Subscription activated successfully!'
            }
        else:
            session.close()
            return False, 'User not found'
    except Exception as e:
        return False, str(e)

def check_plan_expiry(user_id):
    """Plan expiry check karo"""
    try:
        session = SessionLocal()
        user = session.query(User).filter(User.id == user_id).first()
        
        if user and user.is_premium and user.plan_expiry:
            if datetime.now() > user.plan_expiry:
                # Plan expire ho gaya
                user.is_premium = False
                user.plan_type = "free"
                user.resume_analysis_count = 0
                session.commit()
                session.close()
                return True, "expired"
            else:
                session.close()
                return True, "active"
        
        session.close()
        return True, "free"
    except Exception as e:
        print(f"Check expiry error: {e}")
        return False, "error"

def save_resume_history(user_id, user_email, resume_text, resume_data, matched_jobs):
    """Resume analysis history save karo"""
    try:
        import json
        top_job = matched_jobs[0]['job_title'] if matched_jobs else "N/A"
        top_match = matched_jobs[0]['match_percent'] if matched_jobs else 0
        
        session = SessionLocal()
        history = ResumeHistory(
            user_id=user_id,
            user_email=user_email,
            resume_text=resume_text[:2000],
            skills=json.dumps(resume_data.get('skills', [])),
            education=resume_data.get('education', ''),
            experience=resume_data.get('experience_years', ''),
            top_job=top_job,
            match_percent=top_match,
            analyzed_at=datetime.now()
        )
        session.add(history)
        session.commit()
        session.close()
        return True
    except Exception as e:
        print(f"Save history error: {e}")
        return False

def get_all_users():
    """Admin ke liye sab users"""
    try:
        session = SessionLocal()
        users = session.query(User).order_by(User.created_at.desc()).all()
        result = [(
            u.id, u.full_name, u.email, u.phone, 
            str(u.created_at), str(u.last_login) if u.last_login else None, 
            u.login_count, u.is_premium, u.plan_type
        ) for u in users]
        session.close()
        return result
    except Exception as e:
        print(f"Get users error: {e}")
        return []

def get_all_resumes():
    """Admin ke liye sab resume history"""
    try:
        session = SessionLocal()
        resumes = session.query(ResumeHistory).order_by(ResumeHistory.analyzed_at.desc()).all()
        result = [(
            r.id, r.user_email, r.skills, r.education, 
            r.experience, r.top_job, r.match_percent, str(r.analyzed_at)
        ) for r in resumes]
        session.close()
        return result
    except Exception as e:
        print(f"Get resumes error: {e}")
        return []

def get_stats():
    """Dashboard stats"""
    try:
        session = SessionLocal()
        
        total_users = session.query(User).count()
        total_resumes = session.query(ResumeHistory).count()
        premium_users = session.query(User).filter(User.is_premium == True).count()
        avg_match = session.query(ResumeHistory).all()
        avg_match_percent = sum([r.match_percent for r in avg_match]) / len(avg_match) if avg_match else 0
        
        session.close()
        return {
            'total_users': total_users,
            'total_resumes': total_resumes,
            'premium_users': premium_users,
            'avg_match': round(avg_match_percent, 1)
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {'total_users': 0, 'total_resumes': 0, 'premium_users': 0, 'avg_match': 0}