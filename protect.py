#!/usr/bin/env python3
"""
Simple Protection Wrapper

Quick commands to protect files during development without changing your normal settings.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command: str) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False


def main():
    """Main function for protection wrapper."""
    if len(sys.argv) < 2:
        print("[PROTECT]  File Protection - Quick Commands")
        print("=" * 40)
        print()
        print("[CREATE] Usage:")
        print("   python protect.py start    - Start protecting files")
        print("   python protect.py stop     - Stop protection")
        print("   python protect.py status   - Show protection status")
        print("   python protect.py commit   - Safely commit changes")
        print()
        print("[TIP] This preserves your normal IDE and Git settings")
        print("   while preventing auto-reverts during development.")
        return
    
    command = sys.argv[1].lower()
    
    if command == "start":
        print("[START] Starting file protection...")
        success = run_command("python smart_protection.py")
        if success:
            print("[OK] Protection started! Your files are now monitored.")
            print("[TIP] Continue working normally - you'll be alerted if files are reverted.")
    
    elif command == "stop":
        print("[UNLOCK] Stopping file protection...")
        success = run_command("python smart_protection.py stop")
        if success:
            print("[OK] Protection stopped. Normal IDE behavior restored.")
    
    elif command == "status":
        print("[DASHBOARD] Checking protection status...")
        run_command("python smart_protection.py status")
    
    elif command == "commit":
        print("[BACKUP] Safely committing changes...")
        
        # Stop protection temporarily
        print("1️⃣ Stopping protection...")
        run_command("python smart_protection.py stop")
        
        # Add and commit changes
        print("2️⃣ Adding changes...")
        run_command("git add .")
        
        # Get commit message
        if len(sys.argv) > 2:
            commit_msg = " ".join(sys.argv[2:])
        else:
            commit_msg = input("[CREATE] Enter commit message: ").strip()
            if not commit_msg:
                commit_msg = f"Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print("3️⃣ Committing...")
        success = run_command(f'git commit -m "{commit_msg}"')
        
        if success:
            print("[OK] Changes committed successfully!")
            
            # Restart protection
            restart = input("[UPDATE] Restart protection? (y/n): ").lower().strip()
            if restart == 'y' or restart == '':
                print("4️⃣ Restarting protection...")
                run_command("python smart_protection.py")
                print("[OK] Protection restarted!")
        else:
            print("[ERROR] Commit failed. Check git status.")
    
    elif command == "update":
        if len(sys.argv) > 2:
            file_path = sys.argv[2]
            print(f"[UPDATE] Updating protection for: {file_path}")
            run_command(f"python smart_protection.py update {file_path}")
        else:
            print("[ERROR] Usage: python protect.py update <file_path>")
    
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("[TIP] Use 'python protect.py' to see available commands")


if __name__ == "__main__":
    from datetime import datetime
    main()
