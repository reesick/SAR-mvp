"""
One-time script: Enable pgvector extension on Render DB, then create tables and seed data.
"""
from sqlalchemy import text
from app.database import engine, Base
from app.models import *  # noqa – registers all models with Base

print("🔌 Connecting to Render PostgreSQL...")

# Step 1: Enable pgvector extension
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    conn.commit()
    print("✅ pgvector extension enabled")

# Step 2: Create all tables
Base.metadata.create_all(bind=engine)
print("✅ All tables created")

# Step 3: Seed data
from generate_data import generate_synthetic_data
generate_synthetic_data()
print("\n🎉 Render database is fully set up!")
