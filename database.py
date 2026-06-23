import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Database connection pool
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "daily_report_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "password"),
        port=os.getenv("DB_PORT", "5432")
    )
except Exception as e:
    print(f"Error creating connection pool: {e}")
    db_pool = None

def get_connection():
    if db_pool:
        return db_pool.getconn()
    return None

def release_connection(conn):
    if db_pool:
        db_pool.putconn(conn)

def init_db():
    conn = get_connection()
    if not conn:
        return
    try:
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100),
                role VARCHAR(20) DEFAULT 'staff'
            );
        """)

        # Create user_settings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                gemini_api_key VARCHAR(255),
                telegram_bot_token VARCHAR(255),
                telegram_chat_id VARCHAR(100),
                ai_system_instruction TEXT
            );
        """)

        # Create daily_reports table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id) ON DELETE CASCADE,
                report_date DATE NOT NULL,
                header_text VARCHAR(255) DEFAULT 'ตม.จว.นครศรีธรรมราช',
                title_text VARCHAR(255) NOT NULL,
                content TEXT,
                image_paths JSONB,
                font_family VARCHAR(100) DEFAULT 'TH Sarabun IT 9',
                content_font_size INT DEFAULT 19
            );
        """)
        
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

# User Management
def create_user(username, password, full_name, role='staff'):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (username, hashed, full_name, role)
        )
        user_id = cur.fetchone()[0]
        # Initialize empty settings
        cur.execute("INSERT INTO user_settings (user_id) VALUES (%s)", (user_id,))
        conn.commit()
        cur.close()
        return user_id
    except Exception as e:
        print(f"Error creating user: {e}")
        conn.rollback()
        return None
    finally:
        release_connection(conn)

def get_user_by_username(username):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        return user
    finally:
        release_connection(conn)

def get_all_users():
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username, full_name, role FROM users ORDER BY id ASC")
        users = cur.fetchall()
        cur.close()
        return users
    finally:
        release_connection(conn)

def update_user_role(username, role):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET role = %s WHERE username = %s", (role, username))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error updating role: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def delete_user(username):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error deleting user: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def update_admin_role_if_needed(username):
    if username == "admin":
        user = get_user_by_username(username)
        if user and user['role'] != 'admin':
            update_user_role(username, 'admin')

# Settings Management
def get_user_settings(user_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cur.fetchone()
        cur.close()
        return settings
    finally:
        release_connection(conn)

def update_user_settings(user_id, gemini_key, bot_token, chat_id, system_instruction):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_settings 
            SET gemini_api_key = %s, telegram_bot_token = %s, telegram_chat_id = %s, ai_system_instruction = %s
            WHERE user_id = %s
        """, (gemini_key, bot_token, chat_id, system_instruction, user_id))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error updating settings: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

# Report Management
def create_report(user_id, report_date, header_text, title_text, content, image_paths, font_family, font_size):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO daily_reports (user_id, report_date, header_text, title_text, content, image_paths, font_family, content_font_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, report_date, header_text, title_text, content, Json(image_paths), font_family, font_size))
        report_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return report_id
    except Exception as e:
        print(f"Error creating report: {e}")
        conn.rollback()
        return None
    finally:
        release_connection(conn)

def get_reports(user_id=None, role='staff', search_term=None, start_date=None, end_date=None, limit=None, offset=None):
    conn = get_connection()
    if not conn: return []
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT r.*"
        if role == 'admin':
            query += ", u.full_name FROM daily_reports r JOIN users u ON r.user_id = u.id WHERE 1=1"
        else:
            query += " FROM daily_reports r WHERE r.user_id = %s"
            
        params = []
        if role != 'admin':
            params.append(user_id)
            
        if search_term:
            query += " AND (r.title_text ILIKE %s OR r.content ILIKE %s)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern])
            
        if start_date:
            query += " AND r.report_date >= %s"
            params.append(start_date)
            
        if end_date:
            query += " AND r.report_date <= %s"
            params.append(end_date)
            
        query += " ORDER BY r.report_date DESC, r.id DESC"
        
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        if offset is not None:
            query += " OFFSET %s"
            params.append(offset)
        
        cur.execute(query, tuple(params))
        reports = cur.fetchall()
        cur.close()
        return reports
    finally:
        release_connection(conn)

def get_reports_count(user_id=None, role='staff', search_term=None, start_date=None, end_date=None):
    conn = get_connection()
    if not conn: return 0
    try:
        cur = conn.cursor()
        
        query = "SELECT COUNT(*)"
        if role == 'admin':
            query += " FROM daily_reports r JOIN users u ON r.user_id = u.id WHERE 1=1"
        else:
            query += " FROM daily_reports r WHERE r.user_id = %s"
            
        params = []
        if role != 'admin':
            params.append(user_id)
            
        if search_term:
            query += " AND (r.title_text ILIKE %s OR r.content ILIKE %s)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern])
            
        if start_date:
            query += " AND r.report_date >= %s"
            params.append(start_date)
            
        if end_date:
            query += " AND r.report_date <= %s"
            params.append(end_date)
            
        cur.execute(query, tuple(params))
        count = cur.fetchone()[0]
        cur.close()
        return count
    finally:
        release_connection(conn)

def get_report_by_id(report_id):
    conn = get_connection()
    if not conn: return None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM daily_reports WHERE id = %s", (report_id,))
        report = cur.fetchone()
        cur.close()
        return report
    finally:
        release_connection(conn)

def update_report(report_id, report_date, header_text, title_text, content, image_paths, font_family, font_size):
    conn = get_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE daily_reports 
            SET report_date = %s, header_text = %s, title_text = %s, content = %s, image_paths = %s, font_family = %s, content_font_size = %s
            WHERE id = %s
        """, (report_date, header_text, title_text, content, Json(image_paths), font_family, font_size, report_id))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error updating report: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)
