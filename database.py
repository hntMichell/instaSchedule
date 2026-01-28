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
            status TEXT DEFAULT 'Agendado'
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_scheduled_at ON posts (scheduled_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts (status)")
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

def get_post(post_id):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = c.fetchone()
    conn.close()
    return post

def update_post(post_id, data):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        UPDATE posts
        SET client = ?, post_type = ?, caption = ?, image_url = ?, scheduled_at = ?
        WHERE id = ?
    """, (
        data["client"],
        data["post_type"],
        data["caption"],
        data["image_url"],
        data["scheduled_at"],
        post_id
    ))
    conn.commit()
    updated = c.rowcount
    conn.close()
    return updated

def delete_post(post_id):
    conn = connect()
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted

def get_counts():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM posts")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM posts WHERE status = ?", ("Publicado",))
    published = c.fetchone()[0]
    conn.close()
    return {"total": total, "published": published}
