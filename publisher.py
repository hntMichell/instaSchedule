from database import connect

def publish_post(post_id):
    conn = connect()
    c = conn.cursor()

    c.execute("UPDATE posts SET status = ? WHERE id = ?", ("Publicado", post_id))

    conn.commit()
    conn.close()

    print(f"✅ Post {post_id} publicado")
