import os
import uuid
from flask import Flask, render_template, request, redirect, jsonify, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from database import create_tables, insert_post, get_posts, delete_post, get_counts, get_post, update_post
from scheduler import schedule_post, cancel_post

app = Flask(__name__)
create_tables()
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

def save_upload(file):
    if not file or file.filename == "":
        return None
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return None
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    safe_name = secure_filename(file.filename)
    filename = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(file_path)
    return url_for("static", filename=f"uploads/{filename}")

def run_app():
    app.run(debug=True)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        scheduled_at = request.form.get("scheduled_at", "").strip()
        try:
            datetime.fromisoformat(scheduled_at)
        except ValueError:
            return jsonify({"error": "scheduled_at inválido. Use ISO 8601."}), 400

        image_url = request.form.get("image_url", "").strip() or None
        uploaded_url = save_upload(request.files.get("image_file"))
        if uploaded_url:
            image_url = uploaded_url

        data = {
            "client": request.form.get("client", "").strip(),
            "post_type": request.form.get("post_type", "").strip(),
            "caption": request.form.get("caption", "").strip(),
            "image_url": image_url,
            "scheduled_at": scheduled_at
        }

        post_id = insert_post(data)
        schedule_post(post_id, data)
        return redirect("/")

    posts = get_posts()
    counts = get_counts()
    return render_template("dashboard.html", posts=posts, counts=counts)

@app.route("/delete/<int:post_id>", methods=["DELETE"])
def delete(post_id):
    cancel_post(post_id)
    deleted = delete_post(post_id)
    if deleted == 0:
        return jsonify({"success": False, "error": "Post não encontrado"}), 404
    return jsonify({"success": True})

@app.route("/post/<int:post_id>", methods=["GET", "PUT"])
def post_detail(post_id):
    if request.method == "GET":
        post = get_post(post_id)
        if not post:
            return jsonify({"error": "Post não encontrado"}), 404
        return jsonify({
            "id": post[0],
            "client": post[1],
            "post_type": post[2],
            "caption": post[3],
            "image_url": post[4],
            "scheduled_at": post[5],
            "status": post[6]
        })

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        form_data = {
            "client": payload.get("client"),
            "post_type": payload.get("post_type"),
            "caption": payload.get("caption"),
            "image_url": payload.get("image_url"),
            "scheduled_at": payload.get("scheduled_at")
        }
        image_file = None
    else:
        form_data = request.form
        image_file = request.files.get("image_file")

    scheduled_at = (form_data.get("scheduled_at") or "").strip()
    try:
        datetime.fromisoformat(scheduled_at)
    except ValueError:
        return jsonify({"error": "scheduled_at inválido. Use ISO 8601."}), 400

    image_url = (form_data.get("image_url") or "").strip() or None
    uploaded_url = save_upload(image_file)
    if uploaded_url:
        image_url = uploaded_url

    data = {
        "client": (form_data.get("client") or "").strip(),
        "post_type": (form_data.get("post_type") or "").strip(),
        "caption": (form_data.get("caption") or "").strip(),
        "image_url": image_url,
        "scheduled_at": scheduled_at
    }
    updated = update_post(post_id, data)
    if updated == 0:
        return jsonify({"error": "Post não encontrado"}), 404
    cancel_post(post_id)
    schedule_post(post_id, data)
    return jsonify({"success": True})
