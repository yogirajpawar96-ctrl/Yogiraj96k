import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, g, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from database import get_db, close_db, query_db, execute_db

app = Flask(__name__)
app.config.from_object(Config)

# Register database teardown
app.teardown_appcontext(close_db)

# -------------------------------------------------------------
# AUTHENTICATION HELPERS & DECORATORS
# -------------------------------------------------------------
def get_current_user():
    """Returns current logged-in user dict or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return query_db("SELECT * FROM users WHERE id = ?", [user_id], one=True)

@app.context_processor
def inject_global_context():
    """Provides global variables to all Jinja2 templates."""
    user = get_current_user()
    
    # Notification badge for providers (count of new inquiries)
    new_inquiries_count = 0
    if user and user['role'] == 'provider':
        row = query_db(
            "SELECT COUNT(*) as count FROM inquiries WHERE provider_id = ? AND status = 'new'", 
            [user['id']], one=True
        )
        new_inquiries_count = row['count'] if row else 0

    # Notification badge for admin (count of pending listings + pending providers)
    admin_pending_count = 0
    if user and user['role'] == 'admin':
        p_listings = query_db("SELECT COUNT(*) as count FROM listings WHERE status = 'pending'", one=True)
        p_providers = query_db("SELECT COUNT(*) as count FROM users WHERE role = 'provider' AND is_verified = 0", one=True)
        admin_pending_count = (p_listings['count'] if p_listings else 0) + (p_providers['count'] if p_providers else 0)

    # Saved listings count for student
    saved_count = 0
    if user and user['role'] == 'student':
        s_row = query_db("SELECT COUNT(*) as count FROM saved_listings WHERE student_id = ?", [user['id']], one=True)
        saved_count = s_row['count'] if s_row else 0

    return {
        'current_user': user,
        'new_inquiries_count': new_inquiries_count,
        'admin_pending_count': admin_pending_count,
        'saved_count': saved_count,
        'config': Config
    }

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for('login', next=request.url))
            user = get_current_user()
            if not user or user['role'] not in allowed_roles:
                flash("You do not have permission to view that page.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# -------------------------------------------------------------
# PUBLIC ROUTES (HOME, SEARCH, LISTING DETAIL, COMPARE, ABOUT)
# -------------------------------------------------------------
@app.route('/')
def index():
    # Fetch featured verified listings
    featured_accommodations = query_db("""
        SELECT l.*, u.business_name,
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating,
               (SELECT COUNT(*) FROM reviews WHERE listing_id = l.id AND status = 'approved') as review_count
        FROM listings l
        JOIN users u ON l.provider_id = u.id
        WHERE l.status = 'approved' AND l.category = 'accommodation'
        ORDER BY l.views_count DESC, l.id DESC LIMIT 3
    """)
    
    featured_messes = query_db("""
        SELECT l.*, u.business_name,
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating,
               (SELECT COUNT(*) FROM reviews WHERE listing_id = l.id AND status = 'approved') as review_count
        FROM listings l
        JOIN users u ON l.provider_id = u.id
        WHERE l.status = 'approved' AND l.category = 'mess'
        ORDER BY l.views_count DESC, l.id DESC LIMIT 3
    """)
    
    featured_libraries = query_db("""
        SELECT l.*, u.business_name,
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating,
               (SELECT COUNT(*) FROM reviews WHERE listing_id = l.id AND status = 'approved') as review_count
        FROM listings l
        JOIN users u ON l.provider_id = u.id
        WHERE l.status = 'approved' AND l.category = 'library'
        ORDER BY l.views_count DESC, l.id DESC LIMIT 3
    """)
    
    # Counts for category cards and stats banner
    stats = {
        'accommodation_count': query_db("SELECT COUNT(*) as count FROM listings WHERE category = 'accommodation' AND status = 'approved'", one=True)['count'],
        'mess_count': query_db("SELECT COUNT(*) as count FROM listings WHERE category = 'mess' AND status = 'approved'", one=True)['count'],
        'library_count': query_db("SELECT COUNT(*) as count FROM listings WHERE category = 'library' AND status = 'approved'", one=True)['count'],
        'students_count': query_db("SELECT COUNT(*) as count FROM users WHERE role = 'student'", one=True)['count'],
        'providers_count': query_db("SELECT COUNT(*) as count FROM users WHERE role = 'provider' AND is_verified = 1", one=True)['count'],
        'reviews_count': query_db("SELECT COUNT(*) as count FROM reviews WHERE status = 'approved'", one=True)['count']
    }
    
    # Recent genuine student reviews for social proof section
    recent_reviews = query_db("""
        SELECT r.*, l.title as listing_title, l.category as listing_category
        FROM reviews r
        JOIN listings l ON r.listing_id = l.id
        WHERE r.status = 'approved'
        ORDER BY r.id DESC LIMIT 4
    """)

    return render_template('index.html', 
                           featured_accommodations=featured_accommodations,
                           featured_messes=featured_messes,
                           featured_libraries=featured_libraries,
                           stats=stats,
                           recent_reviews=recent_reviews)


@app.route('/search')
def search():
    """
    Search & Filter Module:
    Filter services by keyword, category, subcategory, area, city, budget, and sort criteria.
    """
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    subcategory = request.args.get('subcategory', '').strip()
    area = request.args.get('area', '').strip()
    city = request.args.get('city', '').strip()
    max_price = request.args.get('max_price', '').strip()
    amenity = request.args.get('amenity', '').strip()
    sort_by = request.args.get('sort_by', 'popular')

    sql = """
        SELECT l.*, u.business_name,
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating,
               (SELECT COUNT(*) FROM reviews WHERE listing_id = l.id AND status = 'approved') as review_count
        FROM listings l
        JOIN users u ON l.provider_id = u.id
        WHERE l.status = 'approved'
    """
    params = []

    if q:
        sql += " AND (l.title LIKE ? OR l.description LIKE ? OR l.area LIKE ? OR l.city LIKE ? OR l.address LIKE ?)"
        term = f"%{q}%"
        params.extend([term, term, term, term, term])

    if category:
        sql += " AND l.category = ?"
        params.append(category)

    if subcategory:
        sql += " AND l.subcategory = ?"
        params.append(subcategory)

    if area:
        sql += " AND l.area LIKE ?"
        params.append(f"%{area}%")

    if city:
        sql += " AND l.city LIKE ?"
        params.append(f"%{city}%")

    if max_price:
        try:
            sql += " AND l.pricing_amount <= ?"
            params.append(float(max_price))
        except ValueError:
            pass

    if amenity:
        sql += " AND l.amenities LIKE ?"
        params.append(f"%{amenity}%")

    # Sorting
    if sort_by == 'price_asc':
        sql += " ORDER BY l.pricing_amount ASC"
    elif sort_by == 'price_desc':
        sql += " ORDER BY l.pricing_amount DESC"
    elif sort_by == 'rating':
        sql += " ORDER BY avg_rating DESC, review_count DESC"
    elif sort_by == 'newest':
        sql += " ORDER BY l.id DESC"
    else:  # popular
        sql += " ORDER BY l.views_count DESC, avg_rating DESC"

    listings = query_db(sql, params)

    # Get distinct areas and cities for filter dropdowns
    areas = [r['area'] for r in query_db("SELECT DISTINCT area FROM listings WHERE status = 'approved' ORDER BY area")]
    cities = [r['city'] for r in query_db("SELECT DISTINCT city FROM listings WHERE status = 'approved' ORDER BY city")]

    # Get saved listing IDs for current user to show active bookmark icon
    saved_ids = []
    current_u = get_current_user()
    if current_u and current_u['role'] == 'student':
        rows = query_db("SELECT listing_id FROM saved_listings WHERE student_id = ?", [current_u['id']])
        saved_ids = [r['listing_id'] for r in rows]

    return render_template('search.html', 
                           listings=listings, 
                           total_results=len(listings),
                           areas=areas, 
                           cities=cities,
                           saved_ids=saved_ids,
                           filters={
                               'q': q,
                               'category': category,
                               'subcategory': subcategory,
                               'area': area,
                               'city': city,
                               'max_price': max_price,
                               'amenity': amenity,
                               'sort_by': sort_by
                           })


@app.route('/listings/<int:id>')
def listing_detail(id):
    # Increment view count
    execute_db("UPDATE listings SET views_count = views_count + 1 WHERE id = ?", [id])

    # Fetch listing and provider info
    listing = query_db("""
        SELECT l.*, u.name as provider_name, u.business_name, u.email as provider_email, 
               u.phone as provider_phone, u.is_verified as provider_verified
        FROM listings l
        JOIN users u ON l.provider_id = u.id
        WHERE l.id = ?
    """, [id], one=True)

    if not listing:
        flash("Listing not found or has been removed.", "danger")
        return redirect(url_for('search'))

    # If pending and user is not admin or the owner provider, block view
    curr = get_current_user()
    if listing['status'] != 'approved':
        if not curr or (curr['role'] != 'admin' and curr['id'] != listing['provider_id']):
            flash("This listing is currently under admin verification.", "warning")
            return redirect(url_for('search'))

    # Reviews and ratings
    reviews = query_db("""
        SELECT * FROM reviews 
        WHERE listing_id = ? AND status = 'approved' 
        ORDER BY id DESC
    """, [id])

    rating_stats = query_db("""
        SELECT 
            COUNT(*) as total_reviews,
            COALESCE(AVG(rating), 0) as avg_rating,
            SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as stars_5,
            SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as stars_4,
            SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as stars_3,
            SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as stars_2,
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as stars_1
        FROM reviews
        WHERE listing_id = ? AND status = 'approved'
    """, [id], one=True)

    # Check if student already saved this listing
    is_saved = False
    has_reviewed = False
    if curr and curr['role'] == 'student':
        saved_row = query_db("SELECT id FROM saved_listings WHERE student_id = ? AND listing_id = ?", 
                             [curr['id'], id], one=True)
        is_saved = bool(saved_row)
        rev_row = query_db("SELECT id FROM reviews WHERE student_id = ? AND listing_id = ?", 
                           [curr['id'], id], one=True)
        has_reviewed = bool(rev_row)

    # Similar/related services
    similar_listings = query_db("""
        SELECT l.*, 
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating
        FROM listings l
        WHERE l.id != ? AND l.category = ? AND l.status = 'approved'
        ORDER BY l.views_count DESC LIMIT 3
    """, [id, listing['category']])

    # Amenities list parsing
    amenities_list = [a.strip() for a in (listing['amenities'] or '').split(',') if a.strip()]

    return render_template('listing_detail.html', 
                           listing=listing, 
                           reviews=reviews, 
                           rating_stats=rating_stats,
                           is_saved=is_saved,
                           has_reviewed=has_reviewed,
                           amenities_list=amenities_list,
                           similar_listings=similar_listings)


@app.route('/listings/<int:id>/review', methods=['POST'])
@login_required
@role_required(['student'])
def submit_review(id):
    student = get_current_user()
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash("Please provide a valid star rating between 1 and 5.", "danger")
        return redirect(url_for('listing_detail', id=id))

    if not comment:
        flash("Please write a constructive comment about your experience.", "danger")
        return redirect(url_for('listing_detail', id=id))

    # Check if student already reviewed this listing
    existing = query_db("SELECT id FROM reviews WHERE listing_id = ? AND student_id = ?", [id, student['id']], one=True)
    if existing:
        execute_db("""
            UPDATE reviews SET rating = ?, comment = ?, status = 'approved', created_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [rating, comment, existing['id']])
        flash("Your review has been updated successfully!", "success")
    else:
        execute_db("""
            INSERT INTO reviews (listing_id, student_id, student_name, rating, comment, status)
            VALUES (?, ?, ?, ?, ?, 'approved')
        """, [id, student['id'], student['name'], rating, comment])
        flash("Thank you! Your verified student review was posted successfully.", "success")

    return redirect(url_for('listing_detail', id=id))


