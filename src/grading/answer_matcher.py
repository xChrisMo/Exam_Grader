from typing import Dict, List, Tuple, Optional
import re
from difflib import SequenceMatcher

class AnswerMatcher:
    def __init__(self):
        self.similarity_threshold = 0.8  # Default threshold for answer matching

    def match_answers(self, 
                     questions: List[Dict], 
                     student_answers: List[Dict]) -> List[Dict]:
        """
        Match student answers with corresponding questions.
        
        Args:
            questions: List of question dictionaries with 'number', 'text', 'model_answer', and 'marks'
            student_answers: List of student answer dictionaries with 'number' and 'text'
            
        Returns:
            List of matched answers with question information
        """
        matched_answers = []
        unmatched_questions = questions.copy()
        
        # First pass: Exact number matching
        for answer in student_answers:
            question = self._find_question_by_number(answer['number'], unmatched_questions)
            if question:
                matched_answers.append({
                    'question_number': question['number'],
                    'question_text': question['text'],
                    'model_answer': question['model_answer'],
                    'student_answer': answer['text'],
                    'max_marks': question['marks'],
                    'match_confidence': 1.0
                })
                unmatched_questions.remove(question)
        
        # Second pass: Fuzzy matching for unmatched answers
        for answer in student_answers:
            if not any(a['question_number'] == answer['number'] for a in matched_answers):
                best_match = self._find_best_fuzzy_match(answer, unmatched_questions)
                if best_match:
                    question, confidence = best_match
                    if confidence >= self.similarity_threshold:
                        matched_answers.append({
                            'question_number': question['number'],
                            'question_text': question['text'],
                            'model_answer': question['model_answer'],
                            'student_answer': answer['text'],
                            'max_marks': question['marks'],
                            'match_confidence': confidence
                        })
                        unmatched_questions.remove(question)
        
        # Add unmatched questions with empty student answers
        for question in unmatched_questions:
            matched_answers.append({
                'question_number': question['number'],
                'question_text': question['text'],
                'model_answer': question['model_answer'],
                'student_answer': '',
                'max_marks': question['marks'],
                'match_confidence': 0.0
            })
        
        # Sort by question number
        matched_answers.sort(key=lambda x: int(x['question_number']))
        return matched_answers

    def _find_question_by_number(self, 
                               answer_number: str, 
                               questions: List[Dict]) -> Optional[Dict]:
        """Find a question by exact number match."""
        for question in questions:
            if question['number'] == answer_number:
                return question
        return None

    def _find_best_fuzzy_match(self, 
                             answer: Dict, 
                             questions: List[Dict]) -> Optional[Tuple[Dict, float]]:
        """Find the best matching question using fuzzy matching."""
        best_match = None
        best_confidence = 0.0
        
        # Clean the answer text for comparison
        answer_text = self._clean_text(answer['text'])
        
        for question in questions:
            # Compare with question text
            question_text = self._clean_text(question['text'])
            confidence = self._calculate_similarity(answer_text, question_text)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = question
        
        if best_match and best_confidence >= self.similarity_threshold:
            return best_match, best_confidence
        return None

    def _clean_text(self, text: str) -> str:
        """Clean text for comparison by removing extra whitespace and special characters."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
        return text

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using SequenceMatcher."""
        return SequenceMatcher(None, text1, text2).ratio()

def match_answers(questions: List[Dict], student_answers: List[Dict]) -> List[Dict]:
    """Main function to match student answers with questions."""
    matcher = AnswerMatcher()
    return matcher.match_answers(questions, student_answers) 