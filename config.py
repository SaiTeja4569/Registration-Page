import os

class Config:
    # Flask session encryption key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_super_secret_129837498273498237')
    
    # SQLite Database configuration
    DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database.db'))
    
    # Session security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
