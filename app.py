from flask import Flask, render_template, request, redirect, jsonify
from database import create_tables, insert_post, get_posts, delete_post
from scheduler import schedule_post

app = Flask(__name__)

def run_app():
    create_tables()
    app.run(debug=True)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        data = {
            "client": request.form["client"],
            "post_type": request.form["post_type"],
            "caption": request.form["caption"],
            "image_url": request.form.get("image_url"),
            "scheduled_at": request.form["scheduled_at"]
        }

        post_id = insert_post(data)
        schedule_post(post_id, data)
        return redirect("/")

    posts = get_posts()
    return render_template("dashboard.html", posts=posts)

@app.route("/delete/<int:post_id>", methods=["DELETE"])
def delete(post_id):
    delete_post(post_id)
    return jsonify({"success": True})
