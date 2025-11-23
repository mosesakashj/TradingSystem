#!/usr/bin/env python3
"""
Create admin user in database - Standalone script
"""
import os
import sys

# Load .env FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

print(f"Using DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')}")

# Now import database modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from database.models import Base, User, UserRole

# Create engine with the .env DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./trading.db')
engine = create_engine(DATABASE_URL, echo=True)

# Create all tables
print("\nCreating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created")

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    """Create admin user"""
    
    # Admin credentials
    username = "mosesakash.j@gmail.com"
    email = "mosesakash.j@gmail.com"
    password = "Akash@123"
    full_name = "Moses"
    
    print(f"\nCreating admin user: {username}")
    
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"⚠️  User already exists: {existing_user.username} (ID: {existing_user.id})")
            print(f"   Current role: {existing_user.role.value}")
            
            # Update to admin
            if existing_user.role != UserRole.ADMIN:
                existing_user.role = UserRole.ADMIN
                db.commit()
                print(f"   ✅ Updated to ADMIN role")
            else:
                print(f"   Already an ADMIN")
            
            return existing_user
        
        # Create new user
        hashed_password = pwd_context.hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Admin user created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")
        print(f"   Active: {user.is_active}")
        
        return user
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
    print("\n✅ Done! You can now login with your credentials.")
