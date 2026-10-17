import os
import sqlite3
from functools import wraps
from html import escape

from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

DATABASE = os.path.join(os.path.dirname(__file__), "student_resources.db")


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            price TEXT NOT NULL,
            contact TEXT NOT NULL,
            image TEXT
        )
    """)

    count = conn.execute(
        "SELECT COUNT(*) FROM resources"
    ).fetchone()[0]

    if count == 0:
        resources = [
            (
                "Affordable Student Mess", "Mess",
                "Affordable meals for college students.",
                "Near College Campus", "₹2500/month",
                "mess@example.com",
                "https://images.unsplash.com/photo-1547592180-85f173990554"
            ),
            (
                "Student Boys Hostel", "Hostel",
                "Comfortable accommodation for students.",
                "College Road", "₹5000/month",
                "hostel@example.com",
                "https://images.unsplash.com/photo-1555854877-bab0e564b8d5"
            ),
            (
                "Budget Rental Room", "Rental Room",
                "Affordable rental room for students.",
                "Near Bus Stand", "₹3500/month",
                "rooms@example.com",
                "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267"
            ),
            (
                "College Study Library", "Library",
                "Quiet study space with books and reading facilities.",
                "Main Market", "₹500/month",
                "library@example.com",
                "https://images.unsplash.com/photo-1507842217343-583bb7270b66"
            )
        ]

        conn.executemany("""
            INSERT INTO resources
            (name, category, description, location, price, contact, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, resources)

    conn.commit()
    conn.close()


# ---------------- AUTHENTICATION ----------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to view resources.", "error")
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


# ---------------- DESIGN ----------------

BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} | Student Resources Management System</title>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f8f5;
    color: #26352b;
}

header {
    background: #168447;
    color: white;
    padding: 18px 6%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 14px;
}

header h2 { margin: 0; font-size: 22px; }

nav { display: flex; flex-wrap: wrap; gap: 16px; }

nav a {
    color: white;
    text-decoration: none;
    font-weight: bold;
}

nav a:hover { text-decoration: underline; }

.container {
    width: 90%;
    max-width: 1100px;
    margin: 30px auto;
}

