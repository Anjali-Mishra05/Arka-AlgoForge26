#!/usr/bin/env python3
"""
Migration script to seed initial test users into MongoDB.
Run this once after deploying to ensure test accounts exist.

Usage:
  python migrate_users.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from utils.database import Database
from utils.auth import get_password_hash

load_dotenv()

def migrate_test_users():
    """Seed test users into MongoDB users collection."""
    db = Database("pravaha_app")

    test_users = [
        {
            "username": "user",
            "email": "user@test.com",
            "password": "user",
            "role": "user",
        },
        {
            "username": "admin",
            "email": "admin@test.com",
            "password": "admin",
            "role": "admin",
        },
        {
            "username": "team",
            "email": "team@test.com",
            "password": "team",
            "role": "team",
        },
    ]

    users_collection = db.db["users"]

    for user_data in test_users:
        username = user_data["username"]

        # Check if user already exists
        existing = users_collection.find_one({"username": username})
        if existing:
            print(f"[OK] User '{username}' already exists, skipping")
            continue

        # Hash password and create user
        hashed_password = get_password_hash(user_data["password"])
        user_doc = {
            "username": username,
            "email": user_data["email"],
            "hashed_password": hashed_password,
            "role": user_data["role"],
            "created_at": datetime.utcnow(),
        }

        users_collection.insert_one(user_doc)
        print(f"[OK] Created user '{username}' with email '{user_data['email']}' (role: {user_data['role']})")

    print("\n[OK] Migration complete! Test users have been seeded.")
    print("\nTest account credentials:")
    for user_data in test_users:
        print(f"  - Username: {user_data['username']}, Password: {user_data['password']}, Role: {user_data['role']}")

if __name__ == "__main__":
    try:
        migrate_test_users()
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
