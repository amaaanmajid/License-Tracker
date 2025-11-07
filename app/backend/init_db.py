#!/usr/bin/env python3
"""
Database Initialization Script
Creates all tables and default admin user automatically
"""

import sys
from pathlib import Path

# Add parent directory to path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from database import engine, Base, SessionLocal
import models
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_database():
    """Initialize database with tables and default admin user"""
    
    print("🔄 Initializing License Tracker Database...")
    print("=" * 60)
    
    try:
        # Create all tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # Create default admin user
        db = SessionLocal()
        try:
            # Check if admin already exists
            existing_admin = db.query(models.User).filter(
                models.User.email == "admin@licensetracker.com"
            ).first()
            
            if existing_admin:
                print("ℹ️  Default admin user already exists")
            else:
                print("👤 Creating default admin user...")
                
                admin_user = models.User(
                    user_id=str(uuid.uuid4()),
                    email="admin@licensetracker.com",
                    name="System Administrator",
                    password_hash=pwd_context.hash("Admin@123"),
                    role=models.UserRole.ADMIN
                )
                
                db.add(admin_user)
                db.commit()
                
                print("✅ Default admin user created!")
                print("=" * 60)
                print("📧 Email: admin@licensetracker.com")
                print("🔑 Password: Admin@123")
                print("=" * 60)
                print("⚠️  IMPORTANT: Change this password after first login!")
        
        finally:
            db.close()
        
        print()
        print("🎉 Database initialization complete!")
        print()
        print("Next steps:")
        print("1. Start the backend: uvicorn server:app --reload")
        print("2. Start the frontend: cd frontend && npm start")
        print("3. Login with admin credentials above")
        print()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check if MySQL is running")
        print("2. Verify DATABASE_URL in .env file")
        print("3. Ensure database 'license_tracker' exists")
        print("4. Check user permissions")
        sys.exit(1)

if __name__ == "__main__":
    init_database()