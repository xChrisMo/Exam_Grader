#!/usr/bin/env python3
"""
Test script for the LLM-based answer comparison functionality.
This script demonstrates how the system evaluates how closely a student's answer
matches the model answer in a marking guide.
"""

import os
import sys
from pathlib import Path
import json

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.services.llm_service import LLMService
from src.services.grading_service import GradingService
from utils.logger import logger

def test_direct_answer_comparison():
    """Test the LLM-based direct answer comparison functionality."""
    print("\n=== Testing Direct Answer Comparison ===")
    
    try:
        # Initialize LLM service with DeepSeek configuration
        llm_service = LLMService(
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            base_url=os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com')
        )
        
        # Example question and answers for testing
        question = "What is the capital of France and describe its significance as a cultural center?"
        
        model_answer = """
        The capital of France is Paris. It is one of the world's most significant cultural 
        centers, known for its museums like the Louvre and Musée d'Orsay, architectural 
        landmarks like the Eiffel Tower and Notre-Dame, and its contributions to art, 
        literature, fashion, and cuisine. Paris has a rich history dating back to ancient 
        times and has been a center for philosophical and political movements like the 
        Age of Enlightenment and the French Revolution. The city continues to be a global 
        hub for the arts, education, and international affairs.
        """
        
        # Test case 1: Very close answer
        test_answer_good = """
        Paris is the capital of France. It's considered one of the most important cultural 
        centers in the world. The city is famous for its museums including the Louvre, 
        architectural landmarks like the Eiffel Tower, and its contributions to art, fashion, 
        and food. Paris has been historically important in the development of philosophy, 
        politics, and the arts. It remains a major global city for culture and international 
        relations.
        """
        
        # Test case 2: Partially correct answer
        test_answer_partial = """
        Paris is the capital of France. It has the Eiffel Tower and good food. It's a 
        popular tourist destination in Europe.
        """
        
        # Test case 3: Incorrect answer
        test_answer_incorrect = """
        The capital of France is Lyon. It's an important economic center with 
        beautiful architecture.
        """
        
        # Test case 4: Off-topic answer
        test_answer_offtopic = """
        France is located in Western Europe and shares borders with several countries
        including Germany, Italy, and Spain. It has a population of about 67 million people.
        """
        
        test_cases = [
            ("Good Answer", test_answer_good),
            ("Partial Answer", test_answer_partial),
            ("Incorrect Answer", test_answer_incorrect),
            ("Off-topic Answer", test_answer_offtopic)
        ]
        
        results = []
        
        # Use system prompt for LLM-based answer evaluation
        system_prompt = """
        You are an expert educational grader with years of experience in assessing student work. 
        Your task is to evaluate a student's answer against a model answer from a marking guide.
        
        Evaluate the student's answer based on the following criteria:
        1. Content Accuracy (40%): Correctness of facts, concepts, or procedures
        2. Completeness (30%): Inclusion of all required information or steps
        3. Understanding (20%): Demonstrated comprehension of underlying principles
        4. Clarity (10%): Clear and coherent expression of ideas
        
        IMPORTANT GUIDELINES:
        - Be fair and objective in your assessment
        - Consider partial credit for partially correct answers
        - Identify specific points where the student's answer matches or differs from the model answer
        - Provide constructive feedback that helps the student understand what they did well and what they missed
        - Your feedback should be specific and directly reference the student's response
        - Look for semantic similarity, not just exact word matches
        - Consider alternative correct approaches that might differ from the model answer
        - Be lenient on minor formatting differences or slight wording variations
        
        Output in JSON format:
        {
            "score": <numeric_score>,
            "percentage": <percent_of_max_score>,
            "feedback": "<detailed_feedback_with_specifics>",
            "strengths": ["<specific_strength1>", "<specific_strength2>", ...],
            "weaknesses": ["<specific_weakness1>", "<specific_weakness2>", ...],
            "improvement_suggestions": ["<specific_suggestion1>", "<specific_suggestion2>", ...],
            "key_points": {
                "matched": ["<specific_point1>", "<specific_point2>", ...],
                "missed": ["<specific_point1>", "<specific_point2>", ...],
                "partially_matched": ["<specific_point1>", "<specific_point2>", ...]
            },
            "grading_breakdown": {
                "content_accuracy": {
                    "score": <0-10>,
                    "comments": "<specific_comments>"
                },
                "completeness": {
                    "score": <0-10>,
                    "comments": "<specific_comments>"
                },
                "understanding": {
                    "score": <0-10>,
                    "comments": "<specific_comments>"
                },
                "clarity": {
                    "score": <0-10>,
                    "comments": "<specific_comments>"
                }
            }
        }
        """
        
        max_score = 10
        
        # Run each test case
        for test_name, test_answer in test_cases:
            print(f"\n--- Testing {test_name} ---")
            
            user_prompt = f"""
            Question: {question}
            
            Model Answer from Marking Guide: 
            {model_answer}
            
            Student's Answer: 
            {test_answer}
            
            Maximum Score: {max_score}
            
            Please evaluate how closely the student's answer matches the model answer and assign a score out of {max_score}.
            Consider both the content and the demonstrated understanding. Provide detailed feedback explaining your scoring.
            """
            
            try:
                # Direct LLM call for evaluation
                response = llm_service.client.chat.completions.create(
                    model=llm_service.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                result = response.choices[0].message.content
                parsed = json.loads(result)
                
                # Extract scoring information
                score = float(parsed.get("score", 0))
                score = min(score, max_score)  # Ensure score doesn't exceed max
                
                feedback = parsed.get("feedback", "")
                strengths = parsed.get("strengths", [])
                weaknesses = parsed.get("weaknesses", [])
                improvement_suggestions = parsed.get("improvement_suggestions", [])
                
                # Get key points information
                key_points = parsed.get("key_points", {})
                matched_points = key_points.get("matched", [])
                missed_points = key_points.get("missed", [])
                
                # Get detailed breakdown
                grading_breakdown = parsed.get("grading_breakdown", {})
                
                # Calculate percentage
                percent = (score / max_score) * 100
                
                # Print results
                print(f"Score: {score}/{max_score} ({percent:.1f}%)")
                
                # Determine letter grade
                letter_grade = "A+" if percent >= 97 else \
                               "A" if percent >= 93 else \
                               "A-" if percent >= 90 else \
                               "B+" if percent >= 87 else \
                               "B" if percent >= 83 else \
                               "B-" if percent >= 80 else \
                               "C+" if percent >= 77 else \
                               "C" if percent >= 73 else \
                               "C-" if percent >= 70 else \
                               "D+" if percent >= 67 else \
                               "D" if percent >= 63 else \
                               "D-" if percent >= 60 else "F"
                
                print(f"Letter Grade: {letter_grade}")
                print(f"Feedback: {feedback[:150]}...")
                
                if strengths:
                    print("\nStrengths:")
                    for point in strengths[:3]:
                        print(f"- {point}")
                
                if weaknesses:
                    print("\nWeaknesses:")
                    for point in weaknesses[:3]:
                        print(f"- {point}")
                
                if matched_points:
                    print("\nMatched points:")
                    for point in matched_points[:3]:
                        print(f"- {point}")
                
                if missed_points:
                    print("\nMissed points:")
                    for point in missed_points[:3]:
                        print(f"- {point}")
                
                # Save to results for comparison
                results.append({
                    "test_name": test_name,
                    "score": score,
                    "max_score": max_score,
                    "percent": percent,
                    "letter_grade": letter_grade
                })
            
            except Exception as e:
                print(f"Error evaluating {test_name}: {str(e)}")
        
        # Print comparison summary
        print("\n=== Test Results Summary ===")
        for result in results:
            print(f"{result['test_name']}: {result['score']}/{result['max_score']} ({result['percent']:.1f}%) - {result['letter_grade']}")
        
        return True
    
    except Exception as e:
        print(f"\nDirect Answer Comparison Test: FAILED")
        print(f"Error: {str(e)}")
        return False

def main():
    """Run the test."""
    test_direct_answer_comparison()

if __name__ == "__main__":
    main() 