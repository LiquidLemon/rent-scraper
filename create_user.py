#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.orm import sessionmaker
from database import engine
from models import User
from auth import get_password_hash

def create_user(username: str, password: str):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"Error: User '{username}' already exists!")
            return False
        
        # Create new user
        hashed_password = get_password_hash(password)
        new_user = User(username=username, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        
        print(f"Successfully created user: {username}")
        return True
        
    except Exception as e:
        print(f"Error creating user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    if create_user(username, password):
        sys.exit(0)
    else:
        sys.exit(1)