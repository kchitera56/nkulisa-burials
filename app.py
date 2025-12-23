import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Firebase
import firebase_admin
from firebase_admin import credentials, db as firebase_db

# =========================
# LOAD ENV VARIABLES
# =========================
load_dotenv()

# =========================
# FLASK APP
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# =========================
# DATABASE CONFIG (Render-safe)
# =========================
database_url = os.getenv("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///nkulisa.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =========================
# EMAIL CONFIG
# =========================
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

# =========================
# 🔐 FIREBASE INIT (SAFE – ENV ONLY)
# =========================
firebase_credentials = os.getenv("FIREBASE_CREDENTIALS")
firebase_db_url = os.getenv("FIREBASE_DB_URL")

if firebase_credentials and not firebase_admin._apps:
    try:
        cred = credentials.Certificate(json.loads(firebase_credentials))
        firebase_admin.initialize_app(cred, {
            "databaseURL": firebase_db_url
        })
        print("✅ Firebase initialized safely via ENV")
    except Exception as e:
        print("❌ Firebase initialization error:", e)
else:
    print("⚠ Firebase not initialized (missing FIREBASE_CREDENTIALS)")

# =========================
# DATABASE MODEL
# =========================
class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    package = db.Column(db.String(50), nullable=False)

# =========================
# ROUTES
# =========================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        try:
            msg = Message(
                subject="New Contact Message - Nkulisa Burials NPC",
                recipients=[app.config["MAIL_USERNAME"]],
                body=f"""Name: {request.form['name']}
Email: {request.form['email']}

Message:
{request.form['message']}
"""
            )
            mail.send(msg)
            flash("Message sent successfully.", "success")
        except Exception as e:
            flash(f"Failed to send message: {str(e)}", "danger")

        return redirect(url_for("contact"))

    return render_template("contact.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["name"].strip()
        phone = request.form["phone"].strip()
        email = request.form["email"].strip().lower()
        package = request.form["package"]

        if Member.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        member = Member(
            full_name=full_name,
            email=email,
            phone=phone,
            package=package
        )

        db.session.add(member)
        db.session.commit()

        # Push to Firebase (safe)
        try:
            if firebase_admin._apps:
                firebase_db.reference("members").push({
                    "full_name": full_name,
                    "email": email,
                    "phone": phone,
                    "package": package
                })
        except Exception as e:
            print("Firebase write error:", e)

        flash("Registration successful!", "success")
        return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/constitution")
def constitution():
    return send_from_directory("docs", "constitution.pdf", as_attachment=True)

# =========================
# INIT DATABASE
# =========================
with app.app_context():
    db.create_all()

# =========================
# LOCAL RUN ONLY
# =========================
if __name__ == "__main__":
    app.run(debug=True)
