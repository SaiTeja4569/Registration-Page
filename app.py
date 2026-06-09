import re
import os
import bcrypt
import math
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_wtf.csrf import CSRFProtect, CSRFError
import mysql.connector
from mysql.connector import pooling
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CSRF Protection globally
csrf = CSRFProtect(app)

# Database Connection Pool Setup
db_config = {
    "host": app.config['DB_HOST'],
    "user": app.config['DB_USER'],
    "password": app.config['DB_PASSWORD'],
    "database": app.config['DB_NAME']
}

try:
    # Set up a thread-safe connection pool
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="auth_pool",
        pool_size=5,
        pool_reset_session=True,
        **db_config
    )
    print("Database connection pool established successfully.")
except mysql.connector.Error as err:
    print(f"Database Error: {err}")
    connection_pool = None

def get_db_connection():
    if connection_pool:
        return connection_pool.get_connection()
    return mysql.connector.connect(**db_config)

def initialize_database():
    """Initializes tables and creates a default admin if none exists."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # We assume the database `auth_system` is already created and selected based on db_config.
        
        # Read and execute schema.sql (or create tables here)
        schema_path = os.path.join(app.root_path, 'database', 'schema.sql')
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                # Simple split by ';' for execution, ignoring empty statements
                statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
                for statement in statements:
                    try:
                        cursor.execute(statement)
                    except mysql.connector.Error as err:
                        print(f"Database Error during schema execution: {err}")
        
        conn.commit()
        
        # Create default admin if not exists
        cursor.execute("SELECT id FROM admins LIMIT 1")
        if not cursor.fetchone():
            salt = bcrypt.gensalt()
            hashed_pw = bcrypt.hashpw('admin'.encode('utf-8'), salt).decode('utf-8')
            cursor.execute(
                "INSERT INTO admins (username, password_hash, email) VALUES (%s, %s, %s)",
                ('admin', hashed_pw, 'admin@example.com')
            )
            conn.commit()
            print("Default admin created. Username: admin, Password: admin")
            
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# Run DB initialization
with app.app_context():
    initialize_database()

# --- Helper Validation Functions ---
def validate_email(email):
    return re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email) is not None

def validate_mobile(mobile):
    return len(mobile) == 10 and mobile.isdigit()

def validate_password_strength(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"[0-9]", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Admin privileges required.", "error")
            return redirect(url_for('admin_login_page'))
        return f(*args, **kwargs)
    return decorated_function

# --- Public HTML Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return render_template('landing.html')

@app.route('/register')
def register_page():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return render_template('auth/register.html')

@app.route('/login')
def login_page():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return render_template('auth/login.html')

# --- User Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT fullname, username, email, mobile, created_at, account_status FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if not user or user['account_status'] != 'active':
            session.clear()
            flash("Your account is not active.", "error")
            return redirect(url_for('login_page'))
            
        cursor.execute("SELECT COUNT(*) as count FROM login_logs WHERE user_id = %s", (session['user_id'],))
        login_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT login_time FROM login_logs WHERE user_id = %s ORDER BY login_time DESC LIMIT 1 OFFSET 1", (session['user_id'],))
        last_login_row = cursor.fetchone()
        last_login = last_login_row['login_time'] if last_login_row else None
        
        cursor.execute("SELECT login_time, logout_time, ip_address FROM login_logs WHERE user_id = %s ORDER BY login_time DESC LIMIT 5", (session['user_id'],))
        recent_logins = cursor.fetchall()
            
        return render_template('dashboard/index.html', user=user, login_count=login_count, last_login=last_login, recent_logins=recent_logins)
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return f"Database Error: {err}", 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- Auth API Routes ---
@app.route('/api/register', methods=['POST'])
def api_register():
    fullname = request.form.get('fullname', '').strip()
    email = request.form.get('email', '').strip()
    mobile = request.form.get('mobile', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not all([fullname, email, mobile, username, password, confirm_password]):
        return jsonify({"success": False, "message": "All fields are required."}), 400
    if not validate_email(email):
        return jsonify({"success": False, "message": "Invalid email address."}), 400
    if not validate_mobile(mobile):
        return jsonify({"success": False, "message": "Mobile must be 10 digits."}), 400
    if not validate_password_strength(password):
        return jsonify({"success": False, "message": "Password is too weak."}), 400
    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match."}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone(): return jsonify({"success": False, "message": "Email exists."}), 409
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone(): return jsonify({"success": False, "message": "Username taken."}), 409

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (fullname, email, mobile, username, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (fullname, email, mobile, username, hashed_password)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Registration successful!"}), 201
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/login', methods=['POST'])
def api_login():
    username_or_email = request.form.get('username_or_email', '').strip()
    password = request.form.get('password', '')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, username, password_hash, account_status FROM users WHERE username = %s OR email = %s", (username_or_email, username_or_email))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            if user['account_status'] != 'active':
                return jsonify({"success": False, "message": f"Account is {user['account_status']}."}), 403
                
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Log login
            ip_address = request.remote_addr
            cursor.execute(
                "INSERT INTO login_logs (user_id, username, ip_address) VALUES (%s, %s, %s)",
                (user['id'], user['username'], ip_address)
            )
            conn.commit()
            
            # Get the log ID to update on logout
            session['log_id'] = cursor.lastrowid
            
            return jsonify({"success": True, "message": "Login successful!"}), 200

        return jsonify({"success": False, "message": "Invalid credentials."}), 401
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return jsonify({"success": False, "message": f"Database error: {err}"}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/logout')
def logout():
    if 'user_id' in session and 'log_id' in session:
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE login_logs SET logout_time = CURRENT_TIMESTAMP WHERE id = %s",
                (session['log_id'],)
            )
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

# --- Admin Routes ---
@app.route('/admin')
def admin_index():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_page():
    if 'admin_id' in session: return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, password_hash FROM admins WHERE username = %s", (username,))
            admin = cursor.fetchone()
            
            if admin and bcrypt.checkpw(password.encode('utf-8'), admin['password_hash'].encode('utf-8')):
                session.clear()
                session['admin_id'] = admin['id']
                flash("Admin login successful.", "success")
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid admin credentials.", "error")
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            flash(f"Database error: {err}", "error")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
            
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash("Admin logged out.", "success")
    return redirect(url_for('admin_login_page'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'id_desc')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Stats
        stats = {}
        cursor.execute("SELECT COUNT(*) as c FROM users")
        stats['total_users'] = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM users WHERE account_status='active'")
        stats['active_users'] = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM login_logs WHERE DATE(login_time) = CURDATE()")
        stats['today_logins'] = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM login_logs")
        stats['total_logins'] = cursor.fetchone()['c']
        
        # Build query
        query_conditions = ""
        params = []
        if search:
            query_conditions = "WHERE username LIKE %s OR email LIKE %s"
            params.extend([f"%{search}%", f"%{search}%"])
            
        order_by = "ORDER BY id DESC"
        if sort == 'id_asc': order_by = "ORDER BY id ASC"
        elif sort == 'username_asc': order_by = "ORDER BY username ASC"
        
        # Pagination
        count_query = f"SELECT COUNT(*) as c FROM users {query_conditions}"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()['c']
        total_pages = math.ceil(total_records / per_page)
        offset = (page - 1) * per_page
        
        query = f"SELECT id, fullname, username, email, created_at, account_status FROM users {query_conditions} {order_by} LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        cursor.execute(query, params)
        users = cursor.fetchall()
        
        return render_template('admin/dashboard.html', stats=stats, users=users, current_page=page, total_pages=total_pages)
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return f"Database Error: {err}", 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/admin/users/<int:user_id>/logs')
@admin_required
def admin_user_logs(user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT fullname, username, email FROM users WHERE id = %s", (user_id,))
        target_user = cursor.fetchone()
        if not target_user:
            flash("User not found.", "error")
            return redirect(url_for('admin_dashboard'))
            
        cursor.execute("SELECT login_time, logout_time, ip_address FROM login_logs WHERE user_id = %s ORDER BY login_time DESC LIMIT 50", (user_id,))
        logs = cursor.fetchall()
        
        return render_template('admin/user_logs.html', target_user=target_user, logs=logs)
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return f"Database Error: {err}", 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if request.path.startswith('/api/'):
        return jsonify({"success": False, "message": "CSRF validation failed."}), 400
    flash("CSRF token missing or invalid.", "error")
    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
