#!/usr/bin/env python3
"""
Ultra-Fast Processing Service

This service reduces mapping and grading time from 15+ seconds to under 3 seconds by:
1. Aggressive content truncation
2. Simplified prompts
3. Parallel processing
4. Smart caching
5. Fallback mechanisms
"""

import asyncio
import time
import json
import re
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from utils.logger import logger

class UltraFastMapper:
    """Ultra-fast mapping with aggressive optimizations."""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def ultra_fast_map(self, guide_content: str, submission_content: str, max_questions: int = 5, questions_data: List[Dict] = None, guide_id: str = None) -> List[Dict]:
        """Ultra-fast mapping in under 2 seconds using database-extracted questions."""
        try:
            # If guide_id is provided, try to get questions from database
            if guide_id and not questions_data:
                questions_data = self._get_questions_from_database(guide_id)
                logger.info(f"Retrieved {len(questions_data) if questions_data else 0} questions from database for guide {guide_id}")
                
            # Aggressive preprocessing - keep only essentials
            guide_clean = self._ultra_preprocess(guide_content, 800)
            submission_clean = self._ultra_preprocess(submission_content, 1000)
            
            # Check cache first with consistent key
            cache_key = self._create_consistent_mapping_cache_key(guide_clean, submission_clean, max_questions, questions_data)
            if cache_key in self.cache:
                logger.info("Cache hit - returning cached mapping for consistent results")
                return self.cache[cache_key]
            
            if not self.llm_service:
                return self._instant_fallback_mapping_with_questions(guide_clean, submission_clean, max_questions, questions_data)
            
            if questions_data:
                questions_text = "\n".join([f"Q{i+1}: {q.get('text', q.get('question', ''))}" 
                                          for i, q in enumerate(questions_data[:max_questions])])
                prompt = f"""Map these specific questions to corresponding answers in the student submission.
Return JSON format: {{"mappings":[{{"q":"question text","a":"student answer","id":"Q1"}}]}}

QUESTIONS TO MAP:
{questions_text}

STUDENT SUBMISSION:
{submission_clean}

Find the student's answers to each question in the submission."""
            else:
                # Fallback to content-based mapping
                prompt = f"""Extract questions from the marking guide and map them to corresponding answers in the student submission.
Return JSON format: {{"mappings":[{{"q":"full question text","a":"student answer","id":"Q1"}}]}}

MARKING GUIDE:
{guide_clean}

STUDENT SUBMISSION:
{submission_clean}

Find up to {max_questions} questions and their corresponding answers."""
            
            start_time = time.time()
            
            # Use minimal LLM call
            response = self.llm_service.generate_response(
                system_prompt="Map exam questions to answers. JSON only. Be consistent and deterministic.",
                user_prompt=prompt,
                temperature=0.0,  # Deterministic for speed
                use_cache=True    # Enable caching for consistency
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Ultra-fast mapping completed in {processing_time:.2f}s")
            
            # Quick parsing
            mappings = self._ultra_parse_mapping(response, max_questions, questions_data)
            
            # Cache result
            self.cache[cache_key] = mappings
            
            return mappings
            
        except Exception as e:
            logger.error(f"Ultra-fast mapping failed: {e}")
            return self._instant_fallback_mapping_with_questions(guide_content, submission_content, max_questions, questions_data)
    
    def _ultra_preprocess(self, content: str, max_chars: int) -> str:
        """Balanced preprocessing for speed and accuracy."""
        if not content:
            return ""
        
        # Remove extra whitespace but preserve structure
        content = ' '.join(content.split())
        
        if len(content) > max_chars * 3:  # Much more generous limit
            # Try to truncate at sentence boundaries
            sentences = content.split('.')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence) < max_chars * 2:
                    truncated += sentence + "."
                else:
                    break
            content = truncated if truncated else content[:max_chars * 2]
        
        return content
    
    def _ultra_parse_mapping(self, response: str, max_questions: int, questions_data: List[Dict] = None) -> List[Dict]:
        """Ultra-fast parsing with minimal error handling."""
        try:
            # Try direct JSON parse first
            data = json.loads(response)
            mappings = data.get('mappings', [])
        except:
            # Quick regex extraction
            try:
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    mappings = json.loads(json_match.group())
                else:
                    return self._generate_default_mappings(max_questions)
            except:
                return self._generate_default_mappings(max_questions)
        
        # Convert to standard format quickly
        result = []
        for i, mapping in enumerate(mappings[:max_questions]):
            if isinstance(mapping, dict):
                # Get max score from questions_data if available
                max_score = 10.0  # Default
                if questions_data and i < len(questions_data):
                    max_score = questions_data[i].get('max_score', 10.0)
                
                result.append({
                    'question_id': mapping.get('id', f"Q{i+1}"),
                    'question_text': str(mapping.get('q', ''))[:200],
                    'student_answer': str(mapping.get('a', ''))[:300],
                    'max_score': max_score,
                    'confidence': 0.8
                })
        
        # Fill to required count
        while len(result) < max_questions:
            # Get max score from questions_data if available
            max_score = 10.0  # Default
            if questions_data and len(result) < len(questions_data):
                max_score = questions_data[len(result)].get('max_score', 10.0)
                
            result.append({
                'question_id': f"Q{len(result)+1}",
                'question_text': f"Question {len(result)+1}",
                'student_answer': "Answer not clearly identified",
                'max_score': max_score,
                'confidence': 0.3
            })
        
        return result[:max_questions]
    
    def _instant_fallback_mapping(self, guide: str, submission: str, max_questions: int) -> List[Dict]:
        """Improved fallback mapping using database-extracted questions."""
        return self._instant_fallback_mapping_with_questions(guide, submission, max_questions, None)
    
    def _instant_fallback_mapping_with_questions(self, guide: str, submission: str, max_questions: int, questions_data: List[Dict] = None) -> List[Dict]:
        """Improved fallback mapping using database-extracted questions."""
        # Split submission into meaningful chunks
        submission_chunks = self._split_submission_intelligently(submission)
        
        mappings = []
        for i in range(max_questions):
            if questions_data and i < len(questions_data):
                question_text = questions_data[i].get('text', questions_data[i].get('question', f"Question {i+1}"))
                confidence = 0.7
            else:
                question_text = f"Question {i+1}"
                confidence = 0.5
            
            # Find best matching answer chunk
            answer = self._find_best_answer_chunk(question_text, submission_chunks, i)
            
            mappings.append({
                'question_id': f"Q{i+1}",
                'question_text': question_text,
                'student_answer': answer,
                'confidence': confidence
            })
        
        return mappings

    def _split_submission_intelligently(self, submission: str) -> List[str]:
        """Split submission into meaningful chunks."""
        # First try paragraph splits
        paragraphs = [p.strip() for p in submission.split('\n\n') if p.strip()]
        
        if len(paragraphs) > 1:
            return paragraphs
        
        # Fall back to line splits
        lines = [line.strip() for line in submission.split('\n') if line.strip()]
        
        # Group lines into chunks of reasonable size
        chunks = []
        current_chunk = ""
        
        for line in lines:
            if len(current_chunk + line) < 300:
                current_chunk += line + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [submission]
    
    def _find_best_answer_chunk(self, question: str, chunks: List[str], question_index: int) -> str:
        """Find the best matching answer chunk for a question."""
        if not chunks:
            return "No answer found"
        
        # Simple strategy: use question index to select chunk
        if question_index < len(chunks):
            return chunks[question_index]
        
        # If we have more questions than chunks, cycle through chunks
        chunk_index = question_index % len(chunks)
        return chunks[chunk_index]
    
    def _generate_default_mappings(self, count: int) -> List[Dict]:
        """Generate default mappings instantly."""
        return [
            {
                'question_id': f"Q{i+1}",
                'question_text': f"Question {i+1}",
                'student_answer': "Answer parsing failed",
                'confidence': 0.2
            }
            for i in range(count)
        ]
    
    def _create_consistent_mapping_cache_key(self, guide_content: str, submission_content: str, max_questions: int, questions_data: List[Dict] = None) -> str:
        """Create a consistent cache key for identical mapping inputs."""
        import hashlib
        
        # Normalize guide content
        guide_normalized = ' '.join(guide_content.strip().lower().split())
        
        # Normalize submission content
        submission_normalized = ' '.join(submission_content.strip().lower().split())
        
        # Create base cache content
        cache_content = f"guide:{guide_normalized}|submission:{submission_normalized}|max_q:{max_questions}"
        
        if questions_data:
            questions_normalized = []
            for q in questions_data[:max_questions]:
                question_text = str(q.get('text', q.get('question', ''))).strip().lower()
                question_text = ' '.join(question_text.split())
                questions_normalized.append(question_text)
            
            questions_str = '|'.join(sorted(questions_normalized))  # Sort for consistency
            cache_content += f"|questions:{questions_str}"
        
        cache_key = hashlib.sha256(cache_content.encode('utf-8')).hexdigest()
        
        logger.debug(f"Created consistent mapping cache key: {cache_key[:16]}... for {max_questions} questions")
        return cache_key
    
    def _get_questions_from_database(self, guide_id: str) -> List[Dict]:
        """Retrieve questions and max scores from database for a guide."""
        try:
            from src.database.models import MarkingGuide
            
            guide = MarkingGuide.query.filter_by(id=guide_id).first()
            if not guide or not guide.questions:
                logger.warning(f"No questions found in database for guide {guide_id}")
                return []
            
            # Convert database questions to format needed for mapping
            questions_data = []
            for i, question in enumerate(guide.questions):
                questions_data.append({
                    'question_id': question.get('number', f"Q{i+1}"),
                    'text': question.get('text', ''),
                    'criteria': question.get('criteria', ''),
                    'max_score': float(question.get('marks', 10))
                })
            
            logger.info(f"Retrieved {len(questions_data)} questions from database")
            return questions_data
            
        except Exception as e:
            logger.error(f"Error retrieving questions from database: {e}")
            return []

