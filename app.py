import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("Set SECRET_KEY in the environment before starting the application.")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "true").lower() == "true"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
csrf = CSRFProtect(app)

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "student_resources")
    )

def query(sql, params=(), one=False, commit=False):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close()
        conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

@app.route("/health")
def health():
    try:
        query("SELECT 1", one=True)
        return jsonify(status="ok", database="connected"), 200
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify(status="error", database="unavailable"), 503

@app.context_processor
def common_data():
    return {"current_user": session.get("name"), "current_role": session.get("role")}

@app.route("/")
def index():
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    max_price = request.args.get("max_price", "").strip()
    search = request.args.get("q", "").strip()
    sql = """SELECT l.*, u.name AS provider_name,
             COALESCE((SELECT ROUND(AVG(r.rating),1) FROM reviews r WHERE r.listing_id=l.id),0) AS rating
             FROM listings l JOIN users u ON u.id=l.provider_id WHERE l.status='approved'"""
    params = []
    if category:
        sql += " AND l.category=%s"; params.append(category)
    if location:
        sql += " AND l.location LIKE %s"; params.append("%"+location+"%")
    if search:
        sql += " AND (l.title LIKE %s OR l.description LIKE %s OR l.location LIKE %s)"
        params.extend(["%"+search+"%"]*3)
    if max_price:
        try:
            sql += " AND l.price <= %s"; params.append(float(max_price))
        except ValueError:
            pass
    sql += " ORDER BY l.created_at DESC"
    listings = query(sql, tuple(params))
    return render_template("index.html", listings=listings, category=category, location=location, max_price=max_price, q=search)

@app.route("/listing/<int:listing_id>")
def listing_detail(listing_id):
    listing = query("""SELECT l.*,u.name AS provider_name,u.phone AS provider_phone,
        COALESCE((SELECT ROUND(AVG(r.rating),1) FROM reviews r WHERE r.listing_id=l.id),0) AS rating
        FROM listings l JOIN users u ON u.id=l.provider_id
        WHERE l.id=%s AND l.status='approved'""", (listing_id,), one=True)
    if not listing: abort(404)
    reviews = query("""SELECT r.*,u.name AS student_name FROM reviews r
                       JOIN users u ON u.id=r.student_id WHERE r.listing_id=%s ORDER BY r.created_at DESC""", (listing_id,))
    return render_template("listing_detail.html", listing=listing, reviews=reviews)

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        phone=request.form.get("phone","").strip()
        role=request.form.get("role","student")
        password=request.form.get("password","")
        if role not in ("student","provider"): role="student"
        if not name or not email or len(password)<6:
            flash("Enter your name and email, and use a password of at least 6 characters.", "danger")
        elif query("SELECT id FROM users WHERE email=%s",(email,),one=True):
            flash("An account with this email already exists.", "danger")
        else:
            query("INSERT INTO users(name,email,phone,password_hash,role) VALUES(%s,%s,%s,%s,%s)",
                  (name,email,phone,generate_password_hash(password),role),commit=True)
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        user=query("SELECT * FROM users WHERE email=%s",(email,),one=True)
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session.update(user_id=user["id"],name=user["name"],role=user["role"])
            flash("Welcome back, "+user["name"]+".","success")
            return redirect(url_for("admin_dashboard" if user["role"]=="admin" else "provider_dashboard" if user["role"]=="provider" else "index"))
        flash("Invalid email or password.","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.","info")
    return redirect(url_for("index"))

@app.route("/provider")
@login_required
@role_required("provider")
def provider_dashboard():
    listings=query("SELECT * FROM listings WHERE provider_id=%s ORDER BY created_at DESC",(session["user_id"],))
    return render_template("provider.html", listings=listings)

@app.route("/provider/listing/new", methods=["GET","POST"])
@login_required
@role_required("provider")
def new_listing():
    if request.method=="POST":
        title=request.form.get("title","").strip()
        category=request.form.get("category","")
        location=request.form.get("location","").strip()
        price=request.form.get("price","0")
        description=request.form.get("description","").strip()
        contact=request.form.get("contact","").strip()
        details=request.form.get("details","").strip()
        try: price=float(price)
        except ValueError: price=-1
        if not title or category not in ("Hostel","Rental Room","PG","Mess","Private Library") or not location or price<0:
            flash("Complete all required fields with a valid price.","danger")
        else:
            query("""INSERT INTO listings(provider_id,title,category,location,price,description,contact,details,status)
                     VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
                  (session["user_id"],title,category,location,price,description,contact,details),commit=True)
            flash("Listing submitted. It will appear publicly after admin approval.","success")
            return redirect(url_for("provider_dashboard"))
    return render_template("listing_form.html")

@app.route("/review/<int:listing_id>", methods=["POST"])
@login_required
@role_required("student")
def add_review(listing_id):
    if not query("SELECT id FROM listings WHERE id=%s AND status='approved'",(listing_id,),one=True): abort(404)
    try: rating=int(request.form.get("rating","5"))
    except ValueError: rating=5
    rating=max(1,min(5,rating))
    comment=request.form.get("comment","").strip()
    existing=query("SELECT id FROM reviews WHERE listing_id=%s AND student_id=%s",(listing_id,session["user_id"]),one=True)
    if existing:
        query("UPDATE reviews SET rating=%s,comment=%s WHERE id=%s",(rating,comment,existing["id"]),commit=True)
        flash("Your review was updated.","success")
    else:
        query("INSERT INTO reviews(listing_id,student_id,rating,comment) VALUES(%s,%s,%s,%s)",
              (listing_id,session["user_id"],rating,comment),commit=True)
        flash("Thanks for your feedback.","success")
    return redirect(url_for("listing_detail",listing_id=listing_id))

@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    pending=query("""SELECT l.*,u.name AS provider_name FROM listings l JOIN users u ON u.id=l.provider_id
                     WHERE l.status='pending' ORDER BY l.created_at ASC""")
    listings=query("""SELECT l.*,u.name AS provider_name FROM listings l JOIN users u ON u.id=l.provider_id
                      ORDER BY l.created_at DESC""")
    users=query("SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC")
    return render_template("admin.html",pending=pending,listings=listings,users=users)

@app.route("/admin/listing/<int:listing_id>/<action>", methods=["POST"])
@login_required
@role_required("admin")
def moderate_listing(listing_id,action):
    if action not in ("approve","reject","remove"): abort(400)
    status={"approve":"approved","reject":"rejected","remove":"removed"}[action]
    query("UPDATE listings SET status=%s WHERE id=%s",(status,listing_id),commit=True)
    flash("Listing status updated.","success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."),403
@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="The page or listing could not be found."),404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
