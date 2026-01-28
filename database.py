import sqlite3
from datetime import datetime

DB = "posts.db"

def connect():
    return sqlite3.connect(DB, check_same_thread=False)

def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def create_tables():
    conn = connect()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            post_type TEXT,
            caption TEXT,
            image_url TEXT,
            scheduled_at TEXT,
            status TEXT DEFAULT 'Agendado'
        )
    """)
    if not _column_exists(c, "posts", "account_id"):
        c.execute("ALTER TABLE posts ADD COLUMN account_id INTEGER")
    if not _column_exists(c, "posts", "user_id"):
        c.execute("ALTER TABLE posts ADD COLUMN user_id INTEGER")
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            client_name TEXT,
            ig_user_id TEXT,
            access_token TEXT,
            token_expires_at TEXT,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_scheduled_at ON posts (scheduled_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts (status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts (user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id)")
    conn.commit()
    conn.close()

def insert_post(data):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO posts (client, post_type, caption, image_url, scheduled_at, status, account_id, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["client"],
        data["post_type"],
        data["caption"],
        data["image_url"],
        data["scheduled_at"],
        "Agendado",
        data.get("account_id"),
        data.get("user_id")
    ))
    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return post_id

def get_posts(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE user_id = ? ORDER BY scheduled_at ASC", (user_id,))
    posts = c.fetchall()
    conn.close()
    return posts

def get_post(user_id, post_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    post = c.fetchone()
    conn.close()
    return post

def update_post(user_id, post_id, data):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE posts
        SET client = ?, post_type = ?, caption = ?, image_url = ?, scheduled_at = ?, account_id = ?
        WHERE id = ? AND user_id = ?
    """, (
        data["client"],
        data["post_type"],
        data["caption"],
        data["image_url"],
        data["scheduled_at"],
        data.get("account_id"),
        post_id,
        user_id
    ))
    conn.commit()
    updated = c.rowcount
    conn.close()
    return updated

def delete_post(user_id, post_id):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted

def get_counts(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM posts WHERE status = ? AND user_id = ?", ("Publicado", user_id))
    published = c.fetchone()[0]
    conn.close()
    return {"total": total, "published": published}

def create_user(name, email, password_hash):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (name, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
    """, (name, email, password_hash, datetime.utcnow().isoformat()))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id

def get_user_by_email(email):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_account(data):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO accounts (user_id, client_name, ig_user_id, access_token, token_expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["user_id"],
        data["client_name"],
        data["ig_user_id"],
        data["access_token"],
        data.get("token_expires_at"),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    account_id = c.lastrowid
    conn.close()
    return account_id

def get_accounts(user_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM accounts WHERE user_id = ? ORDER BY client_name ASC", (user_id,))
    accounts = c.fetchall()
    conn.close()
    return accounts

def delete_account(user_id, account_id):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted

def get_account_by_id(user_id, account_id):
    conn = connect()
    c = conn.cursor()
    if user_id is None:
        c.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    else:
        c.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", (account_id, user_id))
    account = c.fetchone()
    conn.close()
    return account
