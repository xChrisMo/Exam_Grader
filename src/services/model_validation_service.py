"""
Automated Model Validation Service
Requirements: 7.1, 7.2, 7.3, 7.5rfitting detection, and model certification
Requirements: 7.1, 7.2, 7.3, 7.5
"""

import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Op
from dataclasses impo
from sklearrix
from scipy import stats
ib
import os
from src.database.models import LLMTrainingJob, LLMModelTesn
port db
from utils.logger import logger

@dataclass
class ValidationConfig:
    """Configuration "
    overfitting_threshoy
 = True
    consistency_check_enabled: True
    min_test_sa 50
    confidence_thresh0.8
    performance_t
    cross_validation_fold int = 5

@dataclass
class ValidationResult:
    """Result of model validation"""
    model_id: str
    validation_id: str
    overall_score: float
    passed: bool
    issues: Liststr]
    recommendations: List[str]
    metrics: Dict[str, Any]
led'
    validae

class ModelValidationService:
    """Service fo"
    
    def __init__(self):
        self.validation_config = ValidationCon)
        self.validation_hist {}
        
    def validate_model(self, msult:
"
        try:
            logger.info(f"Starting validation for model {model_id}")
    
            if config:
                self.validation_config = config
        
            # Get model and tra data
            training_job = er(
                LLMTrainingJob.idel_id
            ).first()
            
            if not training_job:
                raise ValueError(f"Traini)
            
         eted':
    leted")
            
            # Initialize validation result
            ))}"
            issues = []
             = []
            metrics = {}
            
            # 1. Performance Valtion
            performance_score, perf_issues, perf_recommendations = selb)
            ues)
            recommendations.extend(tions)
            e
            
            # 2. Overfitting Detection
            overfitting_score, overfit_issues, overfit_recommendations = selg_job)
            issues.extend(overfit_issues)
            recommendations.extend(overfit_recommendations)
            metrics['overfitting'] = overfitting_score
            
            # 3. Bias Detection
            if self.validation_config.bias_detection_enabled:
                bias_score, bias_issues, bias_recommendations = self._detect_big_job)
                issues.extend(bias_issues)
            s)
                metrics['bias'] = bias
            
            heck
            if self.validation_config.consied:
                consistency_score,
                issues.extend(cons_issues)
                recommendations.extend(cons_ns)
                metrics['consistency'] = consistency_sore
            
            # 5. Model Architecture Validation
            architecture_score, arch_issues, arob)
            iues)
            )
            metrics['architecture'] = architecturscore

            overall_score = self._calculate_overall_score(metrics)
            
            el
            certification_leve)
            
            # Create 

                model_id=model_id,
                validation_id=validation_id,
            e,
                passed=certification_level != 'fled',
                issues=issues,
            ations,
                metrics=metrics,
                certification_level=certification_level,
                validated_at=dcnow()
            )
            
            # Save validation result
            self._save_validation_reslt)
            
            logger.info(f"Va
            return result
            
       as e:
      
            raise
    
    def _validate_performance(self, training_job: LLMTrainingJob) ]:
        """Validate model performance metrics"""
        issues = []
        recommendations = []
        
        try:
            metrics = training_job.me}
            final_accuracy = metrics0)
            final_loss = metrics.get('final_lnf'))
            
