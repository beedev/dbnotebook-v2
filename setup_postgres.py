#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script
Creates the development database for the notebook architecture
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

# Database credentials
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "root"
POSTGRES_DB_ADMIN = "postgres"  # Connect to default postgres db first
POSTGRES_DB_DEV = "rag_chatbot_dev"  # Database to create


def test_connection():
    """Test PostgreSQL connection"""
    try:
        print(f"Testing connection to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}...")
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB_ADMIN
        )
        conn.close()
        print("✓ Connection successful!")
        return True
    except psycopg2.OperationalError as e:
        print(f"✗ Connection failed: {e}")
        return False


def database_exists(cursor, db_name):
    """Check if database exists"""
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    return cursor.fetchone() is not None


def create_database():
    """Create the development database"""
    try:
        # Connect to default postgres database
        print(f"\nConnecting to {POSTGRES_DB_ADMIN} database...")
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB_ADMIN
        )

        # Set isolation level for CREATE DATABASE
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        if database_exists(cursor, POSTGRES_DB_DEV):
            print(f"✓ Database '{POSTGRES_DB_DEV}' already exists")
        else:
            # Create database
            print(f"Creating database '{POSTGRES_DB_DEV}'...")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(POSTGRES_DB_DEV)
                )
            )
            print(f"✓ Database '{POSTGRES_DB_DEV}' created successfully!")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"✗ Error creating database: {e}")
        return False


def verify_database():
    """Verify connection to the new database"""
    try:
        print(f"\nVerifying connection to '{POSTGRES_DB_DEV}'...")
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB_DEV
        )

        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ Successfully connected to '{POSTGRES_DB_DEV}'")
        print(f"  PostgreSQL version: {version[0].split(',')[0]}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"✗ Error connecting to database: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("PostgreSQL Development Database Setup")
    print("=" * 60)

    # Step 1: Test connection
    if not test_connection():
        print("\n✗ Setup failed: Cannot connect to PostgreSQL")
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. Credentials are correct")
        print("  3. PostgreSQL is accessible on localhost:5432")
        sys.exit(1)

    # Step 2: Create database
    if not create_database():
        print("\n✗ Setup failed: Cannot create database")
        sys.exit(1)

    # Step 3: Verify database
    if not verify_database():
        print("\n✗ Setup failed: Cannot verify database")
        sys.exit(1)

    # Success!
    print("\n" + "=" * 60)
    print("✓ Setup completed successfully!")
    print("=" * 60)
    print(f"\nDatabase details:")
    print(f"  Host: {POSTGRES_HOST}")
    print(f"  Port: {POSTGRES_PORT}")
    print(f"  Database: {POSTGRES_DB_DEV}")
    print(f"  User: {POSTGRES_USER}")
    print(f"\nConnection string:")
    print(f"  postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_DEV}")
    print("\nYou can now proceed with the notebook architecture implementation!")


if __name__ == "__main__":
    main()
