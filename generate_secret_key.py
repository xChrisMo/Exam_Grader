#!/usr/bin/env python3
"""
Generate a secure SECRET_KEY for the Exam Grader application.
This script generates a cryptographically secure random key suitable for Flask applications.
"""

import secrets
import sys

def generate_secret_key(length=32):
    """Generate a secure secret key of specified length."""
    return secrets.token_hex(length)

def main():
    """Generate and display a secure secret key."""
    print("🔐 Generating secure SECRET_KEY for Exam Grader...")
    print()
    
    # Generate a 32-byte (64 hex characters) secret key
    secret_key = generate_secret_key(32)
    
    print(f"Generated SECRET_KEY: {secret_key}")
    print()
    print("📋 To use this key:")
    print("1. Copy the key above")
    print("2. Set it as an environment variable in your deployment platform")
    print("3. For Render.com: Go to your service → Environment → Add SECRET_KEY")
    print()
    print("⚠️  Keep this key secure and never commit it to version control!")
    
    return secret_key

if __name__ == "__main__":
    main()