eshold
            performance_score = final_accuracy
            
            if final_accuracy < self.valida:
              })")
                recommendations.append("Consider increasing training epochs or improving training data quality")
            
            # Check loss convergence
            if final_loss > 1.0:
                issues.append(f"High fi)
                recommendations.append("Review learning rate and training)
            
            if np.ss):
                issues.append("Invalid metrics detected (NaN or infinite values)")
                recommendations.append("Check training stability and data preprocessing")
            
            retu
            
        except Exception as e:
            logger.error(f"Error in p

    def _detect_overfitting(self, training_job: LLMTrainingJob) -> Tuple[float, List[str], List[st
        """Detect overfitting in the trained model"""
        issues = []
        recommenda]
        
        try:
            metrics = training_job.metrics or {}
            train_accuracy = metrics.g
            val_accuracy = metric, 0)
            
            if train_accuracy == 0 or val_accuracy == 0:
                return 0.5, ["Insufficient data for ove"]
            
            # Calculate overfitting sc
            accuracy_gap = abs(tacy)
            overfitting_score = max(0.0, 1.0 - 
     
            if accuracy_gap >
                issues.append(f"Potential overfitting detected: train accuracy ({train_accuracy:.3f}) vs valid)

            # Check trainin
            training_history = metrics.get('training_his
            if training_history:
                val_losses = training_history.get('va)
                if len(val_losses 10:
             
                    if len(recent_val_losses) >= 5:
                        trend = np.polyfit(range(len(recent_val_losses)), recent_val_losses, 1)[0]
                 sing
                            issues.append("Validation loss increaing")
                            recommendations.append("Consider early stopping or reducing learning rate")

        except Exception as e:
            logger.error(f"Error in overfitting detection: {str(e)}")
            return "]
    
    def _detect_bias(self, training_job: LLM
        """Detect potential bias in model predictions"""
        issues = []
        recommendations = []
        
        try:
            # Get analysis
            model_tests = db.session.qur(
                L_job.id
            ).all()
            
            if not model_tests:
                return 0.5, ["No test data available for biaction"]
            
            bias_score = 1.0 etected
            
            for test in model_tests:
                if test.status
                    continue
                
                # Get tes
                submissions = db.session.query(LLMTestSubmission).filter(
                    LLMTestSubmission.test_id == test.id
                ).all()
                
                if len(submissions) < self.validation_config.min_test_samples:
                    continue
                
                # Analyze prediction consistency
                confidence_scores = [
                model_grades = [sub.model_grade for sub in submissions if ne]
                
                if confidence_scores and models:
       s
                    confidence_std = np.std(confidence_scores)
                    if confidence_std < 0.1:  # Verence
                        issues.append("Low ")
                        recommendations.append("Revy")
     8
               
                    grade_distribution = np.histogram(mo
                    if np.max(grade_distribution) / np.sum(grade_
                        issu")
                        recommendations.append("Ensure train
                        bias_score *= 0.7
            
            return bias_score, issues, rendations

            logger.error(f"Error in bias detection: {str(e)}")
            return 0.5, ["Bias detection failed"], ["Review mos"]
    
    def _check_consistency(s
        """Check model prediction consistency across t""
        issues = []
   = []
        
        try:
            model_tests =(
                LLMModelTest.model_id == training_job.id,
                LLMModelTest.status == 'completed'
            ).all()
            
            if len(model_tests) < 2:
  cking"]
            
      = []
            for test in model_tests:
                if test.results and test.results.get('accuracy'):
    '])
            
            if len(accuracy_scores) < 2:
                returics"]
            
            # Calculatce
            accuracy_std = np.std(accuracy_scores)
            accuracy_mean = np.mean(aes)
            
            # Consistency s
            if accuracy_mean > 0:
                coefficin

                consistency_score = 0.0
            
            if coefficient_of_variation > 0.2:  # 20% variation
                issues.append(f"High variance in test perform")
                recommendations.append("R
            
            if len(accuracy_s
                z_scores = np.abs(stats.zscore(accuracres))
                outliers = er
                
                if le > 0:
                    issue
                    recommendations.append("Investigate")

        except Exception as e:
            log
            return 0.5, ["Consistency check failed"], ["Review model test results"]
    
    def _validate_architecture(self, training_job: LLMTrainingJob) ->
        """Valida
        issues = []
        recommendations = []
        
        try:
            config = training_job.config or {}
            architecture_score = 1.0
            
            # Check tr
            epochs = config.get('epochs', 0)
            batch_size = config.get('batch_size', 0)
            learning_rate =)
            
            # Validate epochs
            if epochs < 5:
                issues.append(f"Very few training epochs ({epochs})")
                recommendance")
                architecture_score *= 0.8
            elif epochs > 100:
                issues.append(k")
      )
                architecture_score *= 0.9
            
            # Valide
 _size < 4:
                issues.append(f"Very small batch size ({batch_size}) may cause training instabty")
                recomme")
                architecture_score *= 0.8
            elif batch
                issues.append(f"Very large batch size ({batch")
                recommendations.append("Cons")
                architecture_score *= 0.9
            
            # Validate learnin
            if learning_rate > 0.01:
          ")
                recommendations.append("Consider reducing learning rate")
                architecture_score *= 0.8

                recommendations.append("Consider increasing learning rate")
                architec
            
            # Check model size rs
            max_length = config.get('ma, 0)
            if max_length > 2048:
                issues.append(f"Very long seque")
                recommendations.append("Consider 
                architecture_score *= 0.9
            
     ns
    
        except Exception as e:
            logger.error(f")
            return 0.5, ["Architecture validatio"]
    
    def _calculate_overall_score(self, me float:
        """Calculate overall validation score"
        weights = {
            'performance': 0.3,
            'overfitt
            'bias': 0.2,
            'consistency':
            'architecture': 0.1
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric, score in metrics.items():
            if metric in we
                weighted_score += score * weights[metric]
                total_weight += weights[metric]
        
        return weighted_score / total_weight i.0
    
    def _determine_certification_l -> str:
        """Determine certification level based on score and issues"""
        critical_issues = [issue for issue in issues if any(keyword in isower() 
                          for keyword in ['failed', 'inva
        
        if critical_issues or overall_score < 0.5:
            return 'd'
        elif overall_score >= 0.8 and len(issues) <= 2:
            return 'certified'
        else:
            return'
    
    def _save_validation_result(self, result: ValidationResult):
        """Save validation result to database/storage"""
        try:
            # Update training jo
            training_job = db.session.query(LLMT).filter(
                LLMTrainingJob.id == result.model_id
            ).first()
            
            if training_job:
    
                validation_results[result.validatiolt)
                training_job.validation_results = vali
                training_job.quality_score = result.overall_score
                
                db.session.commit()
                log)
            
        except Exception as e:
     ")

    def get_validati
        """Get validation history for a model"""
        try:
            training_job = db.session.query(
                LLMTrainingJob.id == model_id
            ).first()
            
            if not training_job or not training_job.validation_results:
                return []
            
        []
            for validation_data in training_job.vali
                # Conveesult
                validation_data['validated_at'] = datetime.fromisoformat(vat'])
                results.append(ValidationResult(**validatioa))
            
            return sorted(resultrue)
            
        except Exception as e:
            logger.error(f"Error getting validation histor(e)}")
            return []
    
    def batch_validate_models(self, model_ids:
        """
        results = {}
        
        for model_id in model_ids:
            try:
                )
                results[model_id] = result
            except Exception as e:
                logg")
                # Create failed result
                results[model_id] = Validation
                    model_id=model_id,
                    validation_id=f"failed_{int(datetime.
                    overall_score=0.0,
                    passed=False,
                    issues=[f"Validation failed: {str(e)}"],
       in"],
                    metrics={},
                    certification_leve'failed',
        
                )
        
     ults
    
    def get_certification_status(self, y]:
        """Get current certification sta"""
        try:
            traininglter(
                LLMTrainingJob.id == model_id
            ).first()
            
            if not training_job:
                return {'status': 'not_found', 'message': 'Mound'}
            
            if not training_job.validation_results:
                return {'status': 'not_validated', d'}
            
    lt
            latest_validation = max(training_job.validation_results.values(), 
                                  key=lambda x: d_at'])
            
            return {
        
                'certification_leveevel'],
                'overall_sco],
                'validated_at': latest_valida,
                'issues_count': len(latess']),
                'recommendations_count': le])
            }
            
        :
            logger.error(f")
            return {'statu
    
    def create_validation_workflow(self, > str:
        """Create a validation workflow for multiple m
        workflow_id = f"workflow_{int(datetime.ut"
        
        ue
        # For now, just return the workflow ID

        return workflow_id