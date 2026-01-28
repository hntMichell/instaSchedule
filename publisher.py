import json
import urllib.request
import urllib.parse
from database import connect, get_account_by_id
from notify import notify

def _post_form(url, data):
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def publish_to_instagram(account, image_url, caption):
    ig_user_id = account[3]
    access_token = account[4]
    if not ig_user_id or not access_token:
        raise ValueError("Conta sem ig_user_id/access_token")
    container = _post_form(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
        {
            "image_url": image_url,
            "caption": caption or "",
            "access_token": access_token
        }
    )
    creation_id = container.get("id")
    if not creation_id:
        raise ValueError("Falha ao criar container")
    publish = _post_form(
        f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
        {
            "creation_id": creation_id,
            "access_token": access_token
        }
    )
    return publish

def publish_post(post_id):
    conn = connect()
    c = conn.cursor()

    c.execute("SELECT id, caption, image_url, account_id FROM posts WHERE id = ?", (post_id,))
    post = c.fetchone()
    if not post:
        conn.close()
        return

    post_id, caption, image_url, account_id = post
    try:
        if account_id:
            account = get_account_by_id(None, account_id)
            if account:
                if not image_url:
                    raise ValueError("Post sem image_url")
                publish_to_instagram(account, image_url, caption)
        c.execute("UPDATE posts SET status = ? WHERE id = ?", ("Publicado", post_id))
    except Exception as exc:
        notify(f"Falha ao publicar post {post_id}: {exc}")

    conn.commit()
    conn.close()

    print(f"✅ Post {post_id} publicado")
