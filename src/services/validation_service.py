"""
Validation Service

This service provides comprehensive validation for LLM training data,
configurations, and model outputs.
"""

import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from src.database.models import db, LLMDataset, LLMDocument, LLMTrainingJob, LLMDatasetDocument
from utils.logger import logger

class ValidationService:
    """Service for validating LLM training components"""
    
    def __init__(self):
        self.validation_rules = {
            'dataset': {
                'min_documents': 5,
                'min_total_words': 1000,
                'max_document_size_mb': 50,
                'supported_formats': ['.txt', '.pdf', '.docx', '.html', '.md', '.json']
            },
            'training_config': {
                'min_epochs': 1,
                'max_epochs': 100,
                'min_batch_size': 1,
                'max_batch_size': 64,
                'min_learning_rate': 0.00001,
                'max_learning_rate': 0.01,
                'min_max_tokens': 128,
                'max_max_tokens': 4096
            },
            'model_output': {
                'min_confidence_threshold': 0.1,
                'max_confidence_threshold': 1.0,
                'required_metrics': ['accuracy', 'loss']
            }
        }
    
    def validate_dataset_integrity(self, dataset_id: str) -> Dict[str, Any]:
        """
        Validate dataset integrity and quality
        
        Args:
            dataset_id: ID of the dataset to validate
            
        Returns:
            Validation results with issues and recommendations
        """
        try:
            # Get dataset
            dataset = db.session.get(LLMDataset, dataset_id)
            if not dataset:
                return {
                    'valid': False,
                    'errors': ['Dataset not found'],
                    'warnings': [],
                    'recommendations': [],
                    'score': 0.0
                }
            
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'recommendations': [],
                'score': 0.0,
                'details': {
                    'document_analysis': {},
                    'content_analysis': {},
                    'quality_metrics': {}
                }
            }
            
            # Get dataset documents
            dataset_docs = LLMDatasetDocument.query.filter_by(dataset_id=dataset_id).all()
            documents = [db.session.get(LLMDocument, dd.document_id) for dd in dataset_docs]
            documents = [doc for doc in documents if doc is not None]
            
            # Validate document count
            doc_count = len(documents)
            min_docs = self.validation_rules['dataset']['min_documents']
            
            if doc_count < min_docs:
                validation_result['errors'].append(
                    f'Dataset has only {doc_count} documents, minimum required is {min_docs}'
                )
                validation_result['valid'] = False
            elif doc_count < min_docs * 2:
                validation_result['warnings'].append(
                    f'Dataset has {doc_count} documents, consider adding more for better training'
                )
            
            # Validate total content
            total_words = sum(doc.word_count or 0 for doc in documents)
            min_words = self.validation_rules['dataset']['min_total_words']
            
            if total_words < min_words:
                validation_result['errors'].append(
                    f'Dataset has only {total_words} words, minimum required is {min_words}'
                )
                validation_result['valid'] = False
            
            # Validate individual documents
            doc_issues = self._validate_documents(documents)
            validation_result['details']['document_analysis'] = doc_issues
            
            # Add document-level errors and warnings
            for issue in doc_issues.get('errors', []):
                validation_result['errors'].append(f"Document issue: {issue}")
            
            for warning in doc_issues.get('warnings', []):
                validation_result['warnings'].append(f"Document warning: {warning}")
            
            # Content quality analysis
            content_analysis = self._analyze_content_quality(documents)
            validation_result['details']['content_analysis'] = content_analysis
            
            # Add content quality warnings
            if content_analysis['avg_quality_score'] < 0.5:
                validation_result['warnings'].append(
                    'Average content quality is low, consider improving document quality'
                )
            
            # Calculate overall validation score
            validation_result['score'] = self._calculate_dataset_score(
                doc_count, total_words, doc_issues, content_analysis
            )
            
            # Generate recommendations
            validation_result['recommendations'] = self._generate_dataset_recommendations(
                validation_result
            )
            
            logger.info(f"Dataset {dataset_id} validation completed - Score: {validation_result['score']:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating dataset {dataset_id}: {e}")
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}'],
                'warnings': [],
                'recommendations': ['Contact support for assistance'],
                'score': 0.0
            }
    
    def validate_training_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate training configuration parameters
        
        Args:
            config: Training configuration dictionary
            
        Returns:
            Validation results
        """
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'recommendations': [],
                'normalized_config': config.copy()
            }
            
            rules = self.validation_rules['training_config']
            
            # Validate epochs
            epochs = config.get('epochs', 10)
            if not isinstance(epochs, int) or epochs < rules['min_epochs']:
                validation_result['errors'].append(
                    f'Epochs must be at least {rules["min_epochs"]}, got {epochs}'
                )
                validation_result['valid'] = False
            elif epochs > rules['max_epochs']:
                validation_result['errors'].append(
                    f'Epochs cannot exceed {rules["max_epochs"]}, got {epochs}'
                )
                validation_result['valid'] = False
            elif epochs > 50:
                validation_result['warnings'].append(
                    f'High epoch count ({epochs}) may lead to overfitting'
                )
            
            # Validate batch size
            batch_size = config.get('batch_size', 8)
            if not isinstance(batch_size, int) or batch_size < rules['min_batch_size']:
                validation_result['errors'].append(
                    f'Batch size must be at least {rules["min_batch_size"]}, got {batch_size}'
                )
                validation_result['valid'] = False
            elif batch_size > rules['max_batch_size']:
                validation_result['errors'].append(
                    f'Batch size cannot exceed {rules["max_batch_size"]}, got {batch_size}'
                )
                validation_result['valid'] = False
            
            # Validate learning rate
            learning_rate = config.get('learning_rate', 0.0001)
            if not isinstance(learning_rate, (int, float)) or learning_rate < rules['min_learning_rate']:
                validation_result['errors'].append(
                    f'Learning rate must be at least {rules["min_learning_rate"]}, got {learning_rate}'
                )
                validation_result['valid'] = False
            elif learning_rate > rules['max_learning_rate']:
                validation_result['errors'].append(
                    f'Learning rate cannot exceed {rules["max_learning_rate"]}, got {learning_rate}'
                )
                validation_result['valid'] = False
            elif learning_rate > 0.001:
                validation_result['warnings'].append(
                    f'High learning rate ({learning_rate}) may cause training instability'
                )
            
            # Validate max tokens
            max_tokens = config.get('max_tokens', 512)
            if not isinstance(max_tokens, int) or max_tokens < rules['min_max_tokens']:
                validation_result['errors'].append(
                    f'Max tokens must be at least {rules["min_max_tokens"]}, got {max_tokens}'
                )
                validation_result['valid'] = False
            elif max_tokens > rules['max_max_tokens']:
                validation_result['errors'].append(
                    f'Max tokens cannot exceed {rules["max_max_tokens"]}, got {max_tokens}'
                )
                validation_result['valid'] = False
            
            # Validate model ID
            model_id = config.get('model_id', '')
            if not model_id or not isinstance(model_id, str):
                validation_result['errors'].append('Model ID is required and must be a string')
                validation_result['valid'] = False
            
            # Validate dataset ID
            dataset_id = config.get('dataset_id', '')
            if not dataset_id:
                validation_result['errors'].append('Dataset ID is required')
                validation_result['valid'] = False
            else:
                dataset_validation = self.validate_dataset_integrity(dataset_id)
                if not dataset_validation['valid']:
                    validation_result['errors'].append('Selected dataset is not valid for training')
                    validation_result['valid'] = False
                elif dataset_validation['warnings']:
                    validation_result['warnings'].extend([
                        f"Dataset warning: {w}" for w in dataset_validation['warnings']
                    ])
            
            # Generate configuration recommendations
            validation_result['recommendations'] = self._generate_config_recommendations(
                config, validation_result
            )
            
            # Normalize configuration values
            validation_result['normalized_config'].update({
                'epochs': int(epochs),
                'batch_size': int(batch_size),
                'learning_rate': float(learning_rate),
                'max_tokens': int(max_tokens)
            })
            
            logger.info(f"Training config validation completed - Valid: {validation_result['valid']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating training config: {e}")
            return {
                'valid': False,
                'errors': [f'Configuration validation error: {str(e)}'],
                'warnings': [],
                'recommendations': ['Check configuration format and try again'],
                'normalized_config': config
            }
    
    def validate_model_output(self, model_id: str, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate model output and performance metrics
        
        Args:
            model_id: ID of the model
            output_data: Model output data to validate
            
        Returns:
            Validation results
        """
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'recommendations': [],
                'quality_score': 0.0
            }
            
            # Check required metrics
            required_metrics = self.validation_rules['model_output']['required_metrics']
            for metric in required_metrics:
                if metric not in output_data:
                    validation_result['errors'].append(f'Missing required metric: {metric}')
                    validation_result['valid'] = False
            
            # Validate accuracy
            if 'accuracy' in output_data:
                accuracy = output_data['accuracy']
                if not isinstance(accuracy, (int, float)) or accuracy < 0 or accuracy > 1:
                    validation_result['errors'].append(
                        f'Accuracy must be between 0 and 1, got {accuracy}'
                    )
                    validation_result['valid'] = False
                elif accuracy < 0.5:
                    validation_result['warnings'].append(
                        f'Low accuracy ({accuracy:.3f}) indicates poor model performance'
                    )
                elif accuracy > 0.95:
                    validation_result['warnings'].append(
                        f'Very high accuracy ({accuracy:.3f}) may indicate overfitting'
                    )
            
            # Validate loss
            if 'loss' in output_data:
                loss = output_data['loss']
                if not isinstance(loss, (int, float)) or loss < 0:
                    validation_result['errors'].append(
                        f'Loss must be non-negative, got {loss}'
                    )
                    validation_result['valid'] = False
                elif loss > 2.0:
                    validation_result['warnings'].append(
                        f'High loss ({loss:.3f}) indicates poor model convergence'
                    )
            
            if 'confidence_scores' in output_data:
                confidence_scores = output_data['confidence_scores']
                if isinstance(confidence_scores, list):
                    invalid_scores = [s for s in confidence_scores if not (0 <= s <= 1)]
                    if invalid_scores:
                        validation_result['errors'].append(
                            f'Confidence scores must be between 0 and 1, found invalid: {invalid_scores[:5]}'
                        )
                        validation_result['valid'] = False
                    
                    avg_confidence = sum(confidence_scores) / len(confidence_scores)
                    if avg_confidence < 0.6:
                        validation_result['warnings'].append(
                            f'Low average confidence ({avg_confidence:.3f}) indicates model uncertainty'
                        )
            
            # Calculate quality score
            validation_result['quality_score'] = self._calculate_model_quality_score(output_data)
            
            # Generate recommendations
            validation_result['recommendations'] = self._generate_model_recommendations(
                output_data, validation_result
            )
            
            logger.info(f"Model {model_id} output validation completed - Quality: {validation_result['quality_score']:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating model output: {e}")
            return {
                'valid': False,
                'errors': [f'Model output validation error: {str(e)}'],
                'warnings': [],
                'recommendations': ['Check model output format and try again'],
                'quality_score': 0.0
            }
    
    def check_data_quality(self, documents: List[str]) -> Dict[str, Any]:
        """
        Check quality of training documents
        
        Args:
            documents: List of document IDs or content
            
        Returns:
            Data quality analysis
        """
        try:
            quality_result = {
                'overall_quality': 'good',
                'quality_score': 0.0,
                'issues': [],
                'recommendations': [],
                'document_scores': []
            }
            
            if isinstance(documents[0], str) and len(documents[0]) == 36:
                # Document IDs provided
                doc_objects = [db.session.get(LLMDocument, doc_id) for doc_id in documents]
                doc_objects = [doc for doc in doc_objects if doc is not None]
            else:
                # Assume document content provided
                doc_objects = documents
            
            if not doc_objects:
                quality_result['overall_quality'] = 'poor'
                quality_result['issues'].append('No valid documents found')
                return quality_result
            
            total_score = 0.0
            document_scores = []
            
            for i, doc in enumerate(doc_objects):
                if hasattr(doc, 'text_content'):
                    content = doc.text_content or ''
                    word_count = doc.word_count or 0
                else:
                    content = str(doc)
                    word_count = len(content.split())
                
                doc_score = self._calculate_document_quality_score(content, word_count)
                document_scores.append({
                    'document_index': i,
                    'score': doc_score,
                    'word_count': word_count,
                    'issues': self._identify_document_issues(content)
                })
                total_score += doc_score
            
            # Calculate overall quality
            quality_result['quality_score'] = total_score / len(document_scores)
            quality_result['document_scores'] = document_scores
            
            # Determine overall quality level
            if quality_result['quality_score'] >= 0.8:
                quality_result['overall_quality'] = 'excellent'
            elif quality_result['quality_score'] >= 0.6:
                quality_result['overall_quality'] = 'good'
            elif quality_result['quality_score'] >= 0.4:
                quality_result['overall_quality'] = 'fair'
            else:
                quality_result['overall_quality'] = 'poor'
            
            # Identify common issues
            all_issues = []
            for doc_score in document_scores:
                all_issues.extend(doc_score['issues'])
            
            issue_counts = {}
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
            
            # Report issues that affect more than 20% of documents
            threshold = len(document_scores) * 0.2
            for issue, count in issue_counts.items():
                if count > threshold:
                    quality_result['issues'].append(f'{issue} (affects {count} documents)')
            
            # Generate recommendations
            quality_result['recommendations'] = self._generate_quality_recommendations(
                quality_result
            )
            
            logger.info(f"Data quality check completed - Score: {quality_result['quality_score']:.2f}")
            return quality_result
            
        except Exception as e:
            logger.error(f"Error checking data quality: {e}")
            return {
                'overall_quality': 'unknown',
                'quality_score': 0.0,
                'issues': [f'Quality check error: {str(e)}'],
                'recommendations': ['Unable to assess data quality'],
                'document_scores': []
            }
    
    def _validate_documents(self, documents: List[LLMDocument]) -> Dict[str, Any]:
        """Validate individual documents in a dataset"""
        issues = {
            'errors': [],
            'warnings': [],
            'document_details': []
        }
        
        max_size_mb = self.validation_rules['dataset']['max_document_size_mb']
        supported_formats = self.validation_rules['dataset']['supported_formats']
        
        for doc in documents:
            doc_issues = {
                'id': doc.id,
                'name': doc.name,
                'issues': []
            }
            
            # Check file size
            size_mb = (doc.file_size or 0) / (1024 * 1024)
            if size_mb > max_size_mb:
                doc_issues['issues'].append(f'File too large: {size_mb:.1f}MB > {max_size_mb}MB')
                issues['errors'].append(f'{doc.name}: File too large ({size_mb:.1f}MB)')
            
            # Check file format
            file_ext = f'.{doc.file_type}' if doc.file_type else ''
            if file_ext not in supported_formats:
                doc_issues['issues'].append(f'Unsupported format: {file_ext}')
                issues['warnings'].append(f'{doc.name}: Unsupported format ({file_ext})')
            
            # Check content extraction
            if not doc.extracted_text or not doc.text_content:
                doc_issues['issues'].append('No text content extracted')
                issues['warnings'].append(f'{doc.name}: No text content extracted')
            elif (doc.word_count or 0) < 10:
                doc_issues['issues'].append('Very short content')
                issues['warnings'].append(f'{doc.name}: Very short content ({doc.word_count} words)')
            
            # Check validation status
            if hasattr(doc, 'validation_status') and doc.validation_status == 'invalid':
                doc_issues['issues'].append('Document failed validation')
                issues['errors'].append(f'{doc.name}: Failed validation')
            
            issues['document_details'].append(doc_issues)
        
        return issues
    
    def _analyze_content_quality(self, documents: List[LLMDocument]) -> Dict[str, Any]:
        """Analyze content quality across documents"""
        if not documents:
            return {
                'avg_quality_score': 0.0,
                'quality_distribution': {},
                'content_metrics': {}
            }
        
        quality_scores = []
        total_words = 0
        total_chars = 0
        
        for doc in documents:
            if hasattr(doc, 'content_quality_score') and doc.content_quality_score is not None:
                quality_scores.append(doc.content_quality_score)
            else:
                # Calculate basic quality score
                content = doc.text_content or ''
                word_count = doc.word_count or 0
                quality_scores.append(self._calculate_document_quality_score(content, word_count))
            
            total_words += doc.word_count or 0
            total_chars += doc.character_count or 0
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Quality distribution
        quality_ranges = {'high': 0, 'medium': 0, 'low': 0}
        for score in quality_scores:
            if score >= 0.7:
                quality_ranges['high'] += 1
            elif score >= 0.4:
                quality_ranges['medium'] += 1
            else:
                quality_ranges['low'] += 1
        
        return {
            'avg_quality_score': avg_quality,
            'quality_distribution': quality_ranges,
            'content_metrics': {
                'total_documents': len(documents),
                'total_words': total_words,
                'total_characters': total_chars,
                'avg_words_per_doc': total_words / len(documents) if documents else 0,
                'avg_chars_per_doc': total_chars / len(documents) if documents else 0
            }
        }
    
    def _calculate_dataset_score(self, doc_count: int, total_words: int, 
                                doc_issues: Dict, content_analysis: Dict) -> float:
        """Calculate overall dataset quality score"""
        score = 0.0
        
        # Document count score (0-25 points)
        min_docs = self.validation_rules['dataset']['min_documents']
        if doc_count >= min_docs * 4:
            score += 25
        elif doc_count >= min_docs * 2:
            score += 20
        elif doc_count >= min_docs:
            score += 15
        else:
            score += max(0, (doc_count / min_docs) * 15)
        
        # Content volume score (0-25 points)
        min_words = self.validation_rules['dataset']['min_total_words']
        if total_words >= min_words * 10:
            score += 25
        elif total_words >= min_words * 5:
            score += 20
        elif total_words >= min_words:
            score += 15
        else:
            score += max(0, (total_words / min_words) * 15)
        
        # Document quality score (0-30 points)
        avg_quality = content_analysis.get('avg_quality_score', 0.0)
        score += avg_quality * 30
        
        # Issue penalty (0-20 points)
        error_count = len(doc_issues.get('errors', []))
        warning_count = len(doc_issues.get('warnings', []))
        
        issue_penalty = (error_count * 5) + (warning_count * 2)
        score += max(0, 20 - issue_penalty)
        
        return min(100.0, score) / 100.0
    
    def _calculate_document_quality_score(self, content: str, word_count: int) -> float:
        """Calculate quality score for a single document"""
        if not content or word_count == 0:
            return 0.0
        
        score = 0.0
        
        # Length score (0-30 points)
        if word_count >= 500:
            score += 30
        elif word_count >= 100:
            score += 20
        elif word_count >= 50:
            score += 15
        else:
            score += max(0, (word_count / 50) * 15)
        
        # Structure score (0-25 points)
        sentences = len(re.split(r'[.!?]+', content))
        if sentences >= 10:
            score += 25
        elif sentences >= 5:
            score += 20
        else:
            score += max(0, (sentences / 5) * 20)
        
        # Vocabulary diversity (0-25 points)
        words = content.lower().split()
        unique_words = len(set(words))
        if words:
            diversity = unique_words / len(words)
            score += diversity * 25
        
        # Language quality (0-20 points)
        if re.search(r'\b(the|and|of|to|a|in|is|it|you|that)\b', content.lower()):
            score += 20  # Contains common English words
        elif re.search(r'[a-zA-Z]', content):
            score += 10  # Contains letters
        
        return min(100.0, score) / 100.0
    
    def _identify_document_issues(self, content: str) -> List[str]:
        """Identify specific issues in document content"""
        issues = []
        
        if not content or not content.strip():
            issues.append('Empty content')
            return issues
        
        word_count = len(content.split())
        if word_count < 10:
            issues.append('Very short content')
        
        words = content.lower().split()
        if len(words) > 0:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            most_common_freq = max(word_freq.values())
            if most_common_freq > len(words) * 0.3:
                issues.append('Excessive word repetition')
        
        if not re.search(r'[.!?]', content):
            issues.append('No sentence punctuation')
        
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s.!?,-]', content)) / len(content)
        if special_char_ratio > 0.1:
            issues.append('High special character ratio')
        
        return issues
    
    def _calculate_model_quality_score(self, output_data: Dict[str, Any]) -> float:
        """Calculate model output quality score"""
        score = 0.0
        
        # Accuracy contribution (0-40 points)
        if 'accuracy' in output_data:
            accuracy = output_data['accuracy']
            if 0 <= accuracy <= 1:
                score += accuracy * 40
        
        # Loss contribution (0-30 points)
        if 'loss' in output_data:
            loss = output_data['loss']
            if loss >= 0:
                # Lower loss is better, normalize to 0-30 scale
                normalized_loss = max(0, min(1, 1 - (loss / 2.0)))
                score += normalized_loss * 30
        
        # Confidence contribution (0-30 points)
        if 'confidence_scores' in output_data:
            confidence_scores = output_data['confidence_scores']
            if isinstance(confidence_scores, list) and confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                score += avg_confidence * 30
        
        return min(100.0, score) / 100.0
    
    def _generate_dataset_recommendations(self, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for dataset improvement"""
        recommendations = []
        
        if validation_result['score'] < 0.6:
            recommendations.append('Dataset quality is below recommended threshold')
        
        if any('documents' in error for error in validation_result['errors']):
            recommendations.append('Add more documents to improve dataset size')
        
        if any('words' in error for error in validation_result['errors']):
            recommendations.append('Add more content or longer documents')
        
        content_analysis = validation_result['details'].get('content_analysis', {})
        if content_analysis.get('avg_quality_score', 0) < 0.5:
            recommendations.append('Improve document quality by adding well-structured content')
        
        quality_dist = content_analysis.get('quality_distribution', {})
        if quality_dist.get('low', 0) > quality_dist.get('high', 0):
            recommendations.append('Replace low-quality documents with higher-quality content')
        
        return recommendations
    
    def _generate_config_recommendations(self, config: Dict[str, Any], 
                                       validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for training configuration"""
        recommendations = []
        
        epochs = config.get('epochs', 10)
        batch_size = config.get('batch_size', 8)
        learning_rate = config.get('learning_rate', 0.0001)
        
        if epochs < 5:
            recommendations.append('Consider increasing epochs for better training convergence')
        elif epochs > 20:
            recommendations.append('Consider reducing epochs to prevent overfitting')
        
        if batch_size < 4:
            recommendations.append('Consider increasing batch size for more stable training')
        elif batch_size > 16:
            recommendations.append('Consider reducing batch size if experiencing memory issues')
        
        if learning_rate > 0.001:
            recommendations.append('Consider reducing learning rate for more stable training')
        elif learning_rate < 0.00005:
            recommendations.append('Consider increasing learning rate for faster convergence')
        
        return recommendations
    
    def _generate_model_recommendations(self, output_data: Dict[str, Any], 
                                      validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for model improvement"""
        recommendations = []
        
        accuracy = output_data.get('accuracy', 0)
        loss = output_data.get('loss', float('inf'))
        
        if accuracy < 0.6:
            recommendations.append('Model accuracy is low - consider more training data or different architecture')
        elif accuracy > 0.95:
            recommendations.append('Very high accuracy may indicate overfitting - validate on separate test set')
        
        if loss > 1.0:
            recommendations.append('High loss indicates poor convergence - consider adjusting learning rate')
        
        if 'confidence_scores' in output_data:
            confidence_scores = output_data['confidence_scores']
            if isinstance(confidence_scores, list) and confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                if avg_confidence < 0.6:
                    recommendations.append('Low confidence scores - model may need more training')
        
        return recommendations
    
    def _generate_quality_recommendations(self, quality_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations for data quality improvement"""
        recommendations = []
        
        if quality_result['overall_quality'] == 'poor':
            recommendations.append('Data quality is poor - consider replacing or improving documents')
        elif quality_result['overall_quality'] == 'fair':
            recommendations.append('Data quality is fair - some improvements recommended')
        
        for issue in quality_result['issues']:
            if 'short content' in issue.lower():
                recommendations.append('Add more detailed content to documents')
            elif 'repetition' in issue.lower():
                recommendations.append('Reduce repetitive content in documents')
            elif 'punctuation' in issue.lower():
                recommendations.append('Improve document formatting and punctuation')
        
        return recommendations