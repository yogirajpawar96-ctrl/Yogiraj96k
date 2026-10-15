# Student Resources Management System (Student Needs Portal)
**Academic Year:** 2026–2027  
**College:** Commerce Management and Computer Science College  
**Submitted By:**  
1. Yogiraj Pawar  
2. Onkar Shinde  

---

## 📌 Project Overview
Student Needs Portal is a full-stack web application designed to help college students easily discover, compare, and connect with essential student services:
1. **Accommodation Module:** Hostels, PGs, and rental room listings with rent, security deposits, occupancy sharing, and curfew rules.
2. **Mess Services Module:** Homely daily meals, Maharashtrian & North Indian menus, meal timings, tiffin delivery, and pricing.
3. **Private Library Module:** 24/7 air-conditioned reading halls, study cubicles with power sockets, and monthly passes.
4. **Search & Multi-Filter Module:** Search by location (FC Road, Kothrud, Viman Nagar, etc.), category, amenities (Wi-Fi, AC, Food), and budget limit.
5. **Side-by-Side Comparison Matrix:** Compare up to 4 services side-by-side to make informed decisions.
6. **Feedback & Review System:** 1 to 5 star ratings and genuine student feedback.
7. **Admin Governance & Verification:** Mandatory verification for providers and listings before public display.

---

## 🛠️ Technology Stack
- **Frontend:** HTML5, Modern CSS3 (Custom Responsive Design System), JavaScript (ES6, Fetch API, dynamic DOM)
- **Backend:** Python (Flask Framework)
- **Database:** 
  - **Default (Zero-Config):** SQLite 3 (Database file auto-created: `student_portal.db`)
  - **Production / Viva Submission:** MySQL (`schema.mysql.sql` included)
- **Development Tool:** Visual Studio Code (VS Code)

---

## 🚀 Quick Start Guide

### 1. Requirements
Ensure Python 3.10+ is installed on your system.

### 2. Navigate to Project Directory
```powershell
cd C:\Users\YOGIRAJ\.gemini\antigravity\scratch\student_resources_portal
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Initialize Database (Pre-seeded with Sample Data)
```powershell
python init_db.py
```

### 5. Launch Application
```powershell
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🔑 Pre-Seeded Demo Credentials

You can use the **⚡ Quick Demo Login** button on the top-right header or log in using:

| Role | Email | Password | Name / Description |
|---|---|---|---|
| **Student** | `yogiraj@student.com` | `student123` | Yogiraj Pawar (Student Account) |
| **Student 2** | `onkar@student.com` | `student123` | Onkar Shinde (Student Account) |
| **Provider (Hostels)** | `ramesh@sharmaproperties.com` | `provider123` | Ramesh Sharma (Hostel & PG Owner) |
| **Provider (Mess)** | `sunita@annapurnamess.com` | `provider123` | Sunita Deshmukh (Mess Owner) |
| **Provider (Library)** | `mahesh@vidyalibrary.com` | `provider123` | Mahesh Kulkarni (Library Owner) |
| **Administrator** | `admin@studentportal.com` | `admin123` | System Administrator |

---

## 🗄️ Switching to MySQL (Optional)
If running on XAMPP / WAMP / MySQL Server:
1. Open MySQL Workbench or phpMyAdmin and import `schema.mysql.sql`.
2. Open `config.py` and set:
   ```python
   DB_TYPE = 'mysql'
   MYSQL_HOST = 'localhost'
   MYSQL_PORT = 3306
   MYSQL_USER = 'root'
   MYSQL_PASSWORD = ''
   MYSQL_DB = 'student_portal_db'
   ```
3. Run `python app.py`.

---

## 🎓 Viva & Presentation Highlights
- **How does the system ensure verified listings?**  
  New listings from providers are stored with `status = 'pending'`. Only administrators can review and approve them in the Admin Command Center before they appear in student search results.
- **How does the comparison module solve student difficulty?**  
  The `/compare` route dynamically constructs a comparative matrix contrasting prices, security deposits, timings, ratings, and facilities across multiple selected providers.
- **How are passwords stored securely?**  
  Passwords are salted and cryptographically hashed using PBKDF2/SHA-256 via `werkzeug.security`.
