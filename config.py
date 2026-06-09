import os

class Config:
    # Flask session encryption key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_super_secret_129837498273498237')
    
    # MySQL Database credentials
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'auth_system')
    
    # Session security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
