#!/usr/bin/env python3
"""
Smart File Protection System

This system provides non-intrusive protection that only activates during
active development sessions, preserving your normal IDE and Git settings.
"""

import os
import sys
import time
import json
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Set, Optional


class SmartFileProtector:
    """Non-intrusive file protection during active development."""
    
    def __init__(self, project_root: str):
        """Initialize smart protector.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.protection_file = self.project_root / ".file_protection_state"
        self.session_active = False
        self.protected_files: Dict[str, str] = {}  # file_path -> hash
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
    def get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file content."""
        try:
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
        except Exception:
            pass
        return ""
    
    def save_protection_state(self):
        """Save current protection state to file."""
        try:
            state = {
                'session_active': self.session_active,
                'protected_files': self.protected_files,
                'last_update': datetime.now().isoformat(),
                'session_start': getattr(self, 'session_start', datetime.now().isoformat())
            }
            
            with open(self.protection_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            print(f"[WARNING]  Could not save protection state: {e}")
    
    def load_protection_state(self) -> bool:
        """Load protection state from file."""
        try:
            if self.protection_file.exists():
                with open(self.protection_file, 'r') as f:
                    state = json.load(f)
                
                self.session_active = state.get('session_active', False)
                self.protected_files = state.get('protected_files', {})
                
                # Check if session is stale (older than 24 hours)
                last_update = datetime.fromisoformat(state.get('last_update', datetime.now().isoformat()))
                if datetime.now() - last_update > timedelta(hours=24):
                    print("🕐 Previous session expired, starting fresh")
                    self.session_active = False
                    self.protected_files = {}
                
                return True
        except Exception as e:
            print(f"[WARNING]  Could not load protection state: {e}")
        
        return False
    
    def start_protection_session(self, files_to_protect: Set[str]):
        """Start a protection session for specific files.
        
        Args:
            files_to_protect: Set of file paths to protect
        """
        print("[PROTECT]  Starting smart protection session...")
        
        self.session_active = True
        self.session_start = datetime.now().isoformat()
        
        # Record current state of files
        for file_path in files_to_protect:
            full_path = self.project_root / file_path
            if full_path.exists():
                file_hash = self.get_file_hash(full_path)
                self.protected_files[file_path] = file_hash
                print(f"[LOCK] Protecting: {file_path}")
        
        # Save state
        self.save_protection_state()
        
        # Start monitoring
        self.start_monitoring()
        
        print(f"[OK] Protection active for {len(self.protected_files)} files")
        print("[TIP] Use 'python smart_protection.py stop' to end session")
    
    def stop_protection_session(self):
        """Stop the protection session."""
        print("[UNLOCK] Stopping protection session...")
        
        self.session_active = False
        self.stop_monitoring.set()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        # Clear protection state
        self.protected_files = {}
        self.save_protection_state()
        
        # Clean up protection file
        if self.protection_file.exists():
            self.protection_file.unlink()
        
        print("[OK] Protection session ended")
    
    def start_monitoring(self):
        """Start background monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(target=self._monitor_files, daemon=True)
        self.monitoring_thread.start()
    
    def _monitor_files(self):
        """Background monitoring of protected files."""
        print("[MONITOR]  Background monitoring started...")
        
        while not self.stop_monitoring.is_set():
            try:
                for file_path, expected_hash in list(self.protected_files.items()):
                    full_path = self.project_root / file_path
                    
                    if full_path.exists():
                        current_hash = self.get_file_hash(full_path)
                        
                        # If file was reverted (hash changed back to original)
                        if current_hash != expected_hash and current_hash != "":
                            # Check if this looks like a revert (file became smaller or lost recent changes)
                            if self._detect_revert(full_path, file_path):
                                print(f"[ALERT] REVERT DETECTED: {file_path}")
                                self._handle_revert(full_path, file_path)
                    
                    # Update state periodically
                    self.save_protection_state()
                
                # Check every 3 seconds during active session
                self.stop_monitoring.wait(3)
                
            except Exception as e:
                print(f"[WARNING]  Monitoring error: {e}")
                self.stop_monitoring.wait(5)
    
    def _detect_revert(self, full_path: Path, file_path: str) -> bool:
        """Detect if a file has been reverted."""
        try:
            # Simple heuristics to detect reverts
            current_size = full_path.stat().st_size
            current_mtime = full_path.stat().st_mtime
            
            # If file became significantly smaller, likely reverted
            if current_size < 1000:  # Very small file, suspicious
                return True
            
            # If file was modified very recently (within last 10 seconds) 
            # but we didn't expect it, might be auto-revert
            if time.time() - current_mtime < 10:
                print(f"[CREATE] Recent change detected in {file_path}")
                return True
                
        except Exception:
            pass
        
        return False
    
    def _handle_revert(self, full_path: Path, file_path: str):
        """Handle detected revert by creating backup and alerting."""
        try:
            # Create emergency backup of current state
            backup_dir = self.project_root / "emergency_backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{full_path.name}.reverted_{timestamp}"
            
            import shutil
            shutil.copy2(full_path, backup_path)
            
            print(f"[BACKUP] Emergency backup created: {backup_path}")
            print(f"[NOTIFY] ALERT: {file_path} may have been auto-reverted!")
            print(f"   Check the file and restore from backup if needed")
            
        except Exception as e:
            print(f"[ERROR] Could not create emergency backup: {e}")
    
    def update_file_protection(self, file_path: str):
        """Update protection for a file after legitimate changes.
        
        Args:
            file_path: Path of file that was legitimately modified
        """
        if not self.session_active:
            return
        
        full_path = self.project_root / file_path
        if full_path.exists() and file_path in self.protected_files:
            new_hash = self.get_file_hash(full_path)
            self.protected_files[file_path] = new_hash
            self.save_protection_state()
            print(f"[UPDATE] Updated protection for: {file_path}")
    
    def get_session_status(self) -> Dict:
        """Get current session status."""
        return {
            'active': self.session_active,
            'protected_files': len(self.protected_files),
            'files': list(self.protected_files.keys()),
            'monitoring': self.monitoring_thread.is_alive() if self.monitoring_thread else False
        }


def main():
    """Main function for smart protection."""
    project_root = Path(__file__).parent
    protector = SmartFileProtector(str(project_root))
    
    # Load existing state
    protector.load_protection_state()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "stop":
            protector.stop_protection_session()
            return
        
        elif command == "status":
            status = protector.get_session_status()
            print("[DASHBOARD] Protection Status:")
            print(f"   Active: {status['active']}")
            print(f"   Protected files: {status['protected_files']}")
            print(f"   Monitoring: {status['monitoring']}")
            if status['files']:
                print("   Files:")
                for file_path in status['files']:
                    print(f"     • {file_path}")
            return
        
        elif command == "update":
            if len(sys.argv) > 2:
                file_path = sys.argv[2]
                protector.update_file_protection(file_path)
                return
            else:
                print("[ERROR] Usage: python smart_protection.py update <file_path>")
                return
    
    # Default: Start protection session
    print("[PROTECT]  Smart File Protection System")
    print("=" * 50)
    
    # Check if session is already active
    if protector.session_active:
        print("[OK] Protection session already active")
        status = protector.get_session_status()
        print(f"   Protecting {status['protected_files']} files")
        print("   Commands:")
        print("     python smart_protection.py stop     - End session")
        print("     python smart_protection.py status   - Show status")
        return
    
    # Critical files to protect during development
    critical_files = {
        "webapp/exam_grader_app.py",
        "src/database/migrations.py",
        "src/database/utils.py", 
        "utils/rate_limiter.py",
        "utils/error_handler.py",
        "webapp/auth.py",
        "instance/.env"
    }
    
    print("[TARGET] Starting protection for critical files...")
    print("   This will monitor files for auto-reverts without changing your IDE settings")
    print()
    
    # Start protection session
    protector.start_protection_session(critical_files)
    
    print()
    print("🎮 Commands:")
    print("   python smart_protection.py stop                    - End protection")
    print("   python smart_protection.py status                  - Show status")
    print("   python smart_protection.py update <file_path>      - Update file protection")
    print()
    print("[TIP] Protection runs in background. Your normal IDE settings are preserved.")
    print("   Files will be monitored for auto-reverts and you'll be alerted if detected.")


if __name__ == "__main__":
    main()
