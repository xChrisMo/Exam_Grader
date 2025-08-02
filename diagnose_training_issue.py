#!/usr/bin/env python3
"""
Diagnose Training Issue

This script helps diagnose why training jobs are completing with 0% accuracy.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.app import create_app

def diagnose_training_issue():
    """Diagnose the training issue"""
    print("🔍 Diagnosing Training Issue...")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            from src.database.models import LLMTrainingJob, LLMDataset, LLMDocument
            
            print("\n📊 Checking Recent Training Jobs...")
            
            # Get the most recent training job
            recent_job = LLMTrainingJob.query.order_by(LLMTrainingJob.created_at.desc()).first()
            
            if not recent_job:
                print("   ❌ No training jobs found")
                return False
            
            print(f"   📋 Most Recent Job: {recent_job.name}")
            print(f"   📊 Status: {recent_job.status}")
            print(f"   📈 Accuracy: {recent_job.accuracy * 100 if recent_job.accuracy else 0:.2f}%")
            print(f"   📉 Loss: {recent_job.loss if recent_job.loss else 'N/A'}")
            print(f"   🎯 Dataset ID: {recent_job.dataset_id}")
            
            # Check the dataset
            if recent_job.dataset_id:
                print(f"\n📚 Checking Dataset {recent_job.dataset_id}...")
                
                dataset = LLMDataset.query.get(recent_job.dataset_id)
                if dataset:
                    print(f"   📋 Dataset Name: {dataset.name}")
                    print(f"   📄 Document Count: {len(dataset.dataset_documents)}")
                    
                    # Check documents in the dataset
                    for dataset_doc in dataset.dataset_documents:
                        document = LLMDocument.query.get(dataset_doc.document_id)
                        if document:
                            print(f"   📄 Document: {document.name}")
                            print(f"   📝 Content Length: {len(document.text_content) if document.text_content else 0} characters")
                            print(f"   📊 Word Count: {document.word_count if document.word_count else 0} words")
                            
                            # Check if content looks like it has questions
                            if document.text_content:
                                content_lower = document.text_content.lower()
                                question_indicators = ['question', '?', 'q1', 'q2', 'marks', 'score']
                                found_indicators = [ind for ind in question_indicators if ind in content_lower]
                                print(f"   🔍 Question Indicators Found: {found_indicators}")
                else:
                    print("   ❌ Dataset not found")
            
            # Check evaluation results
            if recent_job.evaluation_results:
                print(f"\n📊 Evaluation Results:")
                results = recent_job.evaluation_results
                for key, value in results.items():
                    print(f"   {key}: {value}")
            else:
                print("\n❌ No evaluation results found")
            
            # Check training metrics
            if recent_job.training_metrics:
                print(f"\n📈 Training Metrics:")
                metrics = recent_job.training_metrics
                for epoch, data in metrics.items():
                    if isinstance(data, dict):
                        accuracy = data.get('average_accuracy', 0)
                        print(f"   {epoch}: {accuracy:.2f}% accuracy")
            else:
                print("\n❌ No training metrics found")
            
            print("\n🔍 Potential Issues:")
            
            # Check for common issues
            issues_found = []
            
            if recent_job.accuracy == 0 or recent_job.accuracy is None:
                issues_found.append("Zero accuracy suggests grading service failure or no valid training data")
            
            if recent_job.loss == 1.0 or recent_job.loss is None:
                issues_found.append("Loss of 1.0 suggests no learning occurred")
            
            if not recent_job.evaluation_results:
                issues_found.append("Missing evaluation results")
            
            if not recent_job.training_metrics:
                issues_found.append("Missing training metrics")
            
            if issues_found:
                for i, issue in enumerate(issues_found, 1):
                    print(f"   {i}. {issue}")
            else:
                print("   ✅ No obvious issues detected")
            
            print("\n💡 Recommendations:")
            print("   1. Check if the training guide document contains clear question-answer pairs")
            print("   2. Verify that the LLM service is working properly")
            print("   3. Check if the grading service can process the training data")
            print("   4. Consider using a simpler training guide with clear Q&A format")
            
            return True
            
        except Exception as e:
            print(f"❌ Error diagnosing training issue: {e}")
            return False

if __name__ == "__main__":
    print("🔍 Training Issue Diagnostic Tool...")
    
    if diagnose_training_issue():
        print("\n✨ Diagnostic completed!")
        sys.exit(0)
    else:
        print("\n❌ Diagnostic failed!")
        sys.exit(1)