.hero {
    background: linear-gradient(120deg, #168447, #36ad6a);
    color: white;
    padding: 45px 25px;
    text-align: center;
    border-radius: 14px;
    margin-bottom: 30px;
}

.hero h1 { font-size: 32px; margin-top: 0; }

.search-box, .details, .form-card {
    background: white;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 3px 14px #00000010;
}

.search-box { margin-bottom: 30px; }

input, select {
    width: 100%;
    padding: 12px;
    margin: 8px 0 15px;
    border: 1px solid #ccd8ce;
    border-radius: 7px;
    font-size: 15px;
}

button, .btn {
    display: inline-block;
    background: #168447;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 12px 18px;
    text-decoration: none;
    cursor: pointer;
    font-size: 15px;
}

button:hover, .btn:hover { background: #106b38; }

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
    gap: 22px;
}

.card {
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 14px #00000010;
}

.card img {
    width: 100%;
    height: 180px;
    object-fit: cover;
    background: #dce9df;
}

.card-body { padding: 18px; }

.card h3 { color: #168447; margin-top: 10px; }

.category {
    display: inline-block;
    background: #e0f4e7;
    color: #126b37;
    padding: 5px 10px;
    border-radius: 20px;
    font-size: 13px;
}

.price { font-weight: bold; color: #168447; }

.form-card { max-width: 450px; margin: 35px auto; }

.form-card h1 { text-align: center; color: #168447; }

.message {
    background: #e4f5e9;
    color: #126b37;
    padding: 12px;
    border-radius: 7px;
    margin-bottom: 15px;
}

.error { background: #fde8e8; color: #a12020; }

.details img {
    width: 100%;
    max-height: 350px;
    object-fit: cover;
    border-radius: 10px;
}

footer {
    margin-top: 45px;
    padding: 22px;
    text-align: center;
    background: #e4eee7;
}

@media (max-width: 600px) {
    header { padding: 16px 5%; }
    header h2 { font-size: 18px; }
    .hero h1 { font-size: 25px; }
    .container { width: 92%; }
}
</style>
</head>

<body>
<header>
    <h2>Student Resources</h2>
    <nav>
    {% if user_name %}
        <a href="{{ url_for('home') }}">Home</a>
        <a href="{{ url_for('search') }}">Find Resources</a>
        <a href="{{ url_for('logout') }}">Logout</a>
    {% else %}
        <a href="{{ url_for('login') }}">Login</a>
        <a href="{{ url_for('register') }}">Register</a>
    {% endif %}
    </nav>
</header>

<div class="container">
    {% for category, message in get_flashed_messages(with_categories=true) %}
        <div class="message {% if category == 'error' %}error{% endif %}">
            {{ message }}
        </div>
    {% endfor %}
    {{ content|safe }}
</div>

<footer>Student Resources Management System &copy; 2026</footer>
</body>
</html>
"""


def page(title, content):
    return render_template_string(
        BASE,
        title=title,
        content=content,
        user_name=session.get("user_name")
    )


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please complete all fields.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            conn = get_db()
            try:
                conn.execute("""
                    INSERT INTO users (name, email, password)
                    VALUES (?, ?, ?)
                """, (
                    name,
                    email,
                    generate_password_hash(password)
                ))
                conn.commit()
                flash("Registration successful. Please log in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("This email is already registered.", "error")
            finally:
                conn.close()

    content = """
    <div class="form-card">
        <h1>Create Account</h1>
        <form method="POST">
            <label>Full Name</label>
            <input name="name" required maxlength="100">

            <label>Email Address</label>
            <input type="email" name="email" required maxlength="254">

            <label>Password (minimum 6 characters)</label>
            <input type="password" name="password" minlength="6" required>

            <button type="submit" style="width:100%">Register</button>
        </form>
        <p>Already registered? <a href="/login">Login here</a></p>
    </div>
    """
    return page("Register", content)


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")

    content = """
    <div class="form-card">
        <h1>Welcome Back</h1>
        <p style="text-align:center">Log in to explore student resources.</p>
        <form method="POST">
            <label>Email Address</label>
            <input type="email" name="email" required>

            <label>Password</label>
            <input type="password" name="password" required>

            <button type="submit" style="width:100%">Login</button>
        </form>
        <p>Don't have an account? <a href="/register">Register here</a></p>
    </div>
    """
    return page("Login", content)


# ---------------- HOME ----------------

@app.route("/")
@login_required
def home():
    conn = get_db()
    resources = conn.execute(
        "SELECT * FROM resources ORDER BY id DESC"
    ).fetchall()
    conn.close()

    cards = ""

    for r in resources:
        image = escape(r["image"] or "", quote=True)
        name = escape(r["name"])
        category = escape(r["category"])
        location = escape(r["location"])
        price = escape(r["price"])

        cards += f"""
        <div class="card">
            <img src="{image}" alt="Resource image"
                 onerror="this.style.display='none'">
            <div class="card-body">
                <span class="category">{category}</span>
                <h3>{name}</h3>
                <p>{location}</p>
                <p class="price">{price}</p>
                <a class="btn" href="/resource/{r['id']}">View Details</a>
            </div>
        </div>
        """

    content = f"""
    <section class="hero">
        <h1>Student Resources Management System</h1>
        <p>Welcome, {escape(session.get('user_name', 'Student'))}!</p>
        <p>Find affordable mess, hostels, rental rooms and libraries.</p>
        <a class="btn" href="/search"
           style="background:white;color:#168447">Explore Resources</a>
    </section>

    <div class="search-box">
        <h2>Find Student Resources</h2>
        <form action="/search" method="GET">
            <input name="keyword" placeholder="Search resources or locations">
            <select name="category">
                <option value="">All Categories</option>
                <option>Mess</option>
                <option>Hostel</option>
                <option>Rental Room</option>
                <option>Library</option>
            </select>
            <button type="submit">Search</button>
        </form>
    </div>

    <h2>Available Resources</h2>
    <div class="grid">{cards}</div>
    """
    return page("Home", content)


# ---------------- SEARCH ----------------

@app.route("/search")
@login_required
def search():
    keyword = request.args.get("keyword", "").strip()
    category = request.args.get("category", "").strip()

    conn = get_db()
    query = "SELECT * FROM resources WHERE 1=1"
    params = []

    if keyword:
        query += """
            AND (name LIKE ? OR description LIKE ? OR location LIKE ?)
        """
        pattern = f"%{keyword}%"
        params.extend([pattern, pattern, pattern])

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id DESC"
    resources = conn.execute(query, params).fetchall()
    conn.close()

    cards = ""

    for r in resources:
        image = escape(r["image"] or "", quote=True)
        name = escape(r["name"])
        cat = escape(r["category"])
        location = escape(r["location"])
        price = escape(r["price"])

        cards += f"""
        <div class="card">
            <img src="{image}" alt="Resource image"
                 onerror="this.style.display='none'">
            <div class="card-body">
                <span class="category">{cat}</span>
                <h3>{name}</h3>
                <p>{location}</p>
                <p class="price">{price}</p>
                <a class="btn" href="/resource/{r['id']}">View Details</a>
            </div>
        </div>
        """

    if not cards:
        cards = "<p>No resources found. Try another search.</p>"

    selected = {
        item: ("selected" if category == item else "")
        for item in ["Mess", "Hostel", "Rental Room", "Library"]
    }

    content = f"""
    <h1>Search Resources</h1>
    <div class="search-box">
        <form method="GET">
            <label>Keyword</label>
            <input name="keyword" value="{escape(keyword, quote=True)}"
                   placeholder="Enter resource or location">

            <label>Category</label>
            <select name="category">
                <option value="">All Categories</option>
                <option value="Mess" {selected['Mess']}>Mess</option>
                <option value="Hostel" {selected['Hostel']}>Hostel</option>
                <option value="Rental Room" {selected['Rental Room']}>
                    Rental Room
                </option>
                <option value="Library" {selected['Library']}>Library</option>
            </select>

            <button type="submit">Search</button>
            <a class="btn" href="/search">Clear</a>
        </form>
    </div>
    <div class="grid">{cards}</div>
    """
    return page("Search Resources", content)


# ---------------- RESOURCE DETAILS ----------------

@app.route("/resource/<int:resource_id>")
@login_required
def resource_detail(resource_id):
    conn = get_db()
    resource = conn.execute(
        "SELECT * FROM resources WHERE id = ?", (resource_id,)
    ).fetchone()
    conn.close()

    if resource is None:
        return page(
            "Not Found",
            "<h2>Resource not found.</h2><a class='btn' href='/'>Go Home</a>"
        ), 404

    name = escape(resource["name"])
    category = escape(resource["category"])
    description = escape(resource["description"])
    location = escape(resource["location"])
    price = escape(resource["price"])
    contact = escape(resource["contact"])
    image = escape(resource["image"] or "", quote=True)

    content = f"""
    <div class="details">
        <img src="{image}" alt="Resource image"
             onerror="this.style.display='none'">
        <h1>{name}</h1>
        <span class="category">{category}</span>
        <p><strong>Description:</strong> {description}</p>
        <p><strong>Location:</strong> {location}</p>
        <p><strong>Price:</strong> <span class="price">{price}</span></p>
        <p><strong>Contact:</strong> {contact}</p>
        <a class="btn" href="/search">Back to Search</a>
        <a class="btn" href="/">Home</a>
    </div>
    """
    return page("Resource Details", content)


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


# ---------------- START APPLICATION ----------------

# Create database tables and sample resources when the app starts.
init_db()

if __name__ == "__main__":
    app.run(debug=True)

