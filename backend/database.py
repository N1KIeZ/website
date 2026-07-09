import sqlite3
import bcrypt
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "users.db"

def init_db():
    """Initialize the database with users table"""
    conn = sqlite3.connect(str(DB_FILE))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            hwid TEXT,
            license_key TEXT,
            subscription_expiry TEXT,
            is_banned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')

    try:
        cursor.execute('ALTER TABLE users ADD COLUMN license_key TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE users ADD COLUMN plaintext_password TEXT')
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    return sqlite3.connect(str(DB_FILE))

def create_user(username, password, email=None, license_key=None):
    """Create a new user with bcrypt-hashed password and plaintext storage"""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT INTO users (username, password, plaintext_password, email, license_key) VALUES (?, ?, ?, ?, ?)',
            (username, hashed, password, email, license_key)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username):
    """Get user by username"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'username': row[1],
            'password': row[2],
            'email': row[3],
            'hwid': row[4],
            'subscription_expiry': row[5],
            'is_banned': row[6],
            'created_at': row[7],
            'last_login': row[8]
        }
    return None

def set_subscription_expiry(username, expiry_iso):
    """Set the subscription_expiry for a user (ISO string or None for lifetime)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET subscription_expiry = ? WHERE username = ?',
        (expiry_iso, username)
    )
    conn.commit()
    conn.close()


def update_hwid(username, hwid):
    """Update user's HWID"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'UPDATE users SET hwid = ?, last_login = ? WHERE username = ?',
        (hwid, datetime.now().isoformat(), username)
    )
    conn.commit()
    conn.close()

def verify_user(username, password, hwid=None):
    """Verify user credentials using bcrypt"""
    user = get_user(username)
    if not user:
        return {'success': False, 'message': 'Invalid username or password'}

    if user['is_banned']:
        return {'success': False, 'message': 'Account is banned'}

    # Check subscription expiry
    if user['subscription_expiry']:
        try:
            expiry = datetime.fromisoformat(user['subscription_expiry'])
            if expiry < datetime.now():
                return {'success': False, 'message': 'Subscription expired'}
        except:
            pass

    # Check password with bcrypt
    try:
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            return {'success': False, 'message': 'Invalid username or password'}
    except Exception:
        return {'success': False, 'message': 'Invalid username or password'}

    # Update HWID and last login
    if hwid:
        update_hwid(username, hwid)

    return {'success': True, 'message': 'Login successful', 'user': user}

# Initialize database on import
init_db()