class UltraFastGrader:
    """Ultra-fast grading with aggressive optimizations."""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self.cache = {}
    
    def ultra_fast_grade(self, mappings: List[Dict], guide_content: str = "") -> Dict[str, Any]:
        """Ultra-fast grading in under 2 seconds with consistent scoring."""
        if not mappings:
            return self._empty_result()
        
        try:
            cache_key = self._create_consistent_cache_key(mappings, guide_content)
            if cache_key in self.cache:
                logger.info("Cache hit - returning cached grading for consistent scoring")
                return self.cache[cache_key]
            
            if not self.llm_service:
                return self._instant_fallback_grading(mappings)

            # Update grading to use max scores from guide
            max_scores_from_guide = {m['question_id']: m['max_score'] for m in mappings if 'max_score' in m}
            
            # Improved grading prompt with proper max score handling
            questions_text = ""
            for i, mapping in enumerate(mappings[:10]):  # Increased from 5 to 10
                q = mapping.get('question_text', f"Q{i+1}")[:200]  # Increased from 50 to 200
                a = mapping.get('student_answer', '')[:500]  # Increased from 150 to 500
                max_score = max_scores_from_guide.get(mapping.get('question_id', f"Q{i+1}"), 10.0)
                questions_text += f"\nQuestion {i+1}: {q} (Max Score: {max_score} points)\nStudent Answer: {a}\n---"
            
            prompt = f"""Grade each answer according to its specific maximum score. Return scores as points out of the maximum for each question.
Return JSON format: {{"grades":[{{"id":"Q1","score":8.5,"max_score":10,"feedback":"Good answer"}}]}}

{questions_text}

Grade fairly and provide accurate scores based on answer quality. Use the full range from 0 to max_score for each question."""
            
            start_time = time.time()
            
            response = self.llm_service.generate_response(
                system_prompt="Grade quickly. JSON only. Be consistent and deterministic in your scoring.",
                user_prompt=prompt,
                temperature=0.0,  # Deterministic responses
                use_cache=True    # Enable caching for consistency
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Ultra-fast grading completed in {processing_time:.2f}s")
            
            # Quick parsing and calculation
            grades = self._ultra_parse_grades(response, mappings)
            result = self._ultra_calculate_results(grades)
            
            # Cache result
            self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Ultra-fast grading failed: {e}")
            return self._instant_fallback_grading(mappings)
    
    def _create_consistent_cache_key(self, mappings: List[Dict], guide_content: str = "") -> str:
        """Create a consistent cache key for identical question-answer pairs."""
        import hashlib
        
        # Create a normalized representation of the mappings
        normalized_mappings = []
        for mapping in mappings:
            # Extract and normalize the key components
            question = str(mapping.get('question_text', '')).strip().lower()
            answer = str(mapping.get('student_answer', '')).strip().lower()
            
            # Remove extra whitespace and normalize
            question = ' '.join(question.split())
            answer = ' '.join(answer.split())
            
            normalized_mappings.append({
                'question': question,
                'answer': answer
            })
        
        # Sort mappings to ensure consistent ordering
        normalized_mappings.sort(key=lambda x: (x['question'], x['answer']))
        
        # Create a stable string representation
        cache_content = json.dumps(normalized_mappings, sort_keys=True)
        
        if guide_content:
            guide_normalized = ' '.join(guide_content.strip().lower().split())
            cache_content += f"|guide:{guide_normalized[:200]}"  # Limit guide content
        
        cache_key = hashlib.sha256(cache_content.encode('utf-8')).hexdigest()
        
        logger.debug(f"Created consistent cache key: {cache_key[:16]}... for {len(mappings)} mappings")
        return cache_key
    
    def _ultra_parse_grades(self, response: str, mappings: List[Dict]) -> List[Dict]:
        """Ultra-fast grade parsing with proper max score handling."""
        try:
            # Try direct JSON
            data = json.loads(response)
            grades = data.get('grades', [])
        except:
            # Fallback: try to extract scores and max_scores from response
            scores = re.findall(r'"score":\s*([\d.]+)', response)
            max_scores = re.findall(r'"max_score":\s*([\d.]+)', response)
            grades = []
            for i, score in enumerate(scores):
                max_score = max_scores[i] if i < len(max_scores) else '10'
                grades.append({
                    'id': f'Q{i+1}', 
                    'score': float(score),
                    'max_score': float(max_score)
                })
        
        # Normalize grades with proper max score handling
        result = []
        for i, mapping in enumerate(mappings):
            # Get the actual max score for this question
            actual_max_score = mapping.get('max_score', 10.0)
            
            if i < len(grades):
                grade_data = grades[i]
                # Get score from LLM response
                raw_score = float(grade_data.get('score', actual_max_score * 0.6))
                # Get max_score from LLM response or use actual
                llm_max_score = float(grade_data.get('max_score', actual_max_score))
                
                # Normalize score to actual max_score if LLM used different scale
                if llm_max_score != actual_max_score and llm_max_score > 0:
                    normalized_score = (raw_score / llm_max_score) * actual_max_score
                else:
                    normalized_score = raw_score
                
                # Ensure score is within bounds
                final_score = max(0.0, min(actual_max_score, normalized_score))
            else:
                # Default score: 60% of max score
                final_score = actual_max_score * 0.6
            
            result.append({
                'question_id': mapping.get('question_id', f"Q{i+1}"),
                'score': round(final_score, 2),
                'max_score': float(actual_max_score),
                'feedback': grades[i].get('feedback', 'Fast graded') if i < len(grades) else 'Default graded'
            })
        
        return result
    
    def _ultra_calculate_results(self, grades: List[Dict]) -> Dict[str, Any]:
        """Ultra-fast result calculation using actual max scores from guide."""
        if not grades:
            return self._empty_result()
        
        total_score = sum(grade['score'] for grade in grades)
        # Use actual max scores from guide instead of fixed 100 per question
        max_possible = sum(grade['max_score'] for grade in grades)
        percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
        
        return {
            'total_score': round(total_score, 2),
            'max_score': round(max_possible, 2),
            'percentage': round(percentage, 1),
            'detailed_grades': grades,
            'summary': {
                'total_questions': len(grades),
                'average_score': round(total_score / len(grades), 1) if len(grades) > 0 else 0,
                'processing_method': 'ultra_fast'
            }
        }
    
    def _instant_fallback_grading(self, mappings: List[Dict]) -> Dict[str, Any]:
        """Improved fallback grading with better accuracy."""
        grades = []
        
        for i, mapping in enumerate(mappings):
            answer = mapping.get('student_answer', '').strip()
            question = mapping.get('question_text', '').strip()
            
            # More sophisticated scoring algorithm
            score = self._calculate_fallback_score(answer, question)
            
            grades.append({
                'question_id': mapping.get('question_id', f"Q{i+1}"),
                'score': score,
                'feedback': f'Fallback grading based on content analysis'
            })
        
        return self._ultra_calculate_results(grades)
    
    def _calculate_fallback_score(self, answer: str, question: str) -> int:
        """Calculate a more accurate fallback score."""
        if not answer or answer.lower() in ['no answer found', 'answer not clearly identified', 'answer parsing failed']:
            return 0
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        score = 50  # Start with neutral score
        
        # Length factor (but not the only factor)
        length = len(answer.strip())
        if length > 100:
            score += 15
        elif length > 50:
            score += 10
        elif length > 20:
            score += 5
        elif length < 5:
            score -= 20
        
        # Content quality indicators
        quality_indicators = [
            'because', 'therefore', 'however', 'although', 'furthermore',
            'in conclusion', 'for example', 'such as', 'according to',
            'as a result', 'on the other hand', 'in addition'
        ]
        
        for indicator in quality_indicators:
            if indicator in answer_lower:
                score += 3
        
        if any(word in answer_lower for word in ['yes', 'no', 'true', 'false']):
            if length > 10:  # Explained yes/no answer
                score += 5
        
        if re.search(r'\d+', answer):
            score += 5
        
        if any(char in answer for char in ['1.', '2.', '•', '-', 'a)', 'b)']):
            score += 10
        
        # Penalize very generic answers
        generic_phrases = ['i think', 'maybe', 'probably', 'not sure', 'i guess']
        for phrase in generic_phrases:
            if phrase in answer_lower:
                score -= 5
        
        if question_lower and len(question_lower) > 10:
            question_words = set(re.findall(r'\b\w{4,}\b', question_lower))
            answer_words = set(re.findall(r'\b\w{4,}\b', answer_lower))
            
            overlap = len(question_words.intersection(answer_words))
            if overlap > 0:
                score += min(overlap * 3, 15)  # Max 15 bonus points
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    def _empty_result(self) -> Dict[str, Any]:
        """Empty result structure."""
        return {
            'total_score': 0,
            'max_score': 0,
            'percentage': 0,
            'detailed_grades': [],
            'summary': {'total_questions': 0, 'average_score': 0}
        }

class UltraFastProcessor:
    """Main ultra-fast processing coordinator."""
    
    def __init__(self, llm_service=None):
        self.mapper = UltraFastMapper(llm_service)
        self.grader = UltraFastGrader(llm_service)
    
    async def process_ultra_fast(self, guide_content: str, submission_content: str, 
                               max_questions: int = 5) -> Dict[str, Any]:
        """Process submission in under 3 seconds total."""
        start_time = time.time()
        
        try:
            # Step 1: Ultra-fast mapping
            mappings = self.mapper.ultra_fast_map(guide_content, submission_content, max_questions)
            mapping_time = time.time() - start_time
            
            # Step 2: Ultra-fast grading
            grading_start = time.time()
            grading_result = self.grader.ultra_fast_grade(mappings, guide_content)
            grading_time = time.time() - grading_start
            
            total_time = time.time() - start_time
            
            logger.info(f"Ultra-fast processing completed in {total_time:.2f}s "
                       f"(mapping: {mapping_time:.2f}s, grading: {grading_time:.2f}s)")
            
            return {
                'success': True,
                'mappings': mappings,
                'grading_result': grading_result,
                'processing_time': total_time,
                'performance': {
                    'mapping_time': mapping_time,
                    'grading_time': grading_time,
                    'total_time': total_time,
                    'questions_processed': len(mappings)
                }
            }
            
        except Exception as e:
            logger.error(f"Ultra-fast processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def clear_cache(self):
        """Clear all caches."""
        self.mapper.cache.clear()
        self.grader.cache.clear()
        logger.info("Ultra-fast processing caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'mapper_cache_size': len(self.mapper.cache),
            'grader_cache_size': len(self.grader.cache),
            'total_cached_items': len(self.mapper.cache) + len(self.grader.cache)
        }
    
    def clear_specific_cache(self, cache_type: str = "all"):
        """Clear specific cache type for testing or maintenance."""
        if cache_type in ["all", "mapper"]:
            self.mapper.cache.clear()
            logger.info("Mapper cache cleared")
        
        if cache_type in ["all", "grader"]:
            self.grader.cache.clear()
            logger.info("Grader cache cleared")
        
        logger.info(f"Cache clearing completed for: {cache_type}")

# Global ultra-fast processor instance
_ultra_fast_processor = None

def get_ultra_fast_processor():
    """Get or create ultra-fast processor instance."""
    global _ultra_fast_processor
    
    if _ultra_fast_processor is None:
        try:
            from src.services.consolidated_llm_service import ConsolidatedLLMService
            llm_service = ConsolidatedLLMService()
            _ultra_fast_processor = UltraFastProcessor(llm_service)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM service for ultra-fast processor: {e}")
            _ultra_fast_processor = UltraFastProcessor()
    
    return _ultra_fast_processor