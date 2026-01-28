import os
import uuid
import json
import urllib.parse
import urllib.request
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, jsonify, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import (
    create_tables,
    insert_post,
    get_posts,
    delete_post,
    get_counts,
    get_post,
    update_post,
    create_user,
    get_user_by_email,
    get_user_by_id,
    add_account,
    get_accounts,
    delete_account,
    get_account_by_id
)
from scheduler import schedule_post, cancel_post

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
create_tables()
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
FB_APP_ID = os.environ.get("FB_APP_ID")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET")
FB_REDIRECT_URI = os.environ.get("FB_REDIRECT_URI")
FB_SCOPE = "instagram_basic,instagram_content_publish,pages_read_engagement"

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

def http_get_json(url):
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post_json(url, data):
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper

def run_app():
    app.run(debug=True)

@app.route("/", methods=["GET", "POST"])
@login_required
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
        account_id = request.form.get("account_id")
        if account_id:
            account = get_account_by_id(session.get("user_id"), int(account_id))
            if not account:
                return jsonify({"error": "Conta inválida"}), 400

        data = {
            "client": request.form.get("client", "").strip(),
            "post_type": request.form.get("post_type", "").strip(),
            "caption": request.form.get("caption", "").strip(),
            "image_url": image_url,
            "scheduled_at": scheduled_at,
            "account_id": int(account_id) if account_id else None,
            "user_id": session.get("user_id")
        }

        post_id = insert_post(data)
        schedule_post(post_id, data)
        return redirect("/")

    posts = get_posts(session.get("user_id"))
    counts = get_counts(session.get("user_id"))
    accounts = get_accounts(session.get("user_id"))
    return render_template("dashboard.html", posts=posts, counts=counts, accounts=accounts, user=get_user_by_id(session.get("user_id")))

@app.route("/delete/<int:post_id>", methods=["DELETE"])
@login_required
def delete(post_id):
    cancel_post(post_id)
    deleted = delete_post(session.get("user_id"), post_id)
    if deleted == 0:
        return jsonify({"success": False, "error": "Post não encontrado"}), 404
    return jsonify({"success": True})

@app.route("/post/<int:post_id>", methods=["GET", "PUT"])
@login_required
def post_detail(post_id):
    if request.method == "GET":
        post = get_post(session.get("user_id"), post_id)
        if not post:
            return jsonify({"error": "Post não encontrado"}), 404
        return jsonify({
            "id": post[0],
            "client": post[1],
            "post_type": post[2],
            "caption": post[3],
            "image_url": post[4],
            "scheduled_at": post[5],
            "status": post[6],
            "account_id": post[7] if len(post) > 7 else None
        })

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        form_data = {
            "client": payload.get("client"),
            "post_type": payload.get("post_type"),
            "caption": payload.get("caption"),
            "image_url": payload.get("image_url"),
            "scheduled_at": payload.get("scheduled_at"),
            "account_id": payload.get("account_id")
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

    account_id = form_data.get("account_id")
    if account_id:
        account = get_account_by_id(session.get("user_id"), int(account_id))
        if not account:
            return jsonify({"error": "Conta inválida"}), 400

    data = {
        "client": (form_data.get("client") or "").strip(),
        "post_type": (form_data.get("post_type") or "").strip(),
        "caption": (form_data.get("caption") or "").strip(),
        "image_url": image_url,
        "scheduled_at": scheduled_at,
        "account_id": int(account_id) if account_id else None
    }
    updated = update_post(session.get("user_id"), post_id, data)
    if updated == 0:
        return jsonify({"error": "Post não encontrado"}), 404
    cancel_post(post_id)
    schedule_post(post_id, data)
    return jsonify({"success": True})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if not user or not check_password_hash(user[3], password):
            return render_template("login.html", error="Credenciais inválidas.")
        session["user_id"] = user[0]
        return redirect("/")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            return render_template("register.html", error="Preencha todos os campos.")
        if get_user_by_email(email):
            return render_template("register.html", error="Email já cadastrado.")
        password_hash = generate_password_hash(password)
        user_id = create_user(name, email, password_hash)
        session["user_id"] = user_id
        return redirect("/")
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")

@app.route("/profile")
@login_required
def profile():
    user = get_user_by_id(session.get("user_id"))
    return render_template("profile.html", user=user)

@app.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts():
    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        ig_user_id = request.form.get("ig_user_id", "").strip()
        access_token = request.form.get("access_token", "").strip()
        token_expires_at = request.form.get("token_expires_at", "").strip() or None
        if not client_name or not ig_user_id or not access_token:
            return render_template(
                "accounts.html",
                accounts=get_accounts(session.get("user_id")),
                error="Preencha nome, IG User ID e Access Token."
            )
        add_account({
            "user_id": session.get("user_id"),
            "client_name": client_name,
            "ig_user_id": ig_user_id,
            "access_token": access_token,
            "token_expires_at": token_expires_at
        })
        return redirect("/accounts")
    return render_template("accounts.html", accounts=get_accounts(session.get("user_id")))

@app.route("/accounts/delete/<int:account_id>", methods=["POST"])
@login_required
def account_delete(account_id):
    deleted = delete_account(session.get("user_id"), account_id)
    if deleted == 0:
        return jsonify({"success": False, "error": "Conta não encontrada"}), 404
    return jsonify({"success": True})

@app.route("/oauth/instagram/start")
@login_required
def instagram_oauth_start():
    if not FB_APP_ID or not FB_REDIRECT_URI:
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Configure FB_APP_ID e FB_REDIRECT_URI no .env."
        )
    state = uuid.uuid4().hex
    session["oauth_state"] = state
    params = {
        "client_id": FB_APP_ID,
        "redirect_uri": FB_REDIRECT_URI,
        "scope": FB_SCOPE,
        "response_type": "code",
        "state": state
    }
    return redirect("https://www.facebook.com/v19.0/dialog/oauth?" + urllib.parse.urlencode(params))

