#!/usr/bin/env python3
"""
Initialize all database tables
"""
import os
import sys

# Load .env FIRST
from dotenv import load_dotenv
load_dotenv()

print(f"Using DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')}")

# Now import database modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from database.models import Base

# Create engine
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./trading.db')
engine = create_engine(DATABASE_URL, echo=True)

# Create all tables
print("\n📊 Creating all database tables...")
Base.metadata.create_all(bind=engine)
print("\n✅ All tables created successfully!")

# List tables
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"\n📋 Tables in database:")
for table in tables:
    print(f"   - {table}")

print(f"\n✅ Database initialized with {len(tables)} tables")
