import sqlite3
import re
from flask import g
from config import Config

def get_db():
    """Returns database connection stored in Flask application context."""
    if 'db' not in g:
        if Config.DB_TYPE.lower() == 'mysql':
            try:
                import mysql.connector
                g.db = mysql.connector.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    database=Config.MYSQL_DB,
                    autocommit=True
                )
                g.db_type = 'mysql'
            except Exception as e:
                print(f"[Database Warning] MySQL connection failed ({e}). Falling back to SQLite.")
                g.db = sqlite3.connect(Config.SQLITE_PATH)
                g.db.row_factory = sqlite3.Row
                g.db_type = 'sqlite'
        else:
            g.db = sqlite3.connect(Config.SQLITE_PATH)
            g.db.row_factory = sqlite3.Row
            g.db_type = 'sqlite'
    return g.db

def close_db(e=None):
    """Closes database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """
    Executes a SELECT query and returns rows as dictionaries.
    Automatically handles parameter placeholders (? for SQLite, %s for MySQL).
    """
    conn = get_db()
    db_type = getattr(g, 'db_type', 'sqlite')
    
    if db_type == 'mysql':
        # Translate '?' placeholders to '%s' for MySQL
        mysql_query = query.replace('?', '%s')
        cursor = conn.cursor(dictionary=True)
        cursor.execute(mysql_query, args)
        rv = cursor.fetchall()
        cursor.close()
    else:
        cursor = conn.cursor()
        cursor.execute(query, args)
        rv = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), return_id=False):
    """
    Executes an INSERT, UPDATE, or DELETE query and commits.
    Returns the lastrowid if return_id=True, or rowcount.
    """
    conn = get_db()
    db_type = getattr(g, 'db_type', 'sqlite')
    
    if db_type == 'mysql':
        mysql_query = query.replace('?', '%s')
        cursor = conn.cursor()
        cursor.execute(mysql_query, args)
        last_id = cursor.lastrowid
        row_count = cursor.rowcount
        conn.commit()
        cursor.close()
        return last_id if return_id else row_count
    else:
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
        last_id = cursor.lastrowid
        row_count = cursor.rowcount
        cursor.close()
        return last_id if return_id else row_count
