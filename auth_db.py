import sqlite3
import hashlib
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "tax_agent.db")

def hash_password(password: str) -> str:
    """Hashes password with SHA-256 and salt."""
    salt = "bd_tax_secure_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes users and chat_sessions tables."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    
    # User chat sessions table (stores full conversation JSON per user)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        category TEXT DEFAULT 'regular',
        messages_json TEXT NOT NULL,
        slots_json TEXT DEFAULT '{}',
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, chat_id)
    );
    """)
    conn.commit()
    conn.close()

def register_user(name: str, email: str, password: str) -> tuple[bool, str]:
    """Registers a new user."""
    name = name.strip()
    email = email.strip().lower()
    if not name or not email or not password:
        return False, "All fields are required."
    
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."

    conn = get_db()
    cursor = conn.cursor()
    try:
        now_str = datetime.now().strftime("%B %d, %Y")
        p_hash = hash_password(password)
        cursor.execute("INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                       (name, email, p_hash, now_str))
        conn.commit()
        return True, "Registration successful! You can now log in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    except Exception as e:
        return False, f"Registration error: {str(e)}"
    finally:
        conn.close()

def authenticate_user(email: str, password: str) -> tuple[dict | None, str]:
    """Authenticates user and returns user info dict."""
    email = email.strip().lower()
    if not email or not password:
        return None, "Please provide both email and password."

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None, "No account found with this email."

    p_hash = hash_password(password)
    if row["password_hash"] != p_hash:
        return None, "Incorrect password."

    user = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "created_at": row["created_at"]
    }
    return user, "Login successful."

def load_user_conversations(user_id: int) -> dict:
    """Loads all chat sessions for a specific user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT chat_id, title, created_at, category, messages_json, slots_json 
    FROM user_chats 
    WHERE user_id = ? 
    ORDER BY id ASC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    conversations = {}
    for r in rows:
        try:
            msgs = json.loads(r["messages_json"])
        except Exception:
            msgs = []
        try:
            slots = json.loads(r["slots_json"]) if r["slots_json"] else {}
        except Exception:
            slots = {}

        conversations[r["chat_id"]] = {
            "title": r["title"],
            "created_at": r["created_at"],
            "category": r["category"] or "regular",
            "messages": msgs,
            "slots": slots
        }
    return conversations

def save_user_chat(user_id: int, chat_id: str, conv_data: dict):
    """Inserts or updates a user chat session in SQLite."""
    conn = get_db()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = conv_data.get("title", "New Chat")
    created_at = conv_data.get("created_at", datetime.now().strftime("%I:%M %p"))
    category = conv_data.get("category", "regular")
    messages_json = json.dumps(conv_data.get("messages", []), ensure_ascii=False)
    slots_json = json.dumps(conv_data.get("slots", {}), ensure_ascii=False)

    cursor.execute("""
    INSERT INTO user_chats (user_id, chat_id, title, created_at, updated_at, category, messages_json, slots_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, chat_id) DO UPDATE SET
        title = excluded.title,
        updated_at = excluded.updated_at,
        category = excluded.category,
        messages_json = excluded.messages_json,
        slots_json = excluded.slots_json
    """, (user_id, chat_id, title, created_at, now_str, category, messages_json, slots_json))
    conn.commit()
    conn.close()

def delete_user_chat(user_id: int, chat_id: str):
    """Deletes a specific chat session for a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_chats WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()
    conn.close()

def count_user_chats(user_id: int) -> int:
    """Counts total saved sessions for a user."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_chats WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Initialize tables immediately
init_db()
