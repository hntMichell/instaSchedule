import sqlite3

DB = "posts.db"

def connect():
    return sqlite3.connect(DB, check_same_thread=False)

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
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_post(data):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO posts (client, post_type, caption, image_url, scheduled_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["client"],
        data["post_type"],
        data["caption"],
        data["image_url"],
        data["scheduled_at"],
        "Agendado"
    ))
    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return post_id

def get_posts():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM posts ORDER BY scheduled_at ASC")
    posts = c.fetchall()
    conn.close()
    return posts
