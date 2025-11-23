#!/usr/bin/env python3
"""
Create admin user in database
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from database.user_management import create_user
from database.models import UserRole

def create_admin_user():
    """Create admin user"""
    
    # Admin credentials
    username = "mosesakash.j@gmail.com"
    email = "mosesakash.j@gmail.com"
    password = "Akash@123"
    full_name = "Moses"
    
    print("Creating admin user...")
    
    with get_db() as db:
        try:
            user = create_user(
                db=db,
                username=username,
                email=email,
                password=password,
                full_name=full_name,
                role=UserRole.ADMIN
            )
            
            print(f"✅ Admin user created successfully!")
            print(f"   ID: {user.id}")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role.value}")
            print(f"   Active: {user.is_active}")
            
        except ValueError as e:
            print(f"❌ Error: {e}")
            print("   User might already exist. Checking...")
            
            from database.models import User
            existing_user = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                print(f"   Found existing user: {existing_user.username} (ID: {existing_user.id})")
                print(f"   Role: {existing_user.role.value}")
                print(f"   Active: {existing_user.is_active}")
                
                # Update to admin if not already
                if existing_user.role != UserRole.ADMIN:
                    existing_user.role = UserRole.ADMIN
                    db.commit()
                    print(f"   ✅ Updated user to ADMIN role")
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    create_admin_user()