@app.route('/listings/<int:id>/inquire', methods=['POST'])
@login_required
@role_required(['student'])
def submit_inquiry(id):
    student = get_current_user()
    listing = query_db("SELECT * FROM listings WHERE id = ?", [id], one=True)
    if not listing:
        flash("Listing not found.", "danger")
        return redirect(url_for('search'))

    message = request.form.get('message', '').strip()
    phone = request.form.get('phone', student.get('phone', '')).strip()
    move_in_date = request.form.get('move_in_date', '').strip()

    if not message:
        flash("Please write a message detailing your inquiry or requirements.", "danger")
        return redirect(url_for('listing_detail', id=id))

    execute_db("""
        INSERT INTO inquiries (listing_id, student_id, provider_id, student_name, student_email, student_phone, message, move_in_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')
    """, [id, student['id'], listing['provider_id'], student['name'], student['email'], phone, message, move_in_date])

    flash("Inquiry sent successfully to the service provider! They will contact you shortly.", "success")
    return redirect(url_for('listing_detail', id=id))


@app.route('/listings/<int:id>/bookmark', methods=['POST'])
@login_required
@role_required(['student'])
def toggle_bookmark(id):
    student = get_current_user()
    existing = query_db("SELECT id FROM saved_listings WHERE student_id = ? AND listing_id = ?", 
                        [student['id'], id], one=True)
    
    if existing:
        execute_db("DELETE FROM saved_listings WHERE id = ?", [existing['id']])
        is_saved = False
        message = "Removed from your saved services."
    else:
        execute_db("INSERT INTO saved_listings (student_id, listing_id) VALUES (?, ?)", [student['id'], id])
        is_saved = True
        message = "Saved to your bookmarks!"

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'is_saved': is_saved, 'message': message})
    
    flash(message, "info")
    return redirect(request.referrer or url_for('listing_detail', id=id))


