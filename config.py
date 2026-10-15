import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'student_resource_mgmt_secret_key_2026_cmcs')
    
    # Database mode: 'sqlite' or 'mysql'
    # Default is 'sqlite' for zero-friction setup and immediate execution.
    # Set DB_TYPE='mysql' in environment or change here to use MySQL with XAMPP/WAMP.
    DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')
    
    # SQLite configuration
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.path.join(BASE_DIR, 'student_portal.db')
    
    # MySQL configuration (for XAMPP / WAMP / MySQL Server)
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'student_portal_db')
    
    # Project Metadata
    PROJECT_NAME = "Student Resources Management System"
    PROJECT_SHORT_NAME = "Student Needs Portal"
    ACADEMIC_YEAR = "2026–2027"
    COLLEGE_NAME = "Commerce Management and Computer Science College"
    STUDENTS = ["Yogiraj Pawar", "Onkar Shinde"]
