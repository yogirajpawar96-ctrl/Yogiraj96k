-- =====================================================================
-- STUDENT RESOURCES MANAGEMENT SYSTEM (STUDENT NEEDS PORTAL)
-- Academic Year: 2026-2027
-- College: Commerce Management and Computer Science College
-- Authors: Yogiraj Pawar, Onkar Shinde
-- Database: MySQL Schema DDL
-- =====================================================================

CREATE DATABASE IF NOT EXISTS student_portal_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE student_portal_db;

-- 1. USERS TABLE (Students, Service Providers, Administrators)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role ENUM('student', 'provider', 'admin') NOT NULL DEFAULT 'student',
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(30) NULL,
    password_hash VARCHAR(255) NOT NULL,
    college_name VARCHAR(150) NULL,
    business_name VARCHAR(150) NULL,
    address TEXT NULL,
    is_verified TINYINT(1) DEFAULT 0 COMMENT '0: Pending, 1: Verified, 2: Rejected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. LISTINGS TABLE (Accommodations, Mess Services, Private Libraries)
CREATE TABLE IF NOT EXISTS listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider_id INT NOT NULL,
    category ENUM('accommodation', 'mess', 'library') NOT NULL,
    subcategory VARCHAR(60) NOT NULL COMMENT 'Hostel, PG, Room, Veg Mess, AC Library, etc.',
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    area VARCHAR(100) NOT NULL,
    landmark VARCHAR(150) NULL,
    contact_phone VARCHAR(30) NOT NULL,
    contact_email VARCHAR(120) NULL,
    pricing_amount DECIMAL(10,2) NOT NULL,
    pricing_period VARCHAR(50) DEFAULT 'Per Month',
    deposit_amount DECIMAL(10,2) DEFAULT 0.00,
    capacity_or_beds VARCHAR(100) NULL,
    timings VARCHAR(150) NULL,
    menu_details TEXT NULL,
    amenities TEXT NULL COMMENT 'Comma separated amenities list',
    rules TEXT NULL,
    image_url TEXT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    views_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. REVIEWS & RATINGS TABLE
CREATE TABLE IF NOT EXISTS reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    student_id INT NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL,
    status ENUM('approved', 'flagged', 'hidden') DEFAULT 'approved',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. INQUIRIES TABLE (Direct inquiry from Student to Provider)
CREATE TABLE IF NOT EXISTS inquiries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    student_id INT NOT NULL,
    provider_id INT NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    student_email VARCHAR(120) NOT NULL,
    student_phone VARCHAR(30) NULL,
    message TEXT NOT NULL,
    move_in_date VARCHAR(50) NULL,
    status ENUM('new', 'contacted', 'closed') DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. SAVED / BOOKMARKED LISTINGS
CREATE TABLE IF NOT EXISTS saved_listings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    listing_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_listing (student_id, listing_id),
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
) ENGINE=InnoDB;
