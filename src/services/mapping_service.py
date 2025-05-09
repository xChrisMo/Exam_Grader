"""
Mapping Service for mapping submissions to marking guide criteria.
This service groups questions and answers from marking guides with corresponding 
questions and answers in student submissions.
"""
import re
from typing import Dict, List, Tuple, Optional, Any

class MappingService:
    """Mapping service that groups questions and answers between marking guides and submissions."""
    
    def __init__(self, llm_service=None):
        """Initialize with or without LLM service."""
        self.llm_service = llm_service
        
    def extract_questions_and_answers(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract questions and answers from content.
        Looks for patterns like "Question X: ... [content]" followed by "Answer:" or similar patterns.
        
        A real implementation would use the LLM to more accurately parse different formats.
        """
        items = []
        
        if not content or not content.strip():
            return items
            
        # Normalize whitespace and remove extra newlines
        content = re.sub(r'\n{3,}', '\n\n', content.strip())
        
        # Pre-process content to ensure questions are properly separated
        # Replace any "Question X" that doesn't start on a new line with a newline-prefixed version
        content = re.sub(r'([^\n])(\s*)(Question|Q)\s+(\d+)', r'\1\n\n\3 \4', content, flags=re.IGNORECASE)
        
        # Try to split content into separate questions 
        # Find all occurrences of question patterns: "Question X:" or "Q X:"
        question_matches = list(re.finditer(r'(?:^|\n+)((?:Question|Q)[.\s]*\d+[.\s]*:?[.\s]*)(.*?)(?=(?:\n+(?:Question|Q)[.\s]*\d+[.\s]*:?)|$)', 
                                           content, re.IGNORECASE | re.DOTALL))
        
        # If no question patterns found, treat the whole content as one item
        if not question_matches:
            items.append({
                "id": "item1",
                "text": content.strip(),
                "type": "unknown"
            })
            return items
        
        # Process each question match
        for i, match in enumerate(question_matches):
            current_id = i + 1
            question_num = match.group(1).strip()
            question_content = match.group(2).strip()
            
            # Try to separate the question from its answer
            # Look for answer pattern: "Answer:" or "A:" etc.
            answer_match = re.search(r'(?:^|\n+)((?:Answer|A|Solution|Sol)[.\s]*:?[.\s]*)(.*)', 
                                    question_content, re.IGNORECASE | re.DOTALL)
            
            if answer_match:
                # We found both question and answer
                question_text = question_content[:answer_match.start()].strip()
                answer_text = answer_match.group(2).strip()
                
                # Extract max score if present (e.g., [10 marks] or (5 points))
                max_score_match = re.search(r'(?:\[|\()?\s*(\d+)\s*(?:mark|point|score)s?(?:\]|\))?', question_text)
                max_score = int(max_score_match.group(1)) if max_score_match else 10  # Default to 10 if not found
                
                # Add the full question to our list
                items.append({
                    "id": f"q{current_id}",
                    "number": question_num,
                    "text": question_text,
                    "answer": answer_text,
                    "max_score": max_score,
                    "type": "question_answer"
                })
            else:
                # Only the question, no clear answer separation
                items.append({
                    "id": f"q{current_id}",
                    "number": question_num,
                    "text": question_content,
                    "type": "question_only"
                })
        
        return items
        
    def map_submission_to_guide(self, marking_guide_content: str, student_submission_content: str) -> Tuple[Dict, Optional[str]]:
        """Map a student submission to a marking guide."""
        try:
            # Extract questions and answers from the marking guide
            guide_items = self.extract_questions_and_answers(marking_guide_content)
            
            # Extract questions and answers from the student submission
            submission_items = self.extract_questions_and_answers(student_submission_content)
            
            # Create mappings between guide items and submission items
            mappings = []
            
            # Try to match questions by their numbers/identifiers
            for guide_item in guide_items:
                best_match = None
                best_score = 0
                
                for submission_item in submission_items:
                    # Try different matching strategies, ordered by confidence
                    
                    # 1. Match by question number
                    if 'number' in guide_item and 'number' in submission_item:
                        guide_num = re.sub(r'[^0-9]', '', guide_item['number'])
                        submission_num = re.sub(r'[^0-9]', '', submission_item['number'])
                        
                        if guide_num and submission_num and guide_num == submission_num:
                            match_score = 0.95  # High confidence for matching question numbers
                            
                            # If both have the same question number, consider it the best match
                            if match_score > best_score:
                                best_score = match_score
                                best_match = (submission_item, match_score)
                    
                    # 2. Match by first line of question text exact match
                    elif guide_item.get('text', '').split('\n')[0].strip() == \
                         submission_item.get('text', '').split('\n')[0].strip():
                        match_score = 0.9  # High confidence for exact first line match
                        
                        if match_score > best_score:
                            best_score = match_score
                            best_match = (submission_item, match_score)
                    
                    # 3. Match by partial text match in first sentence
                    else:
                        guide_first_line = guide_item.get('text', '').split('\n')[0].strip()
                        submission_first_line = submission_item.get('text', '').split('\n')[0].strip()
                        
                        if guide_first_line and submission_first_line:
                            # Check if either is a substring of the other
                            if guide_first_line in submission_first_line or submission_first_line in guide_first_line:
                                match_score = 0.7  # Medium confidence for partial match
                                
                                if match_score > best_score:
                                    best_score = match_score
                                    best_match = (submission_item, match_score)
                
                # If we found a match, create the mapping
                if best_match:
                    submission_item, match_score = best_match
                    
                    mapping = {
                        "guide_id": guide_item.get('id'),
                        "guide_text": guide_item.get('text'),
                        "guide_answer": guide_item.get('answer', ''),
                        "max_score": guide_item.get('max_score', 10),
                        "submission_id": submission_item.get('id'),
                        "submission_text": submission_item.get('text'),
                        "submission_answer": submission_item.get('answer', ''),
                        "match_score": match_score
                    }
                    
                    mappings.append(mapping)
            
            # Identify unmapped items
            mapped_guide_ids = [m.get('guide_id') for m in mappings]
            mapped_submission_ids = [m.get('submission_id') for m in mappings]
            
            unmapped_guide_items = [item for item in guide_items if item.get('id') not in mapped_guide_ids]
            unmapped_submission_items = [item for item in submission_items if item.get('id') not in mapped_submission_ids]
            
            # Create result
            result = {
                "status": "success",
                "message": "Questions and answers mapped successfully",
                "mappings": mappings,
                "unmapped_guide_items": unmapped_guide_items,
                "unmapped_submission_items": unmapped_submission_items,
                "metadata": {
                    "mapping_count": len(mappings),
                    "guide_item_count": len(guide_items),
                    "submission_item_count": len(submission_items),
                    "unmapped_guide_count": len(unmapped_guide_items),
                    "unmapped_submission_count": len(unmapped_submission_items)
                }
            }
            
            return result, None
            
        except Exception as e:
            error_message = f"Error in mapping service: {str(e)}"
            return {"status": "error", "message": error_message}, error_message
