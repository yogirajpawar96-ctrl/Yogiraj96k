import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import Config

def init_database():
    db_path = Config.SQLITE_PATH
    print(f"[*] Initializing database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Create Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL DEFAULT 'student',
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT NOT NULL,
        college_name TEXT,
        business_name TEXT,
        address TEXT,
        is_verified INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Create Listings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        provider_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        address TEXT NOT NULL,
        city TEXT NOT NULL,
        area TEXT NOT NULL,
        landmark TEXT,
        contact_phone TEXT NOT NULL,
        contact_email TEXT,
        pricing_amount REAL NOT NULL,
        pricing_period TEXT DEFAULT 'Per Month',
        deposit_amount REAL DEFAULT 0.0,
        capacity_or_beds TEXT,
        timings TEXT,
        menu_details TEXT,
        amenities TEXT,
        rules TEXT,
        image_url TEXT,
        status TEXT DEFAULT 'pending',
        views_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 3. Create Reviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
        comment TEXT NOT NULL,
        status TEXT DEFAULT 'approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 4. Create Inquiries Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        provider_id INTEGER NOT NULL,
        student_name TEXT NOT NULL,
        student_email TEXT NOT NULL,
        student_phone TEXT,
        message TEXT NOT NULL,
        move_in_date TEXT,
        status TEXT DEFAULT 'new',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 5. Create Saved Listings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        listing_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (student_id, listing_id),
        FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
    );
    """)

    conn.commit()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        print("[*] Seeding default users, verified services, and sample reviews...")

        # Default Users
        users_data = [
            # Admin
            ('admin', 'Administrator (Head)', 'admin@studentportal.com', '9876543210', 
             generate_password_hash('admin123'), None, 'Campus Central Admin', 'College Campus, Pune', 1),
            # Providers
            ('provider', 'Ramesh Sharma', 'ramesh@sharmaproperties.com', '9822011223', 
             generate_password_hash('provider123'), None, 'Sharma Hostels & PG Living', 'Deccan Gymkhana, FC Road, Pune', 1),
            ('provider', 'Sunita Deshmukh', 'sunita@annapurnamess.com', '9850022334', 
             generate_password_hash('provider123'), None, 'Annapurna Bhojanalaya & Mess', 'Near Garware College, Karve Road, Pune', 1),
            ('provider', 'Mahesh Kulkarni', 'mahesh@vidyalibrary.com', '9881144556', 
             generate_password_hash('provider123'), None, 'Vidya 24/7 Digital Study Lounge', 'Fergusson College Road, Shivajinagar, Pune', 1),
            ('provider', 'Vikram Patil', 'vikram@patilresidency.com', '9765432109', 
             generate_password_hash('provider123'), None, 'Patil Premium Student Rooms', 'Gangapur Road, Nashik', 0), # Pending verification
            # Students
            ('student', 'Yogiraj Pawar', 'yogiraj@student.com', '9403312345', 
             generate_password_hash('student123'), 'Commerce Management and Computer Science College', None, None, 1),
            ('student', 'Onkar Shinde', 'onkar@student.com', '9422054321', 
             generate_password_hash('student123'), 'Commerce Management and Computer Science College', None, None, 1),
            ('student', 'Snehal More', 'snehal@student.com', '9123456780', 
             generate_password_hash('student123'), 'Fergusson College Pune', None, None, 1)
        ]

        cursor.executemany("""
        INSERT INTO users (role, name, email, phone, password_hash, college_name, business_name, address, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, users_data)
        conn.commit()

        # Seed Listings
        # Provider 2 = Ramesh Sharma (id=2), Provider 3 = Sunita Deshmukh (id=3), Provider 4 = Mahesh Kulkarni (id=4)
        listings_data = [
            # 1. Hostel / PG (Accommodation)
            (
                2, 'accommodation', 'PG & Hostel',
                'Sai Comfort Deluxe Boys PG & Hostel',
                'Well-maintained, fully furnished student hostel offering high-speed WiFi, attached bathrooms, RO drinking water, 24/7 CCTV surveillance, and daily housekeeping. Walking distance from major colleges and bus stops.',
                'Plot 42, Ghole Road, Near FC Road', 'Pune', 'Shivajinagar', 'Opposite British Library',
                '9822011223', 'ramesh@sharmaproperties.com',
                6500.0, 'Per Month', 5000.0, '2 & 3 Sharing Available',
                'Gate Closes at 10:30 PM', '',
                'High-Speed Wi-Fi, 24/7 Hot Water (Solar), RO Water Purifier, Daily Housekeeping, CCTV Security, Biometric Access, Study Table & Chair, Individual Wooden Wardrobe, Power Backup',
                'Smoking and alcohol strictly prohibited. Visiting hours: 5:00 PM to 8:00 PM in the reception lounge.',
                'https://images.unsplash.com/photo-1555854877-bab0e564b8d5?auto=format&fit=crop&w=1000&q=80',
                'approved', 142
            ),
            # 2. Girls PG (Accommodation)
            (
                2, 'accommodation', 'Girls PG',
                'Greenfield Luxury Girls Residency & PG',
                'Safe, premium, and homely accommodation exclusively for female students. Located in a secure gated community with 24/7 female warden, biometric security, biometric gate, and healthy vegetarian breakfast and dinner included.',
                'B-Wing, Mayur Colony, Near MIT Campus', 'Pune', 'Kothrud', 'Behind Joggers Park',
                '9822011223', 'ramesh@sharmaproperties.com',
                7800.0, 'Per Month', 6000.0, 'Single & 2 Sharing Rooms',
                'Gate Closes at 10:00 PM', '',
                'Food Included (Breakfast & Dinner), Air Conditioning Option, High-Speed Wi-Fi, Automatic Washing Machine, Microwave & Fridge Access, 24/7 Security & CCTV, Attached Balcony, Lift',
                'College ID required at check-in. Curfew 10:00 PM strictly followed.',
                'https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=1000&q=80',
                'approved', 215
            ),
            # 3. Rental Flat / Student Room
            (
                2, 'accommodation', 'Student Flat / Room',
                'Scholars Haven 2BHK Furnished Student Sharing',
                'Spacious 2BHK flat furnished specifically for college students with separate study zones, modular kitchen with gas connection, refrigerator, high-speed fiber internet, and quiet study-friendly environment.',
                'Row House 5, Hermes Heritage, Lane 6', 'Pune', 'Viman Nagar', 'Near Symbiosis Campus',
                '9822011223', 'ramesh@sharmaproperties.com',
                8500.0, 'Per Month', 8000.0, '4 Students Capacity (2 per room)',
                'No Curfew (Self Key Access)', '',
                'Modular Kitchen, High-Speed Wi-Fi, Refrigerator, Geyser, Inverter Backup, Water Purifier, Two Wheeler Parking, Separate Study Desks',
                'Quiet hours from 11:00 PM to 6:00 AM.',
                'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1000&q=80',
                'approved', 98
            ),
            # 4. Mess Services - Maharashtrian & North Indian
            (
                3, 'mess', 'Pure Veg Mess',
                'Annapurna Deluxe Homely Pure Veg Mess',
                'Hygienic, freshly cooked home-style Maharashtrian and North Indian meals. Unlimited chapatis, 2 fresh seasonal vegetables, dal tadka, steamed basmati rice, salad, and pickle. Special Sunday Feast with sweet/Gulab Jamun.',
                'Shop 12, Golden Arcade, Karve Road', 'Pune', 'Kothrud', 'Opposite Garware College',
                '9850022334', 'sunita@annapurnamess.com',
                3200.0, 'Per Month', 500.0, 'Capacity: 120 Students / Shift',
                'Lunch: 11:30 AM - 3:00 PM | Dinner: 7:30 PM - 10:30 PM',
                'Daily Menu: 4 Fresh Chapatis (Unlimited option available), 2 Subzis (Dry & Gravy), Dal Tadka/Kadhi, Steamed Rice, Salad, Chutney, Pickle. Sunday Special: Paneer Masala, Puran Poli / Gulab Jamun, Veg Pulao.',
                'Hygienic Stainless Steel Utensils, RO Filtered Drinking Water, Tiffin / Dabba Delivery Available, Free Trial Meal for New Admissions, Air Conditioned Dining Hall, Weekly Sweet & Special Dish',
                'Meal coupons valid for 30 days. Prior notice of 2 hours needed for packed tiffin.',
                'https://images.unsplash.com/photo-1613292443284-c7742d4a1380?auto=format&fit=crop&w=1000&q=80',
                'approved', 380
            ),
            # 5. Mess Services - Multi-Cuisine Veg & Non-Veg
            (
                3, 'mess', 'Veg & Non-Veg Mess',
                'Royal Swad Multi-Cuisine Student Dining & Tiffin',
                'Balanced nutritious meal plan for students. Pure vegetarian food served daily, with authentic Chicken and Egg curry served 3 times a week (Wed, Fri, Sun) for non-veg lovers. Tiffin delivery to nearby hostels and PGs.',
                'Fergusson College Road, Lane 2', 'Pune', 'Shivajinagar', 'Near Goodluck Cafe',
                '9850022334', 'sunita@annapurnamess.com',
                3600.0, 'Per Month', 500.0, 'Capacity: 80 Students',
                'Lunch: 12:00 PM - 3:30 PM | Dinner: 7:30 PM - 11:00 PM',
                'Mon/Tue/Thu/Sat: Veg Feast (Chapatis, Dal Fry, Jeera Rice, Paneer/Mix Veg, Salad). Wed/Fri/Sun: Non-Veg Special (Chicken Sukka / Egg Curry) along with parallel vegetarian menu option.',
                'Separate Veg & Non-Veg Cooking Sections, Delivery to Hostels, Digital Payment Accepted, Unlimited Rice & Roti, Clean Handwash Stations',
                'Subscribers can pause plan up to 5 days during exams/vacation.',
                'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=1000&q=80',
                'approved', 290
            ),
            # 6. Private Library - 24/7 Digital Reading Room
            (
                4, 'library', '24/7 AC Study Library',
                'Vidya 24/7 Air-Conditioned Silent Study Library',
                'State-of-the-art modern air-conditioned private library and reading lounge built for serious academic, UPSC, MPSC, CA, and college examinations. Individual partitioned wooden cubicles, ergonomic mesh chairs, and dedicated charging sockets.',
                '3rd Floor, Shreenath Plaza, Dnyaneshwar Paduka Chowk, FC Road', 'Pune', 'Shivajinagar', 'Above Bank of Maharashtra',
                '9881144556', 'mahesh@vidyalibrary.com',
                1100.0, 'Per Month', 300.0, '150 Individual Study Cubicles',
                'Open 24 Hours, 7 Days a Week (365 Days)', '',
                'Individual Charging Socket & USB Port at every desk, High-Speed Dual-Band Wi-Fi (300 Mbps), Silent Dual Inverter AC, Ergonomic High-Back Chairs, Personal Locker Facility, RO Cold & Warm Water, Daily English & Marathi Newspapers, Tea/Coffee Vending Machine, Discussion Room',
                'Strict silence zone. Cell phones must remain on silent mode. No phone conversations allowed inside study hall.',
                'https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1000&q=80',
                'approved', 420
            ),
            # 7. Private Library - Abhyasika Reading Hall
            (
                4, 'library', 'Digital Abhyasika & Library',
                'Saraswati Central Digital Study Abhyasika',
                'Peaceful and affordable reading hall with natural ventilation, LED reading lights, clean restrooms, and reserve seating for semester exam preparations.',
                'Near Karve Statue, Kothrud', 'Pune', 'Kothrud', 'Near Kothrud Bus Stand',
                '9881144556', 'mahesh@vidyalibrary.com',
                850.0, 'Per Month', 200.0, '90 Reserved Seats',
                '6:00 AM - 11:30 PM (Daily)', '',
                'Power Sockets, High-Speed Wi-Fi, Water Dispenser, Safe Parking, CCTV Surveillance, Magazine Section, Locker Storage',
                'No reservation without monthly pass. Footwear to be kept on shoe racks.',
                'https://images.unsplash.com/photo-1497633762265-9d179a990aa6?auto=format&fit=crop&w=1000&q=80',
                'approved', 175
            ),
            # 8. Pending Accommodation Listing (Demonstrates Admin Approval workflow!)
            (
                5, 'accommodation', 'Boys Hostel',
                'Patil Heights Premium Student Living',
                'Brand new hostel building near engineering colleges in Nashik with solar heating, elevator, and sports area.',
                'Plot 18, Near MVP Campus, Gangapur Road', 'Nashik', 'Gangapur Road', 'Near Horizon Hospital',
                '9765432109', 'vikram@patilresidency.com',
                5500.0, 'Per Month', 5000.0, '2 Sharing',
                'Gate Closes at 10:00 PM', '',
                'Wi-Fi, Solar Water, Lift, Table Tennis Room, RO Purifier, Power Backup',
                'ID verification mandatory at check-in.',
                'https://images.unsplash.com/photo-1596276020587-8044fe049813?auto=format&fit=crop&w=1000&q=80',
                'pending', 12
            )
        ]

        cursor.executemany("""
        INSERT INTO listings (
            provider_id, category, subcategory, title, description, address, city, area, landmark,
            contact_phone, contact_email, pricing_amount, pricing_period, deposit_amount,
            capacity_or_beds, timings, menu_details, amenities, rules, image_url, status, views_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, listings_data)
        conn.commit()

        # Seed Reviews
        reviews_data = [
            (1, 6, 'Yogiraj Pawar', 5, 'Exceptional place! Wi-Fi speed is top-notch and Ramesh uncle takes great care of maintenance. Perfect for college students.', 'approved'),
            (1, 7, 'Onkar Shinde', 4, 'Very clean rooms and safe locality. Close to FC Road and bus stop. Highly recommended.', 'approved'),
            (2, 8, 'Snehal More', 5, 'Super safe with biometric entry. The breakfast is healthy and tastes like home. Warden is very supportive.', 'approved'),
            (4, 6, 'Yogiraj Pawar', 5, 'Best mess in Kothrud! Unlimited hot rotis and very hygienic dining hall. Special Sunday meals are delicious.', 'approved'),
            (4, 7, 'Onkar Shinde', 5, 'Great price-to-quality ratio. The tiffin service is punctual and food is never too oily or spicy.', 'approved'),
            (6, 6, 'Yogiraj Pawar', 5, 'Best study library in Pune! 24/7 AC, silent ambiance, and fast Wi-Fi helped me crack my exams without any distractions.', 'approved'),
            (6, 7, 'Onkar Shinde', 4, 'Ergonomic chairs are so comfortable for long study hours. Power sockets at every single desk.', 'approved')
        ]

        cursor.executemany("""
        INSERT INTO reviews (listing_id, student_id, student_name, rating, comment, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, reviews_data)
        conn.commit()

        # Seed Inquiries
        inquiries_data = [
            (1, 6, 2, 'Yogiraj Pawar', 'yogiraj@student.com', '9403312345', 'Hi Ramesh ji, is double sharing room currently available on the 2nd floor? Want to join from 1st of next month.', 'Next Month 1st', 'contacted'),
            (4, 7, 3, 'Onkar Shinde', 'onkar@student.com', '9422054321', 'Hello Sunita ji, do you deliver packed lunch tiffins to Fergusson College area?', 'Immediate', 'new'),
            (6, 6, 4, 'Yogiraj Pawar', 'yogiraj@student.com', '9403312345', 'Hi, I need a 24-hour monthly study slot with personal locker from Monday.', 'Next Monday', 'new')
        ]

        cursor.executemany("""
        INSERT INTO inquiries (listing_id, student_id, provider_id, student_name, student_email, student_phone, message, move_in_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, inquiries_data)

        # Seed Saved Listings
        saved_data = [
            (6, 1), # Yogiraj saved Sai Comfort Hostel
            (6, 4), # Yogiraj saved Annapurna Mess
            (6, 6), # Yogiraj saved Vidya Library
            (7, 1), # Onkar saved Sai Comfort Hostel
            (7, 6)  # Onkar saved Vidya Library
        ]
        cursor.executemany("""
        INSERT INTO saved_listings (student_id, listing_id)
        VALUES (?, ?)
        """, saved_data)

        conn.commit()
        print("[+] Seed completed successfully!")

    conn.close()
    print("[+] Database is initialized and ready.")

if __name__ == '__main__':
    init_database()
