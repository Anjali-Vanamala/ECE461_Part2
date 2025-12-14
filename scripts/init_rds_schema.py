#!/usr/bin/env python3
"""
Initialize RDS PostgreSQL database schema.

This script creates the necessary tables for the artifacts storage backend.
Run this once after creating your RDS instance.

Usage:
    python scripts/init_rds_schema.py

Environment variables required:
    RDS_ENDPOINT - RDS instance endpoint
    RDS_DB_NAME - Database name (default: artifacts_db)
    RDS_USERNAME - Database username (default: postgres)
    RDS_PASSWORD - Database password
    RDS_PORT - Database port (default: 5432)
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables if .env file exists
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

# Check required environment variables
required_vars = ["RDS_ENDPOINT", "RDS_PASSWORD"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("\nRequired variables:")
    print("  RDS_ENDPOINT - RDS instance endpoint (e.g., mydb.abc123.us-east-2.rds.amazonaws.com)")
    print("  RDS_PASSWORD - Database password")
    print("\nOptional variables:")
    print("  RDS_DB_NAME - Database name (default: artifacts_db)")
    print("  RDS_USERNAME - Database username (default: postgres)")
    print("  RDS_PORT - Database port (default: 5432)")
    sys.exit(1)

# Import after setting up environment
try:
    from sqlalchemy import inspect

    from backend.storage.rds_postgres import _get_engine, _init_database
except ImportError as e:
    print(f"❌ Error importing RDS backend: {e}")
    print("Make sure you have installed: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

def main():
    """Initialize database schema."""
    print("🔧 Initializing RDS PostgreSQL schema...")
    print(f"   Endpoint: {os.getenv('RDS_ENDPOINT')}")
    print(f"   Database: {os.getenv('RDS_DB_NAME', 'artifacts_db')}")
    print()

    try:
        # Initialize database (creates tables)
        _init_database()

        # Verify tables were created
        engine = _get_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "artifacts" in tables:
            print("✅ Database schema initialized successfully!")
            print(f"   Created table: artifacts")
            print()
            print("📋 Table structure:")
            columns = inspector.get_columns("artifacts")
            for col in columns:
                print(f"   - {col['name']}: {col['type']}")
            print()
            print("✅ Ready to use RDS PostgreSQL backend!")
            print("   Set environment variable: STORAGE_BACKEND=rds_postgres")
        else:
            print("⚠️  Warning: Table 'artifacts' not found after initialization")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify RDS instance is running and accessible")
        print("  2. Check security group allows connections from your IP")
        print("  3. Verify database credentials are correct")
        print("  4. Ensure database exists (RDS_DB_NAME)")
        sys.exit(1)

if __name__ == "__main__":
    main()
