
import os
import sqlite3
from functools import wraps
from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, flash, abort
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "change-this-secret-before-deployment"
)

DATABASE = "student_resources.db"


# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT DEFAULT '',
            price REAL DEFAULT 0,
            description TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()


# ---------- LOGIN PROTECTION ----------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- COMMON PAGE DESIGN ----------

BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Student Resources Management System</title>
<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f8f5;
    color: #172033;
}
header {
    background: #176b45;
    color: white;
    padding: 18px 7%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}
header a { color: white; text-decoration: none; margin-right: 14px; }
main { max-width: 1000px; margin: 35px auto; padding: 20px; }
.card {
    background: white;
    padding: 22px;
    border-radius: 12px;
    margin-bottom: 18px;
    box-shadow: 0 2px 8px #0001;
}
input, select, textarea, button {
    width: 100%;
    box-sizing: border-box;
    padding: 12px;
    margin: 7px 0 14px;
    border: 1px solid #ccc;
    border-radius: 6px;
}
button, .btn {
    background: #176b45;
    color: white;
    border: 0;
    padding: 12px 18px;
    border-radius: 6px;
    cursor: pointer;
    text-decoration: none;
}
.message { color: #b42318; }
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(230px,1fr));
    gap: 16px;
}
.price { color: #176b45; font-weight: bold; }
</style>
</head>
<body>
{% if session.get('user_id') %}
<header>
    <strong>Student Resources Management System</strong>
    <nav>
        <a href="{{ url_for('home') }}">Home</a>
        <a href="{{ url_for('search') }}">Services</a>
        <a href="{{ url_for('logout') }}">Logout</a>
    </nav>
</header>
{% endif %}
<main>
{% with messages = get_flashed_messages() %}
    {% for message in messages %}
        <p class="message">{{ message }}</p>
    {% endfor %}
{% endwith %}
CONTENT
</main>
</body>
</html>
"""


def page(content, **context):
    return render_template_string(
        BASE.replace("CONTENT", content), **context
    )


# ---------- REGISTER ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Enter all details. Password must have 8 characters.")
            return redirect(url_for("register"))

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
            """, (
                name, email, generate_password_hash(password)
            ))
            conn.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("This email is already registered.")
            return redirect(url_for("register"))

        finally:
            conn.close()

    content = """
    <div class="card">
    <h2>Create Account</h2>
    <form method="post">
        <label>Full Name</label>
        <input name="name" required>

        <label>Email</label>
        <input type="email" name="email" required>

        <label>Password (minimum 8 characters)</label>
        <input type="password" name="password"
               minlength="8" required>

        <button type="submit">Register</button>
    </form>
    <a href="{{ url_for('login') }}">Back to Login</a>
    </div>
    """
    return page(content)


# ---------- LOGIN ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("""
            SELECT * FROM users WHERE email = ?
        """, (email,)).fetchone()
        conn.close()

        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    content = """
    <div class="card">
    <h2>Welcome Back</h2>
    <p>Login to access student resources.</p>
    <form method="post">
        <label>Email</label>
        <input type="email" name="email" required>

        <label>Password</label>
        <input type="password" name="password" required>

        <button type="submit">Login</button>
    </form>
    <p>New user? <a href="{{ url_for('register') }}">Create Account</a></p>
    </div>
    """
    return page(content)


# ---------- HOME PAGE ----------

@app.route("/")
@login_required
def home():
    content = """
    <div class="card">
        <h1>Welcome, {{ session.get('user_name') }}!</h1>
        <p>Find the resources you need in one place.</p>
        <p>Browse mess facilities, hostels, rental rooms
           and libraries.</p>
        <a class="btn" href="{{ url_for('search') }}">
            Explore Services
        </a>
    </div>
    """
    return page(content)


# ---------- SEARCH SERVICES ----------

@app.route("/search")
@login_required
def search():
    category = request.args.get("category", "").strip()
    keyword = request.args.get("keyword", "").strip()

    query = "SELECT * FROM resources WHERE 1=1"
    values = []

    if category:
        query += " AND category = ?"
        values.append(category)

    if keyword:
        query += " AND (name LIKE ? OR location LIKE ?)"
        values.extend(["%" + keyword + "%", "%" + keyword + "%"])

    query += " ORDER BY name"

    conn = get_db()
    resources = conn.execute(query, values).fetchall()
    conn.close()

    content = """
    <h2>Search Services</h2>
    <div class="card">
    <form method="get">
        <input name="keyword" placeholder="Search name or location"
               value="{{ keyword }}">

        <select name="category">
            <option value="">All Categories</option>
            {% for c in ['mess','hostel','rental','library'] %}
            <option value="{{ c }}"
                {% if category == c %}selected{% endif %}>
                {{ c.title() }}
            </option>
            {% endfor %}
        </select>

        <button type="submit">Search</button>
    </form>
    </div>

    <div class="grid">
    {% for r in resources %}
        <div class="card">
            <h3>{{ r['name'] }}</h3>
            <p>Category: {{ r['category'] }}</p>
            <p>Location: {{ r['location'] }}</p>
            <p class="price">Price: ₹{{ r['price'] }}</p>
            <a class="btn"
               href="{{ url_for('details',
                                resource_id=r['resource_id']) }}">
                View Details
            </a>
        </div>
    {% else %}
        <p>No matching services found.</p>
    {% endfor %}
    </div>
    """
    return page(
        content, resources=resources,
        category=category, keyword=keyword
    )


# ---------- RESOURCE DETAILS ----------

@app.route("/resource/<int:resource_id>")
@login_required
def details(resource_id):
    conn = get_db()
    resource = conn.execute("""
        SELECT * FROM resources WHERE resource_id = ?
    """, (resource_id,)).fetchone()
    conn.close()

    if resource is None:
        abort(404)

    content = """
    <div class="card">
        <h1>{{ resource['name'] }}</h1>
        <p>Category: {{ resource['category'] }}</p>
        <p>Location: {{ resource['location'] }}</p>
        <p class="price">Price: ₹{{ resource['price'] }}</p>
        <p>{{ resource['description'] }}</p>
        <a class="btn" href="{{ url_for('search') }}">
            Back to Services
        </a>
    </div>
    """
    return page(content, resource=resource)


# ---------- LOGOUT ----------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- START APPLICATION ----------

init_db()

if __name__ == "__main__":
    app.run(debug=True)
