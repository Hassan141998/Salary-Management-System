"""
Initialize PostgreSQL Database for RASS Cuisine
Run this ONCE after deploying to create tables and admin user
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import app, db, User

def init_database():
    print("=" * 60)
    print("RASS CUISINE - Database Initialization")
    print("=" * 60)

    with app.app_context():
        try:
            # Check database connection
            db_url = app.config['SQLALCHEMY_DATABASE_URI']
            if 'postgresql' in db_url:
                print("\n✅ Using PostgreSQL (Neon)")
                print(f"   Host: {db_url.split('@')[1].split('/')[0]}")
            else:
                print("\n✅ Using SQLite (Local)")

            print("\n1. Creating all tables...")
            db.create_all()
            print("   ✅ Tables created successfully!")

            # List created tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   Tables: {', '.join(tables)}")

            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()

            if admin:
                print("\n2. Admin user already exists")
                print("   Username: admin")
                print("   (Password unchanged)")
            else:
                print("\n2. Creating admin user...")
                admin = User(username='admin')
                admin.set_password('rass2024')
                db.session.add(admin)
                db.session.commit()
                print("   ✅ Admin user created!")
                print("   Username: admin")
                print("   Password: rass2024")
                print("   ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")

            print("\n" + "=" * 60)
            print("✅ DATABASE INITIALIZATION COMPLETE!")
            print("=" * 60)
            print("\nYour application is ready to use!")
            print("Login at: https://rasscuisine-czqa87whf-hassan-ahmeds-projects-f245c0d0.vercel.app")
            print("\n")

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            print("\nPlease check:")
            print("1. DATABASE_URL is set correctly in .env or Vercel")
            print("2. Neon database is accessible")
            print("3. Connection string is correct")
            print("\nYour DATABASE_URL should look like:")
            print("postgresql://user:pass@host/database?sslmode=require")

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Make sure .env file has DATABASE_URL")
    print("Or set it as environment variable before running.\n")

    response = input("Do you want to proceed with initialization? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        init_database()
    else:
        print("\nInitialization cancelled.")