#!/usr/bin/env python3
"""
Cross-platform file locking script to prevent auto-restore.
"""

import os
import stat
from pathlib import Path


def lock_file(file_path: Path) -> bool:
    """Make a file read-only to prevent modification."""
    try:
        if file_path.exists():
            # Make file read-only
            current_permissions = file_path.stat().st_mode
            read_only_permissions = current_permissions & ~stat.S_IWRITE
            file_path.chmod(read_only_permissions)
            print(f"[LOCK] Locked: {file_path}")
            return True
        else:
            print(f"[WARNING]  File not found: {file_path}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to lock {file_path}: {e}")
        return False


def unlock_file(file_path: Path) -> bool:
    """Make a file writable."""
    try:
        if file_path.exists():
            # Make file writable
            current_permissions = file_path.stat().st_mode
            writable_permissions = current_permissions | stat.S_IWRITE
            file_path.chmod(writable_permissions)
            print(f"[UNLOCK] Unlocked: {file_path}")
            return True
        else:
            print(f"[WARNING]  File not found: {file_path}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to unlock {file_path}: {e}")
        return False


def main():
    """Main function to lock/unlock files."""
    import sys
    
    # Critical files to protect
    critical_files = [
        "webapp/exam_grader_app.py",
        "src/database/migrations.py",
        "src/database/utils.py", 
        "utils/rate_limiter.py",
        "utils/error_handler.py",
        "webapp/auth.py",
        "instance/.env"
    ]
    
    if len(sys.argv) > 1 and sys.argv[1] == "unlock":
        print("[UNLOCK] Unlocking critical files...")
        for file_path in critical_files:
            unlock_file(Path(file_path))
        print("[OK] Files unlocked!")
    else:
        print("[LOCK] Locking critical files...")
        for file_path in critical_files:
            lock_file(Path(file_path))
        print("[OK] Files locked!")
        print("[TIP] To unlock: python lock_files.py unlock")


if __name__ == "__main__":
    main()
