#!/usr/bin/env python3
"""
Deployment script for LLM training improvements.
"""

import os
import sys
import subprocess
import logging
import json
import time
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manages the deployment of LLM training improvements."""
    
    def __init__(self, environment: str = 'production'):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / 'backups' / f'deployment_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        
    def deploy(self) -> bool:
        """Execute complete deployment process."""
        logger.info(f"Starting LLM improvements deployment for {self.environment}")
        
        try:
            # Pre-deployment checks
            if not self._pre_deployment_checks():
                logger.error("Pre-deployment checks failed")
                return False
            
            # Create backup
            if not self._create_backup():
                logger.error("Backup creation failed")
                return False
            
            # Run database migrations
            if not self._run_migrations():
                logger.error("Database migrations failed")
                return False
            
            # Update application
            if not self._update_application():
                logger.error("Application update failed")
                return False
            
            # Post-deployment verification
            if not self._post_deployment_verification():
                logger.error("Post-deployment verification failed")
                return False
            
            logger.info("Deployment completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed with exception: {e}")
            return False
    
    def _pre_deployment_checks(self) -> bool:
        """Perform pre-deployment checks."""
        logger.info("Running pre-deployment checks...")
        
        # Check database connection
        try:
            sys.path.insert(0, str(self.project_root))
            from webapp.app_factory import create_app
            from src.database.models import db
            
            app = create_app(self.environment)
            with app.app_context():
                db.session.execute("SELECT 1").fetchone()
            
            logger.info("Database connection check passed")
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
        
        # Check file permissions
        critical_dirs = ['logs', 'uploads', 'temp', 'instance']
        for dir_name in critical_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
            
            if not os.access(dir_path, os.W_OK):
                logger.error(f"No write access to: {dir_name}")
                return False
        
        logger.info("Pre-deployment checks passed")
        return True
    
    def _create_backup(self) -> bool:
        """Create backup of current system."""
        logger.info("Creating system backup...")
        
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup database
            db_path = self.project_root / 'instance' / 'exam_grader.db'
            if db_path.exists():
                import shutil
                shutil.copy2(db_path, self.backup_dir / 'exam_grader.db')
            
            # Backup configuration files
            config_files = ['.env', '.env.local', 'config/performance.json', 'config/security.json']
            config_backup_dir = self.backup_dir / 'config'
            config_backup_dir.mkdir(exist_ok=True)
            
            for config_file in config_files:
                source = self.project_root / config_file
                if source.exists():
                    import shutil
                    dest = config_backup_dir / Path(config_file).name
                    shutil.copy2(source, dest)
            
            logger.info(f"Backup created successfully at {self.backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False
    
    def _run_migrations(self) -> bool:
        """Run database migrations."""
        logger.info("Running database migrations...")
        
        try:
            sys.path.insert(0, str(self.project_root))
            from webapp.app_factory import create_app
            from src.database.models import db
            
            app = create_app(self.environment)
            
            with app.app_context():
                # Run LLM testing enhancements migration
                migration_script = self.project_root / 'migrations' / 'add_llm_testing_enhancements.py'
                if migration_script.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("migration", migration_script)
                    migration_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(migration_module)
                    
                    # Run upgrade
                    migration_module.upgrade()
                    logger.info("LLM testing enhancements migration completed")
                
                # Create any missing tables
                db.create_all()
                
            logger.info("Database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database migrations failed: {e}")
            return False
    
    def _update_application(self) -> bool:
        """Update application code."""
        logger.info("Updating application code...")
        
        try:
            # Install/update Python dependencies
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '--upgrade'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to update dependencies: {result.stderr}")
                return False
            
            logger.info("Application code updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Application update failed: {e}")
            return False
    
    def _post_deployment_verification(self) -> bool:
        """Verify deployment success."""
        logger.info("Running post-deployment verification...")
        
        try:
            sys.path.insert(0, str(self.project_root))
            from webapp.app_factory import create_app
            from src.database.models import db
            
            app = create_app(self.environment)
            with app.app_context():
                # Test basic database operations
                db.session.execute("SELECT 1").fetchone()
                
                # Verify new models can be imported
                try:
                    from src.services.system_monitoring import monitoring_service
                    from src.database.models import LLMModelTest
                    logger.info("New features verification passed")
                except ImportError as e:
                    logger.warning(f"Some new features may not be available: {e}")
                
            logger.info("Post-deployment verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Post-deployment verification failed: {e}")
            return False


def main():
    """Main deployment function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy LLM training improvements')
    parser.add_argument('--environment', '-e', default='production',
                       choices=['development', 'testing', 'production'],
                       help='Deployment environment')
    
    args = parser.parse_args()
    
    deployment_manager = DeploymentManager(args.environment)
    success = deployment_manager.deploy()
    
    if success:
        logger.info("Deployment completed successfully!")
        return True
    else:
        logger.error("Deployment failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)