@app.route("/oauth/instagram/callback")
@login_required
def instagram_oauth_callback():
    if request.args.get("error"):
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Autorização negada."
        )
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or state != session.get("oauth_state"):
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Estado de OAuth inválido."
        )
    if not FB_APP_ID or not FB_APP_SECRET or not FB_REDIRECT_URI:
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Configure FB_APP_ID, FB_APP_SECRET e FB_REDIRECT_URI no .env."
        )

    token_resp = http_get_json(
        "https://graph.facebook.com/v19.0/oauth/access_token?" + urllib.parse.urlencode({
            "client_id": FB_APP_ID,
            "redirect_uri": FB_REDIRECT_URI,
            "client_secret": FB_APP_SECRET,
            "code": code
        })
    )
    short_token = token_resp.get("access_token")
    if not short_token:
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Falha ao obter access token."
        )

    long_resp = http_get_json(
        "https://graph.facebook.com/v19.0/oauth/access_token?" + urllib.parse.urlencode({
            "grant_type": "fb_exchange_token",
            "client_id": FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "fb_exchange_token": short_token
        })
    )
    access_token = long_resp.get("access_token")
    expires_in = long_resp.get("expires_in")
    if not access_token:
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Falha ao gerar token de longa duração."
        )

    pages = http_get_json(
        "https://graph.facebook.com/v19.0/me/accounts?" + urllib.parse.urlencode({
            "fields": "id,name,instagram_business_account",
            "access_token": access_token
        })
    )
    page_list = pages.get("data", [])
    ig_accounts = []
    for page in page_list:
        ig = page.get("instagram_business_account")
        if ig and ig.get("id"):
            ig_accounts.append({
                "ig_user_id": ig.get("id"),
                "page_name": page.get("name")
            })

    if not ig_accounts:
        return render_template(
            "accounts.html",
            accounts=get_accounts(session.get("user_id")),
            error="Nenhuma conta Instagram Business/Creator vinculada a esta página."
        )

    session["oauth_token"] = access_token
    session["oauth_expires_in"] = expires_in

    if len(ig_accounts) == 1:
        return _save_ig_account(ig_accounts[0]["ig_user_id"], ig_accounts[0]["page_name"])
    return render_template("select_account.html", accounts=ig_accounts)

@app.route("/oauth/instagram/choose", methods=["POST"])
@login_required
def instagram_oauth_choose():
    ig_user_id = request.form.get("ig_user_id", "").strip()
    page_name = request.form.get("page_name", "").strip()
    if not ig_user_id:
        return redirect("/accounts")
    return _save_ig_account(ig_user_id, page_name)

def _save_ig_account(ig_user_id, page_name):
    access_token = session.get("oauth_token")
    expires_in = session.get("oauth_expires_in")
    if not access_token:
        return redirect("/accounts")

    ig_info = http_get_json(
        "https://graph.facebook.com/v19.0/{ig_user_id}?".format(ig_user_id=ig_user_id) + urllib.parse.urlencode({
            "fields": "username",
            "access_token": access_token
        })
    )
    client_name = ig_info.get("username") or page_name or ("IG " + ig_user_id)
    token_expires_at = None
    if expires_in:
        token_expires_at = (datetime.utcnow().timestamp() + int(expires_in))

    add_account({
        "user_id": session.get("user_id"),
        "client_name": client_name,
        "ig_user_id": ig_user_id,
        "access_token": access_token,
        "token_expires_at": str(token_expires_at) if token_expires_at else None
    })
    session.pop("oauth_token", None)
    session.pop("oauth_expires_in", None)
    return redirect("/accounts")
