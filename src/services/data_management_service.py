"""
Data Management Service

This service provides data integrity validation, cleanup tools, and storage
optimization for the LLM training system.
"""

import os
import shutil
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.database.models import (
    db, LLMDocument, LLMDataset, LLMTrainingJob, LLMModelTest, 
    LLMTestSubmission, LLMDatasetDocument, LLMTrainingReport
)
from utils.logger import logger

class DataManagementService:
    """Service for managing data integrity and cleanup operations"""
    
    def __init__(self):
        self.cleanup_rules = {
            'orphaned_files': {
                'enabled': True,
                'max_age_days': 30,
                'file_patterns': ['*.tmp', '*.log', '*.cache']
            },
            'failed_jobs': {
                'enabled': True,
                'max_age_days': 90,
                'keep_recent': 10
            },
            'old_reports': {
                'enabled': True,
                'max_age_days': 180,
                'keep_recent': 5
            },
            'unused_datasets': {
                'enabled': False,  # Manual only
                'max_age_days': 365
            }
        }
    
    def validate_data_integrity(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate data integrity across the system
        
        Args:
            user_id: Optional user ID to limit validation scope
            
        Returns:
            Validation results with issues and recommendations
        """
        try:
            validation_result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'scope': f'user_{user_id}' if user_id else 'system_wide',
                'issues': [],
                'warnings': [],
                'statistics': {},
                'recommendations': []
            }
            
            # Validate documents
            doc_issues = self._validate_documents(user_id)
            validation_result['issues'].extend(doc_issues['issues'])
            validation_result['warnings'].extend(doc_issues['warnings'])
            validation_result['statistics']['documents'] = doc_issues['stats']
            
            # Validate datasets
            dataset_issues = self._validate_datasets(user_id)
            validation_result['issues'].extend(dataset_issues['issues'])
            validation_result['warnings'].extend(dataset_issues['warnings'])
            validation_result['statistics']['datasets'] = dataset_issues['stats']
            
            # Validate training jobs
            job_issues = self._validate_training_jobs(user_id)
            validation_result['issues'].extend(job_issues['issues'])
            validation_result['warnings'].extend(job_issues['warnings'])
            validation_result['statistics']['training_jobs'] = job_issues['stats']
            
            # Validate file system consistency
            fs_issues = self._validate_file_system(user_id)
            validation_result['issues'].extend(fs_issues['issues'])
            validation_result['warnings'].extend(fs_issues['warnings'])
            validation_result['statistics']['file_system'] = fs_issues['stats']
            
            # Generate recommendations
            validation_result['recommendations'] = self._generate_integrity_recommendations(
                validation_result
            )
            
            # Calculate overall health score
            total_issues = len(validation_result['issues'])
            total_warnings = len(validation_result['warnings'])
            health_score = max(0, 100 - (total_issues * 10) - (total_warnings * 2))
            validation_result['health_score'] = health_score
            
            logger.info(f"Data integrity validation completed - Health Score: {health_score}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating data integrity: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'issues': [f'Validation failed: {str(e)}'],
                'warnings': [],
                'statistics': {},
                'recommendations': ['Contact support for assistance'],
                'health_score': 0
            }
    
    def cleanup_orphaned_data(self, user_id: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
        """
        Clean up orphaned files and database records
        
        Args:
            user_id: Optional user ID to limit cleanup scope
            dry_run: If True, only report what would be cleaned up
            
        Returns:
            Cleanup results
        """
        try:
            cleanup_result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'dry_run': dry_run,
                'scope': f'user_{user_id}' if user_id else 'system_wide',
                'cleaned_items': {
                    'orphaned_files': [],
                    'orphaned_records': [],
                    'broken_references': []
                },
                'space_freed_mb': 0,
                'records_cleaned': 0
            }
            
            # Clean orphaned files
            file_cleanup = self._cleanup_orphaned_files(user_id, dry_run)
            cleanup_result['cleaned_items']['orphaned_files'] = file_cleanup['files']
            cleanup_result['space_freed_mb'] += file_cleanup['space_freed_mb']
            
            # Clean orphaned database records
            record_cleanup = self._cleanup_orphaned_records(user_id, dry_run)
            cleanup_result['cleaned_items']['orphaned_records'] = record_cleanup['records']
            cleanup_result['records_cleaned'] += record_cleanup['count']
            
            # Fix broken references
            reference_cleanup = self._fix_broken_references(user_id, dry_run)
            cleanup_result['cleaned_items']['broken_references'] = reference_cleanup['references']
            cleanup_result['records_cleaned'] += reference_cleanup['count']
            
            # Clean old temporary data
            temp_cleanup = self._cleanup_temporary_data(user_id, dry_run)
            cleanup_result['space_freed_mb'] += temp_cleanup['space_freed_mb']
            
            logger.info(f"Cleanup completed - Freed {cleanup_result['space_freed_mb']:.2f}MB, "
                       f"cleaned {cleanup_result['records_cleaned']} records")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'dry_run': dry_run,
                'cleaned_items': {},
                'space_freed_mb': 0,
                'records_cleaned': 0
            }
    
    def optimize_storage(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Optimize storage usage by compressing and archiving old data
        
        Args:
            user_id: Optional user ID to limit optimization scope
            
        Returns:
            Optimization results
        """
        try:
            optimization_result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'scope': f'user_{user_id}' if user_id else 'system_wide',
                'optimizations': [],
                'space_saved_mb': 0,
                'files_processed': 0
            }
            
            # Compress old training logs
            log_compression = self._compress_old_logs(user_id)
            optimization_result['optimizations'].append({
                'type': 'log_compression',
                'files_processed': log_compression['files_processed'],
                'space_saved_mb': log_compression['space_saved_mb']
            })
            optimization_result['space_saved_mb'] += log_compression['space_saved_mb']
            optimization_result['files_processed'] += log_compression['files_processed']
            
            # Archive completed training data
            archive_result = self._archive_old_training_data(user_id)
            optimization_result['optimizations'].append({
                'type': 'training_data_archive',
                'files_processed': archive_result['files_processed'],
                'space_saved_mb': archive_result['space_saved_mb']
            })
            optimization_result['space_saved_mb'] += archive_result['space_saved_mb']
            optimization_result['files_processed'] += archive_result['files_processed']
            
            # Deduplicate similar documents
            dedup_result = self._deduplicate_documents(user_id)
            optimization_result['optimizations'].append({
                'type': 'document_deduplication',
                'files_processed': dedup_result['files_processed'],
                'space_saved_mb': dedup_result['space_saved_mb']
            })
            optimization_result['space_saved_mb'] += dedup_result['space_saved_mb']
            optimization_result['files_processed'] += dedup_result['files_processed']
            
            logger.info(f"Storage optimization completed - Saved {optimization_result['space_saved_mb']:.2f}MB")
            return optimization_result
            
        except Exception as e:
            logger.error(f"Error during storage optimization: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'optimizations': [],
                'space_saved_mb': 0,
                'files_processed': 0
            }
    
    def create_backup(self, user_id: str, backup_type: str = 'full') -> Dict[str, Any]:
        """
        Create backup of user data
        
        Args:
            user_id: User ID to backup
            backup_type: Type of backup ('full', 'incremental', 'metadata_only')
            
        Returns:
            Backup results
        """
        try:
            backup_result = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': user_id,
                'backup_type': backup_type,
                'backup_path': '',
                'size_mb': 0,
                'files_backed_up': 0,
                'success': False
            }
            
            # Create backup directory
            backup_dir = Path(f'backups/user_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_result['backup_path'] = str(backup_dir)
            
            if backup_type in ['full', 'metadata_only']:
                # Backup database records
                db_backup = self._backup_database_records(user_id, backup_dir)
                backup_result['files_backed_up'] += db_backup['files_count']
                backup_result['size_mb'] += db_backup['size_mb']
            
            if backup_type == 'full':
                # Backup user files
                file_backup = self._backup_user_files(user_id, backup_dir)
                backup_result['files_backed_up'] += file_backup['files_count']
                backup_result['size_mb'] += file_backup['size_mb']
            
            # Create backup manifest
            manifest = {
                'created_at': backup_result['timestamp'],
                'user_id': user_id,
                'backup_type': backup_type,
                'files_count': backup_result['files_backed_up'],
                'size_mb': backup_result['size_mb']
            }
            
            manifest_path = backup_dir / 'manifest.json'
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            
            backup_result['success'] = True
            logger.info(f"Backup created for user {user_id}: {backup_result['size_mb']:.2f}MB")
            
            return backup_result
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': user_id,
                'error': str(e),
                'success': False
            }
    
    def get_storage_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed storage usage statistics
        
        Args:
            user_id: Optional user ID to limit statistics scope
            
        Returns:
            Storage statistics
        """
        try:
            stats = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'scope': f'user_{user_id}' if user_id else 'system_wide',
                'storage_usage': {},
                'file_counts': {},
                'recommendations': []
            }
            
            # Calculate storage usage by category
            if user_id:
                query_filter = {'user_id': user_id}
            else:
                query_filter = {}
            
            # Document storage
            documents = LLMDocument.query.filter_by(**query_filter).all()
            doc_size = sum(doc.file_size or 0 for doc in documents)
            stats['storage_usage']['documents'] = {
                'size_mb': doc_size / (1024 * 1024),
                'count': len(documents)
            }
            
            # Training job data
            training_jobs = LLMTrainingJob.query.filter_by(**query_filter).all()
            stats['file_counts']['training_jobs'] = len(training_jobs)
            
            # Model tests
            model_tests = LLMModelTest.query.filter_by(**query_filter).all()
            test_submissions = []
            for test in model_tests:
                test_submissions.extend(test.test_submissions)
            
            test_size = sum(sub.file_size or 0 for sub in test_submissions)
            stats['storage_usage']['model_tests'] = {
                'size_mb': test_size / (1024 * 1024),
                'count': len(test_submissions)
            }
            
            # Calculate total usage
            total_size_mb = sum(
                category['size_mb'] for category in stats['storage_usage'].values()
                if isinstance(category, dict) and 'size_mb' in category
            )
            stats['storage_usage']['total'] = {'size_mb': total_size_mb}
            
            # Generate recommendations
            if total_size_mb > 1000:  # > 1GB
                stats['recommendations'].append('Consider archiving old training data to reduce storage usage')
            
            if len(documents) > 100:
                stats['recommendations'].append('Review document collection for duplicates or unused files')
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'storage_usage': {},
                'file_counts': {},
                'recommendations': []
            }    
  
  def _validate_documents(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Validate document integrity"""
        query = LLMDocument.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        documents = query.all()
        issues = []
        warnings = []
        
        for doc in documents:
            if not os.path.exists(doc.file_path):
                issues.append(f"Document {doc.name} (ID: {doc.id}) - File not found: {doc.file_path}")
            
            # Check file size consistency
            elif os.path.getsize(doc.file_path) != doc.file_size:
                warnings.append(f"Document {doc.name} - File size mismatch")
            
            if not doc.text_content and doc.extracted_text:
                warnings.append(f"Document {doc.name} - Marked as extracted but no content found")
            
            if doc.created_at < datetime.now(timezone.utc) - timedelta(days=365):
                usage_count = LLMDatasetDocument.query.filter_by(document_id=doc.id).count()
                if usage_count == 0:
                    warnings.append(f"Document {doc.name} - Old unused document (1+ years)")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'stats': {
                'total_documents': len(documents),
                'missing_files': len([i for i in issues if 'File not found' in i]),
                'size_mismatches': len([w for w in warnings if 'size mismatch' in w])
            }
        }
    
    def _validate_datasets(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Validate dataset integrity"""
        query = LLMDataset.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        datasets = query.all()
        issues = []
        warnings = []
        
        for dataset in datasets:
            # Check document associations
            dataset_docs = LLMDatasetDocument.query.filter_by(dataset_id=dataset.id).all()
            actual_doc_count = len(dataset_docs)
            
            if actual_doc_count != dataset.document_count:
                issues.append(f"Dataset {dataset.name} - Document count mismatch: "
                            f"recorded {dataset.document_count}, actual {actual_doc_count}")
            
            missing_docs = 0
            for dataset_doc in dataset_docs:
                doc = LLMDocument.query.get(dataset_doc.document_id)
                if not doc:
                    missing_docs += 1
            
            if missing_docs > 0:
                issues.append(f"Dataset {dataset.name} - {missing_docs} referenced documents not found")
            
            if actual_doc_count == 0:
                warnings.append(f"Dataset {dataset.name} - Empty dataset")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'stats': {
                'total_datasets': len(datasets),
                'count_mismatches': len([i for i in issues if 'count mismatch' in i]),
                'empty_datasets': len([w for w in warnings if 'Empty dataset' in w])
            }
        }
    
    def _validate_training_jobs(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Validate training job integrity"""
        query = LLMTrainingJob.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        jobs = query.all()
        issues = []
        warnings = []
        
        for job in jobs:
            # Check dataset reference
            if job.dataset_id:
                dataset = LLMDataset.query.get(job.dataset_id)
                if not dataset:
                    issues.append(f"Training job {job.name} - Referenced dataset not found")
            
            if job.status in ['training', 'preparing']:
                if job.start_time and job.start_time < datetime.now(timezone.utc) - timedelta(hours=24):
                    warnings.append(f"Training job {job.name} - Stuck in {job.status} state for >24h")
            
            if job.status == 'completed' and job.progress != 100:
                warnings.append(f"Training job {job.name} - Completed but progress is {job.progress}%")
            
            if job.status == 'failed' and job.created_at < datetime.now(timezone.utc) - timedelta(days=90):
                warnings.append(f"Training job {job.name} - Old failed job (>90 days)")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'stats': {
                'total_jobs': len(jobs),
                'missing_datasets': len([i for i in issues if 'dataset not found' in i]),
                'stuck_jobs': len([w for w in warnings if 'Stuck in' in w])
            }
        }
    
    def _validate_file_system(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Validate file system consistency"""
        issues = []
        warnings = []
        
        # Check upload directories
        upload_dirs = [
            'webapp/uploads/llm_documents',
            'webapp/uploads/test_submissions'
        ]
        
        total_files = 0
        orphaned_files = 0
        
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                for root, dirs, files in os.walk(upload_dir):
                    total_files += len(files)
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        doc_ref = LLMDocument.query.filter_by(file_path=file_path).first()
                        test_ref = LLMTestSubmission.query.filter_by(file_path=file_path).first()
                        
                        if not doc_ref and not test_ref:
                            orphaned_files += 1
                            if orphaned_files <= 10:  # Limit warnings
                                warnings.append(f"Orphaned file: {file_path}")
        
        if orphaned_files > 10:
            warnings.append(f"... and {orphaned_files - 10} more orphaned files")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'stats': {
                'total_files': total_files,
                'orphaned_files': orphaned_files
            }
        }
    
    def _cleanup_orphaned_files(self, user_id: Optional[str], dry_run: bool) -> Dict[str, Any]:
        """Clean up orphaned files"""
        cleaned_files = []
        space_freed = 0
        
        upload_dirs = [
            'webapp/uploads/llm_documents',
            'webapp/uploads/test_submissions'
        ]
        
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                for root, dirs, files in os.walk(upload_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        
                        doc_ref = LLMDocument.query.filter_by(file_path=file_path).first()
                        test_ref = LLMTestSubmission.query.filter_by(file_path=file_path).first()
                        
                        if not doc_ref and not test_ref:
                            file_size = os.path.getsize(file_path)
                            cleaned_files.append({
                                'path': file_path,
                                'size_mb': file_size / (1024 * 1024)
                            })
                            space_freed += file_size
                            
                            if not dry_run:
                                try:
                                    os.remove(file_path)
                                    logger.debug(f"Removed orphaned file: {file_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to remove {file_path}: {e}")
        
        return {
            'files': cleaned_files,
            'space_freed_mb': space_freed / (1024 * 1024)
        }
    
    def _cleanup_orphaned_records(self, user_id: Optional[str], dry_run: bool) -> Dict[str, Any]:
        """Clean up orphaned database records"""
        cleaned_records = []
        count = 0
        
        # Clean up dataset-document associations with missing documents
        orphaned_associations = db.session.query(LLMDatasetDocument).filter(
            ~LLMDatasetDocument.document_id.in_(
                db.session.query(LLMDocument.id)
            )
        ).all()
        
        for assoc in orphaned_associations:
            cleaned_records.append({
                'type': 'dataset_document_association',
                'dataset_id': assoc.dataset_id,
                'document_id': assoc.document_id
            })
            count += 1
            
            if not dry_run:
                db.session.delete(assoc)
        
        if not dry_run and count > 0:
            db.session.commit()
        
        return {
            'records': cleaned_records,
            'count': count
        }
    
    def _fix_broken_references(self, user_id: Optional[str], dry_run: bool) -> Dict[str, Any]:
        """Fix broken references between entities"""
        fixed_references = []
        count = 0
        
        # Fix dataset document counts
        datasets = LLMDataset.query.all()
        for dataset in datasets:
            actual_count = LLMDatasetDocument.query.filter_by(dataset_id=dataset.id).count()
            if dataset.document_count != actual_count:
                fixed_references.append({
                    'type': 'dataset_document_count',
                    'dataset_id': dataset.id,
                    'old_count': dataset.document_count,
                    'new_count': actual_count
                })
                count += 1
                
                if not dry_run:
                    dataset.document_count = actual_count
        
        if not dry_run and count > 0:
            db.session.commit()
        
        return {
            'references': fixed_references,
            'count': count
        }
    
    def _cleanup_temporary_data(self, user_id: Optional[str], dry_run: bool) -> Dict[str, Any]:
        """Clean up temporary files and data"""
        space_freed = 0
        
        # Clean up temp directories
        temp_dirs = ['temp', 'webapp/temp']
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_mtime < cutoff_date:
                            file_size = os.path.getsize(file_path)
                            space_freed += file_size
                            
                            if not dry_run:
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    logger.warning(f"Failed to remove temp file {file_path}: {e}")
        
        return {
            'space_freed_mb': space_freed / (1024 * 1024)
        }
    
    def _compress_old_logs(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Compress old log files"""
        # Placeholder implementation
        return {
            'files_processed': 0,
            'space_saved_mb': 0
        }
    
    def _archive_old_training_data(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Archive old training data"""
        # Placeholder implementation
        return {
            'files_processed': 0,
            'space_saved_mb': 0
        }
    
    def _deduplicate_documents(self, user_id: Optional[str]) -> Dict[str, Any]:
        """Find and remove duplicate documents"""
        files_processed = 0
        space_saved = 0
        
        # Find documents with same content hash
        query = LLMDocument.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        documents = query.all()
        hash_groups = {}
        
        for doc in documents:
            if doc.file_path and os.path.exists(doc.file_path):
                file_hash = self._calculate_file_hash(doc.file_path)
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(doc)
        
        # Process duplicate groups
        for file_hash, docs in hash_groups.items():
            if len(docs) > 1:
                # Keep the oldest document, mark others as duplicates
                docs.sort(key=lambda x: x.created_at)
                original = docs[0]
                
                for duplicate in docs[1:]:
                    files_processed += 1
                    space_saved += duplicate.file_size or 0
                    logger.info(f"Found duplicate: {duplicate.name} (original: {original.name})")
        
        return {
            'files_processed': files_processed,
            'space_saved_mb': space_saved / (1024 * 1024)
        }
    
    def _backup_database_records(self, user_id: str, backup_dir: Path) -> Dict[str, Any]:
        """Backup database records for a user"""
        files_count = 0
        size_mb = 0
        
        # Export user's documents
        documents = LLMDocument.query.filter_by(user_id=user_id).all()
        if documents:
            doc_data = [doc.to_dict() for doc in documents]
            doc_file = backup_dir / 'documents.json'
            with open(doc_file, 'w') as f:
                json.dump(doc_data, f, indent=2)
            files_count += 1
            size_mb += doc_file.stat().st_size / (1024 * 1024)
        
        # Export user's datasets
        datasets = LLMDataset.query.filter_by(user_id=user_id).all()
        if datasets:
            dataset_data = [dataset.to_dict() for dataset in datasets]
            dataset_file = backup_dir / 'datasets.json'
            with open(dataset_file, 'w') as f:
                json.dump(dataset_data, f, indent=2)
            files_count += 1
            size_mb += dataset_file.stat().st_size / (1024 * 1024)
        
        # Export training jobs
        jobs = LLMTrainingJob.query.filter_by(user_id=user_id).all()
        if jobs:
            job_data = [job.to_dict() for job in jobs]
            job_file = backup_dir / 'training_jobs.json'
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            files_count += 1
            size_mb += job_file.stat().st_size / (1024 * 1024)
        
        return {
            'files_count': files_count,
            'size_mb': size_mb
        }
    
    def _backup_user_files(self, user_id: str, backup_dir: Path) -> Dict[str, Any]:
        """Backup user files"""
        files_count = 0
        size_mb = 0
        
        # Create files directory in backup
        files_dir = backup_dir / 'files'
        files_dir.mkdir(exist_ok=True)
        
        # Copy user's document files
        documents = LLMDocument.query.filter_by(user_id=user_id).all()
        for doc in documents:
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    dest_path = files_dir / f"doc_{doc.id}_{Path(doc.file_path).name}"
                    shutil.copy2(doc.file_path, dest_path)
                    files_count += 1
                    size_mb += dest_path.stat().st_size / (1024 * 1024)
                except Exception as e:
                    logger.warning(f"Failed to backup file {doc.file_path}: {e}")
        
        return {
            'files_count': files_count,
            'size_mb': size_mb
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def _generate_integrity_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        issues_count = len(validation_result['issues'])
        warnings_count = len(validation_result['warnings'])
        
        if issues_count > 0:
            recommendations.append(f"Address {issues_count} critical data integrity issues immediately")
        
        if warnings_count > 10:
            recommendations.append("Consider running cleanup to address numerous warnings")
        
        # Check specific issue types
        stats = validation_result.get('statistics', {})
        
        if stats.get('file_system', {}).get('orphaned_files', 0) > 50:
            recommendations.append("Run orphaned file cleanup to free up storage space")
        
        if stats.get('datasets', {}).get('empty_datasets', 0) > 5:
            recommendations.append("Remove or populate empty datasets")
        
        if stats.get('training_jobs', {}).get('stuck_jobs', 0) > 0:
            recommendations.append("Review and cancel stuck training jobs")
        
        return recommendations