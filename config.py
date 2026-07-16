import os

class Config:
    # Flask session encryption key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_super_secret_129837498273498237')
    
    # PostgreSQL Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is missing. A valid PostgreSQL connection string is required.")
    
    # Session security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