@app.route('/compare')
def compare():
    """
    Side-by-side comparison feature to solve Problem Statement:
    'Difficulty comparing available options'
    """
    raw_ids = request.args.get('ids', '')
    id_list = []
    for item in raw_ids.split(','):
        item = item.strip()
        if item.isdigit():
            id_list.append(int(item))
            
    # Max 4 items comparison
    id_list = id_list[:4]
    
    listings = []
    if id_list:
        placeholders = ','.join(['?'] * len(id_list))
        listings = query_db(f"""
            SELECT l.*, u.business_name,
                   COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating,
                   (SELECT COUNT(*) FROM reviews WHERE listing_id = l.id AND status = 'approved') as review_count
            FROM listings l
            JOIN users u ON l.provider_id = u.id
            WHERE l.id IN ({placeholders}) AND l.status = 'approved'
        """, id_list)

    all_available = query_db("""
        SELECT id, title, category, pricing_amount, area 
        FROM listings WHERE status = 'approved' ORDER BY title ASC
    """)

    return render_template('compare.html', listings=listings, all_available=all_available, selected_ids=id_list)


@app.route('/about')
def about():
    return render_template('about.html')


# -------------------------------------------------------------
# AUTHENTICATION MODULE (LOGIN, LOGOUT, REGISTRATION)
# -------------------------------------------------------------
@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = query_db("SELECT * FROM users WHERE email = ?", [email], one=True)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = user['name']

            flash(f"Welcome back, {user['name']}!", "success")
            
            # Smart redirect based on user role
            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'provider':
                return redirect(url_for('provider_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash("Invalid email address or password. Please try again.", "danger")

    return render_template('auth/login.html')


@app.route('/auth/quick-login/<role>')
def quick_login(role):
    """
    Convenient one-click demonstrator login for evaluator / viva demo.
    Allows testing Student, Provider, and Admin roles instantly.
    """
    email_map = {
        'admin': 'admin@studentportal.com',
        'provider': 'ramesh@sharmaproperties.com',
        'student': 'yogiraj@student.com'
    }
    target_email = email_map.get(role)
    if target_email:
        user = query_db("SELECT * FROM users WHERE email = ?", [target_email], one=True)
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = user['name']
            flash(f"Quick Demo: Signed in as {user['name']} ({user['role'].capitalize()})", "success")
            
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'provider':
                return redirect(url_for('provider_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
                
    flash("Demo account not found.", "warning")
    return redirect(url_for('login'))


@app.route('/auth/register-student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        college_name = request.form.get('college_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash("Please fill in all mandatory fields.", "danger")
            return render_template('auth/register_student.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register_student.html')

        existing = query_db("SELECT id FROM users WHERE email = ?", [email], one=True)
        if existing:
            flash("An account with this email already exists. Please login instead.", "warning")
            return redirect(url_for('login'))

        password_hash = generate_password_hash(password)
        new_id = execute_db("""
            INSERT INTO users (role, name, email, phone, password_hash, college_name, is_verified)
            VALUES ('student', ?, ?, ?, ?, ?, 1)
        """, [name, email, phone, password_hash, college_name], return_id=True)

        session['user_id'] = new_id
        session['role'] = 'student'
        session['user_name'] = name

        flash("Student account created successfully! Welcome to the portal.", "success")
        return redirect(url_for('student_dashboard'))

    return render_template('auth/register_student.html')


@app.route('/auth/register-provider', methods=['GET', 'POST'])
def register_provider():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        business_name = request.form.get('business_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not business_name or not email or not password:
            flash("Please fill in all mandatory fields.", "danger")
            return render_template('auth/register_provider.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register_provider.html')

        existing = query_db("SELECT id FROM users WHERE email = ?", [email], one=True)
        if existing:
            flash("An account with this email already exists.", "warning")
            return redirect(url_for('login'))

        password_hash = generate_password_hash(password)
        new_id = execute_db("""
            INSERT INTO users (role, name, email, phone, password_hash, business_name, address, is_verified)
            VALUES ('provider', ?, ?, ?, ?, ?, ?, 0)
        """, [name, email, phone, password_hash, business_name, address], return_id=True)

        session['user_id'] = new_id
        session['role'] = 'provider'
        session['user_name'] = name

        flash("Provider registration submitted! Your account is pending admin verification.", "info")
        return redirect(url_for('provider_dashboard'))

    return render_template('auth/register_provider.html')


@app.route('/auth/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('index'))


# -------------------------------------------------------------
# STUDENT DASHBOARD MODULE
# -------------------------------------------------------------
@app.route('/student/dashboard')
@login_required
@role_required(['student'])
def student_dashboard():
    student = get_current_user()

    # Saved listings
    saved_listings = query_db("""
        SELECT l.*, u.business_name,
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating
        FROM saved_listings sl
        JOIN listings l ON sl.listing_id = l.id
        JOIN users u ON l.provider_id = u.id
        WHERE sl.student_id = ?
        ORDER BY sl.id DESC
    """, [student['id']])

    # Inquiries sent by student
    my_inquiries = query_db("""
        SELECT i.*, l.title as listing_title, l.category as listing_category,
               u.business_name as provider_business, u.phone as provider_phone
        FROM inquiries i
        JOIN listings l ON i.listing_id = l.id
        JOIN users u ON i.provider_id = u.id
        WHERE i.student_id = ?
        ORDER BY i.id DESC
    """, [student['id']])

    # Reviews posted by student
    my_reviews = query_db("""
        SELECT r.*, l.title as listing_title, l.category as listing_category
        FROM reviews r
        JOIN listings l ON r.listing_id = l.id
        WHERE r.student_id = ?
        ORDER BY r.id DESC
    """, [student['id']])

    return render_template('student/dashboard.html',
                           student=student,
                           saved_listings=saved_listings,
                           my_inquiries=my_inquiries,
                           my_reviews=my_reviews)


# -------------------------------------------------------------
# PROVIDER DASHBOARD MODULE
# -------------------------------------------------------------
@app.route('/provider/dashboard')
@login_required
@role_required(['provider'])
def provider_dashboard():
    provider = get_current_user()

    listings = query_db("""
        SELECT l.*,
               COALESCE((SELECT AVG(rating) FROM reviews WHERE listing_id = l.id AND status = 'approved'), 0) as avg_rating,
               (SELECT COUNT(*) FROM reviews WHERE listing_id = l.id AND status = 'approved') as review_count,
               (SELECT COUNT(*) FROM inquiries WHERE listing_id = l.id) as inquiry_count
        FROM listings l
        WHERE l.provider_id = ?
        ORDER BY l.id DESC
    """, [provider['id']])

    stats = {
        'total_listings': len(listings),
        'approved_listings': sum(1 for item in listings if item['status'] == 'approved'),
        'pending_listings': sum(1 for item in listings if item['status'] == 'pending'),
        'total_views': sum(item['views_count'] for item in listings),
        'total_inquiries': query_db("SELECT COUNT(*) as count FROM inquiries WHERE provider_id = ?", [provider['id']], one=True)['count']
    }

    recent_inquiries = query_db("""
        SELECT i.*, l.title as listing_title
        FROM inquiries i
        JOIN listings l ON i.listing_id = l.id
        WHERE i.provider_id = ?
        ORDER BY i.id DESC LIMIT 5
    """, [provider['id']])

    return render_template('provider/dashboard.html',
                           provider=provider,
                           listings=listings,
                           stats=stats,
                           recent_inquiries=recent_inquiries)


@app.route('/provider/add-listing', methods=['GET', 'POST'])
@login_required
@role_required(['provider'])
def add_listing():
    provider = get_current_user()
    
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        subcategory = request.form.get('subcategory', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        area = request.form.get('area', '').strip()
        landmark = request.form.get('landmark', '').strip()
        contact_phone = request.form.get('contact_phone', provider.get('phone', '')).strip()
        contact_email = request.form.get('contact_email', provider.get('email', '')).strip()
        pricing_amount = request.form.get('pricing_amount', 0, type=float)
        pricing_period = request.form.get('pricing_period', 'Per Month').strip()
        deposit_amount = request.form.get('deposit_amount', 0.0, type=float)
        capacity_or_beds = request.form.get('capacity_or_beds', '').strip()
        timings = request.form.get('timings', '').strip()
        menu_details = request.form.get('menu_details', '').strip()
        amenities = request.form.get('amenities', '').strip()
        rules = request.form.get('rules', '').strip()
        image_url = request.form.get('image_url', '').strip()

        # Fallback image based on category if empty
        if not image_url:
            if category == 'accommodation':
                image_url = 'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=1000&q=80'
            elif category == 'mess':
                image_url = 'https://images.unsplash.com/photo-1613292443284-c7742d4a1380?auto=format&fit=crop&w=1000&q=80'
            else:
                image_url = 'https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1000&q=80'

        if not title or not category or not pricing_amount or not address or not area:
            flash("Please fill in all mandatory service details.", "danger")
            return render_template('provider/add_listing.html')

        new_id = execute_db("""
            INSERT INTO listings (
                provider_id, category, subcategory, title, description, address, city, area, landmark,
                contact_phone, contact_email, pricing_amount, pricing_period, deposit_amount,
                capacity_or_beds, timings, menu_details, amenities, rules, image_url, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, [
            provider['id'], category, subcategory, title, description, address, city, area, landmark,
            contact_phone, contact_email, pricing_amount, pricing_period, deposit_amount,
            capacity_or_beds, timings, menu_details, amenities, rules, image_url
        ], return_id=True)

        flash("Listing submitted successfully! It is queued for admin approval.", "success")
        return redirect(url_for('provider_dashboard'))

    return render_template('provider/add_listing.html', provider=provider)


@app.route('/provider/edit-listing/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required(['provider'])
def edit_listing(id):
    provider = get_current_user()
    listing = query_db("SELECT * FROM listings WHERE id = ? AND provider_id = ?", [id, provider['id']], one=True)
    if not listing:
        flash("Listing not found or unauthorized.", "danger")
        return redirect(url_for('provider_dashboard'))

    if request.method == 'POST':
        subcategory = request.form.get('subcategory', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        area = request.form.get('area', '').strip()
        landmark = request.form.get('landmark', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        contact_email = request.form.get('contact_email', '').strip()
        pricing_amount = request.form.get('pricing_amount', 0, type=float)
        pricing_period = request.form.get('pricing_period', 'Per Month').strip()
        deposit_amount = request.form.get('deposit_amount', 0.0, type=float)
        capacity_or_beds = request.form.get('capacity_or_beds', '').strip()
        timings = request.form.get('timings', '').strip()
        menu_details = request.form.get('menu_details', '').strip()
        amenities = request.form.get('amenities', '').strip()
        rules = request.form.get('rules', '').strip()
        image_url = request.form.get('image_url', '').strip()

        execute_db("""
            UPDATE listings SET
                subcategory = ?, title = ?, description = ?, address = ?, city = ?, area = ?, landmark = ?,
                contact_phone = ?, contact_email = ?, pricing_amount = ?, pricing_period = ?, deposit_amount = ?,
                capacity_or_beds = ?, timings = ?, menu_details = ?, amenities = ?, rules = ?, image_url = ?
            WHERE id = ? AND provider_id = ?
        """, [
            subcategory, title, description, address, city, area, landmark,
            contact_phone, contact_email, pricing_amount, pricing_period, deposit_amount,
            capacity_or_beds, timings, menu_details, amenities, rules, image_url,
            id, provider['id']
        ])

        flash("Listing updated successfully!", "success")
        return redirect(url_for('provider_dashboard'))

    return render_template('provider/edit_listing.html', listing=listing)


@app.route('/provider/delete-listing/<int:id>', methods=['POST'])
@login_required
@role_required(['provider'])
def delete_listing(id):
    provider = get_current_user()
    execute_db("DELETE FROM listings WHERE id = ? AND provider_id = ?", [id, provider['id']])
    flash("Listing deleted successfully.", "info")
    return redirect(url_for('provider_dashboard'))


@app.route('/provider/inquiries')
@login_required
@role_required(['provider'])
def provider_inquiries():
    provider = get_current_user()
    inquiries = query_db("""
        SELECT i.*, l.title as listing_title, l.category as listing_category
        FROM inquiries i
        JOIN listings l ON i.listing_id = l.id
        WHERE i.provider_id = ?
        ORDER BY i.id DESC
    """, [provider['id']])

    return render_template('provider/inquiries.html', inquiries=inquiries)


@app.route('/provider/inquiries/<int:id>/status', methods=['POST'])
@login_required
@role_required(['provider'])
def update_inquiry_status(id):
    provider = get_current_user()
    status = request.form.get('status', 'contacted')
    execute_db("UPDATE inquiries SET status = ? WHERE id = ? AND provider_id = ?", [status, id, provider['id']])
    flash(f"Inquiry marked as '{status}'.", "success")
    return redirect(url_for('provider_inquiries'))


# -------------------------------------------------------------
# ADMINISTRATOR MODULE (VERIFICATION, MODERATION, AUDITING)
# -------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    stats = {
        'total_users': query_db("SELECT COUNT(*) as count FROM users", one=True)['count'],
        'total_students': query_db("SELECT COUNT(*) as count FROM users WHERE role = 'student'", one=True)['count'],
        'total_providers': query_db("SELECT COUNT(*) as count FROM users WHERE role = 'provider'", one=True)['count'],
        'pending_providers': query_db("SELECT COUNT(*) as count FROM users WHERE role = 'provider' AND is_verified = 0", one=True)['count'],
        'total_listings': query_db("SELECT COUNT(*) as count FROM listings", one=True)['count'],
        'pending_listings': query_db("SELECT COUNT(*) as count FROM listings WHERE status = 'pending'", one=True)['count'],
        'approved_listings': query_db("SELECT COUNT(*) as count FROM listings WHERE status = 'approved'", one=True)['count'],
        'total_reviews': query_db("SELECT COUNT(*) as count FROM reviews", one=True)['count'],
        'total_inquiries': query_db("SELECT COUNT(*) as count FROM inquiries", one=True)['count']
    }

    pending_listings = query_db("""
        SELECT l.*, u.business_name, u.name as provider_name, u.phone as provider_phone
        FROM listings l
        JOIN users u ON l.provider_id = u.id
        WHERE l.status = 'pending'
        ORDER BY l.id DESC
    """)

    pending_providers = query_db("""
        SELECT * FROM users
        WHERE role = 'provider' AND is_verified = 0
        ORDER BY id DESC
    """)

    recent_reviews = query_db("""
        SELECT r.*, l.title as listing_title, u.email as student_email
        FROM reviews r
        JOIN listings l ON r.listing_id = l.id
        JOIN users u ON r.student_id = u.id
        ORDER BY r.id DESC LIMIT 6
    """)

    return render_template('admin/dashboard.html',
                           stats=stats,
                           pending_listings=pending_listings,
                           pending_providers=pending_providers,
                           recent_reviews=recent_reviews)


@app.route('/admin/listings')
@login_required
@role_required(['admin'])
def admin_listings():
    status_filter = request.args.get('status', 'all')
    if status_filter == 'all':
        listings = query_db("""
            SELECT l.*, u.business_name, u.name as provider_name
            FROM listings l
            JOIN users u ON l.provider_id = u.id
            ORDER BY l.id DESC
        """)
    else:
        listings = query_db("""
            SELECT l.*, u.business_name, u.name as provider_name
            FROM listings l
            JOIN users u ON l.provider_id = u.id
            WHERE l.status = ?
            ORDER BY l.id DESC
        """, [status_filter])

    return render_template('admin/verify_listings.html', listings=listings, current_status=status_filter)


@app.route('/admin/listings/<int:id>/status', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_update_listing_status(id):
    status = request.form.get('status')
    if status in ['approved', 'rejected', 'pending']:
        execute_db("UPDATE listings SET status = ? WHERE id = ?", [status, id])
        flash(f"Listing #{id} status changed to '{status}'.", "success")
    return redirect(request.referrer or url_for('admin_listings'))


@app.route('/admin/listings/<int:id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_delete_listing(id):
    execute_db("DELETE FROM listings WHERE id = ?", [id])
    flash(f"Listing #{id} permanently deleted.", "info")
    return redirect(request.referrer or url_for('admin_listings'))


@app.route('/admin/providers')
@login_required
@role_required(['admin'])
def admin_providers():
    providers = query_db("""
        SELECT u.*, 
               (SELECT COUNT(*) FROM listings WHERE provider_id = u.id) as listing_count
        FROM users u
        WHERE u.role = 'provider'
        ORDER BY u.id DESC
    """)
    return render_template('admin/verify_providers.html', providers=providers)


@app.route('/admin/providers/<int:id>/verify', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_verify_provider(id):
    action = request.form.get('action') # 'approve' or 'reject'
    val = 1 if action == 'approve' else 2
    execute_db("UPDATE users SET is_verified = ? WHERE id = ? AND role = 'provider'", [val, id])
    flash(f"Provider status updated to {'Verified' if val == 1 else 'Rejected'}.", "success")
    return redirect(url_for('admin_providers'))


@app.route('/admin/reviews')
@login_required
@role_required(['admin'])
def admin_reviews():
    reviews = query_db("""
        SELECT r.*, l.title as listing_title, l.id as listing_id, u.email as student_email
        FROM reviews r
        JOIN listings l ON r.listing_id = l.id
        JOIN users u ON r.student_id = u.id
        ORDER BY r.id DESC
    """)
    return render_template('admin/manage_reviews.html', reviews=reviews)


@app.route('/admin/reviews/<int:id>/status', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_update_review_status(id):
    action = request.form.get('action')
    if action == 'delete':
        execute_db("DELETE FROM reviews WHERE id = ?", [id])
        flash(f"Review #{id} was deleted.", "info")
    elif action in ['approved', 'flagged', 'hidden']:
        execute_db("UPDATE reviews SET status = ? WHERE id = ?", [action, id])
        flash(f"Review #{id} status updated to '{action}'.", "success")
    return redirect(url_for('admin_reviews'))


@app.route('/admin/users')
@login_required
@role_required(['admin'])
def admin_users():
    users = query_db("SELECT * FROM users ORDER BY role, id DESC")
    return render_template('admin/manage_users.html', users=users)


if __name__ == '__main__':
    # Initialize DB if not already created
    if not os.path.exists(Config.SQLITE_PATH):
        from init_db import init_database
        init_database()
        
    print(f"[*] Starting Student Resources Management System on http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
