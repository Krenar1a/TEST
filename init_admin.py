"""
Database initialization script to create the admin user.
Run this once to set up the admin user in the database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.models.database import SessionLocal, engine, Base
from app.models.admin import AdminUser, APIKey
from werkzeug.security import generate_password_hash

def init_admin_user():
    """Initialize the admin user with default credentials."""
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if admin user already exists
        existing_admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
        
        if existing_admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin_user = AdminUser(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Please change the default password after first login.")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
        
    finally:
        db.close()

if __name__ == "__main__":
    init_admin_user()
