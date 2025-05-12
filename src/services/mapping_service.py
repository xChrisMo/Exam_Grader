"""
Mapping Service for mapping submissions to marking guide criteria.
This service groups questions and answers from marking guides with corresponding 
questions and answers in student submissions.
"""
import re
import json
from typing import Dict, List, Tuple, Optional, Any

class MappingService:
    """Mapping service that groups questions and answers between marking guides and submissions."""
    
    def __init__(self, llm_service=None):
        """Initialize with or without LLM service."""
        self.llm_service = llm_service
        
    def extract_questions_and_answers(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract questions and answers from content using LLM if available.
        Otherwise falls back to regex-based extraction.
        """
        if not content or not content.strip():
            return []
            
        if self.llm_service:
            try:
                # Use LLM to extract questions and answers
                system_prompt = """
                You are an expert at analyzing exam documents. Your task is to identify questions and their corresponding answers.
                For each question-answer pair, provide:
                1. A unique ID
                2. The question text
                3. The answer text
                4. The maximum possible score (if mentioned)
                
                Important guidelines:
                - Questions may be numbered in different ways (e.g., "QUESTION ONE", "Question 1", "1.")
                - Answers may be structured in different ways (e.g., bullet points, paragraphs, numbered lists)
                - Look for key phrases that indicate the start of questions (e.g., "QUESTION", "Q", "Question")
                - Look for key phrases that indicate answers (e.g., "Answer:", "Solution:", or content after the question)
                - For the marking guide, extract the full question text including any sub-questions
                - For submissions, match answers to their corresponding questions even if the numbering differs
                - Carefully scan for marks/points in the following formats:
                  * "X marks" or "X points"
                  * "(X marks)" or "(X points)"
                  * "Total: X marks" or "Total: X points"
                  * "Maximum: X marks" or "Maximum: X points"
                  * "X% of total marks"
                  * Any other format indicating marks/points
                - For sub-questions, look for mark allocations like:
                  * "Part (a): X marks"
                  * "Section 1: X marks"
                  * "(X marks each)"
                - DO NOT assume any default marks if not explicitly stated
                
                Output in JSON format:
                {
                    "items": [
                        {
                            "id": "q1",
                            "text": "question text",
                            "answer": "answer text",
                            "max_score": null,  # Only include if explicitly stated
                            "score_breakdown": {
                                "total": null,  # Only include if explicitly stated
                                "sub_questions": [
                                    {
                                        "text": "sub-question text",
                                        "answer": "sub-question answer",
                                        "marks": null  # Only include if explicitly stated
                                    }
                                ]
                            }
                        }
                    ]
                }
                """
                
                user_prompt = f"""
                Please analyze this exam document and extract all questions and answers.
                Pay special attention to:
                1. Question numbering and format
                2. Mark allocations for each question and sub-question
                3. Answer structure and format
                4. Any special instructions about marks or scoring
                
                Document content:
                {content}
                """
                
                response = self.llm_service.client.chat.completions.create(
                    model=self.llm_service.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )
                
                result = response.choices[0].message.content
                parsed = json.loads(result)
                return parsed.get("items", [])
                
            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to regex: {str(e)}")
        
        # Fallback to regex-based extraction
        items = []
        content = re.sub(r'\n{3,}', '\n\n', content.strip())
        content = re.sub(r'([^\n])(\s*)(Question|Q)\s+(\d+)', r'\1\n\n\3 \4', content, flags=re.IGNORECASE)
        
        question_matches = list(re.finditer(r'(?:^|\n+)((?:Question|Q)[.\s]*\d+[.\s]*:?[.\s]*)(.*?)(?=(?:\n+(?:Question|Q)[.\s]*\d+[.\s]*:?)|$)', 
                                           content, re.IGNORECASE | re.DOTALL))
        
        if not question_matches:
            items.append({
                "id": "item1",
                "text": content.strip(),
                "type": "unknown"
            })
            return items
        
        for i, match in enumerate(question_matches):
            current_id = i + 1
            question_num = match.group(1).strip()
            question_content = match.group(2).strip()
            
            answer_match = re.search(r'(?:^|\n+)((?:Answer|A|Solution|Sol)[.\s]*:?[.\s]*)(.*)', 
                                    question_content, re.IGNORECASE | re.DOTALL)
            
            if answer_match:
                question_text = question_content[:answer_match.start()].strip()
                answer_text = answer_match.group(2).strip()
            else:
                question_text = question_content
                answer_text = ""
            
            # Try to extract max score with more patterns
            max_score = None
            score_patterns = [
                r'(?:max|maximum|total)[.\s]*(?:score|points|marks)[.\s]*:?\s*(\d+)',
                r'\((\d+)\s*(?:marks|points)\)',
                r'(\d+)\s*(?:marks|points)\s*(?:each|total|maximum)?',
                r'(?:worth|total|maximum)\s*(?:of\s*)?(\d+)\s*(?:marks|points)'
            ]
            
            for pattern in score_patterns:
                max_score_match = re.search(pattern, question_content, re.IGNORECASE)
                if max_score_match:
                    max_score = int(max_score_match.group(1))
                    break
            
                items.append({
                    "id": f"q{current_id}",
                    "text": question_text,
                    "answer": answer_text,
                "max_score": max_score  # Will be None if no marks found
                })
        
        return items
        
    def map_submission_to_guide(self, marking_guide_content: str, student_submission_content: str) -> Tuple[Dict, Optional[str]]:
        """Map a student submission to a marking guide using LLM if available."""
        try:
            # Extract questions and answers from both documents
            guide_items = self.extract_questions_and_answers(marking_guide_content)
            submission_items = self.extract_questions_and_answers(student_submission_content)
            
            if not guide_items or not submission_items:
                return {
                    "status": "error",
                    "message": "No questions found in one or both documents"
                }, "No questions found"
            
            mappings = []
            
            if self.llm_service:
                try:
                    # Use LLM to match questions
                    system_prompt = """
                    You are an expert at matching exam questions between a marking guide and a student submission.
                    Your task is to match each question in the student submission to the corresponding question in the marking guide.
                    
                    Important guidelines:
                    1. Questions may be numbered differently (e.g., "QUESTION ONE" vs "Question 1")
                    2. Look for semantic similarity in the question content
                    3. Consider the structure of the question (e.g., number of sub-questions)
                    4. Match answers to their corresponding questions even if the format differs
                    5. Verify mark allocations between guide and submission:
                       - Check if marks are explicitly stated
                       - Look for mark breakdowns in sub-questions
                       - Consider any special scoring instructions
                       - DO NOT assume any default marks if not explicitly stated
                    6. Provide a high confidence score (0.8-1.0) only for very clear matches
                    7. For partial matches, provide a lower score (0.5-0.7) and explain why
                    
                    Output in JSON format:
                    {
                        "mappings": [
                            {
                                "guide_id": "q1",
                                "submission_id": "q2",
                                "match_score": 0.95,
                                "match_reason": "Exact match in question content and structure",
                                "mark_verification": {
                                    "guide_marks": null,  # Only include if explicitly stated
                                    "submission_marks": null,  # Only include if explicitly stated
                                    "mark_match": true,
                                    "mark_breakdown": {
                                        "main_question": null,  # Only include if explicitly stated
                                        "sub_questions": [
                                            {
                                                "guide_sub_q": "sub-question text",
                                                "submission_sub_q": "matching answer text",
                                                "marks": null,  # Only include if explicitly stated
                                                "match_score": 0.9
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    }
                    """
                    
                    user_prompt = f"""
                    Marking Guide Questions:
                    {json.dumps(guide_items, indent=2)}
                    
                    Student Submission Questions:
                    {json.dumps(submission_items, indent=2)}
                    
                    Please match the questions and provide a confidence score for each match.
                    Consider both the question text and answer content when matching.
                    Pay special attention to mark allocations and verify they match between guide and submission.
                    DO NOT assume any default marks if not explicitly stated.
                    """
                    
                    response = self.llm_service.client.chat.completions.create(
                        model=self.llm_service.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.0,
                        response_format={"type": "json_object"}
                    )
                    
                    result = response.choices[0].message.content
                    parsed = json.loads(result)
                    
                    # Process LLM mappings
                    for mapping in parsed.get("mappings", []):
                        guide_id = mapping["guide_id"]
                        submission_id = mapping["submission_id"]
                        match_score = mapping["match_score"]
                        mark_verification = mapping.get("mark_verification", {})
                        
                        guide_item = next((item for item in guide_items if item["id"] == guide_id), None)
                        submission_item = next((item for item in submission_items if item["id"] == submission_id), None)
                        
                        if guide_item and submission_item:
                            mappings.append({
                                "guide_id": guide_id,
                                "guide_text": guide_item["text"],
                                "guide_answer": guide_item.get("answer", ""),
                                "max_score": guide_item.get("max_score"),  # No default value
                                "submission_id": submission_id,
                                "submission_text": submission_item["text"],
                                "submission_answer": submission_item.get("answer", ""),
                                "match_score": match_score,
                                "match_reason": mapping.get("match_reason", ""),
                                "mark_verification": mark_verification
                            })
                    
                except Exception as e:
                    logger.warning(f"LLM mapping failed, falling back to text matching: {str(e)}")
                    # Fall back to text matching
                    mappings = self._text_based_mapping(guide_items, submission_items)
            else:
                # Use text-based mapping
                mappings = self._text_based_mapping(guide_items, submission_items)
            
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
            
    def _text_based_mapping(self, guide_items: List[Dict], submission_items: List[Dict]) -> List[Dict]:
        """Fallback method for text-based question matching with improved accuracy."""
        mappings = []
        
        # Simple text preprocessing function without NLTK dependency
        def preprocess_text(text):
            if not text:
                return []
            # Convert to lowercase
            text = text.lower()
            # Remove special characters and digits
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'\d+', ' ', text)
            # Split into words
            words = text.split()
            # Remove common stopwords
            common_stopwords = {'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 
                              "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 
                              'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 
                              'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 
                              'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 
                              'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was',
                              'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 
                              'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 
                              'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 
                              'about', 'against', 'between', 'into', 'through', 'during', 'before', 
                              'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 
                              'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once'}
            return [w for w in words if w not in common_stopwords and len(w) > 1]
        
        # Function to calculate Jaccard similarity
        def jaccard_similarity(set1, set2):
            if not set1 or not set2:
                return 0
            intersection = len(set(set1).intersection(set(set2)))
            union = len(set(set1).union(set(set2)))
            return intersection / union if union > 0 else 0
        
        # Function to calculate cosine similarity using TF-IDF approach
        def cosine_similarity_tokens(tokens1, tokens2):
            if not tokens1 or not tokens2:
                return 0
                
            # Count term frequencies
            counts1 = {}
            counts2 = {}
            
            for token in tokens1:
                counts1[token] = counts1.get(token, 0) + 1
            
            for token in tokens2:
                counts2[token] = counts2.get(token, 0) + 1
            
            # Find all unique terms
            unique_terms = set(counts1.keys()).union(set(counts2.keys()))
            
            # Calculate dot product and magnitudes
            dot_product = 0
            magnitude1 = 0
            magnitude2 = 0
            
            for term in unique_terms:
                tf1 = counts1.get(term, 0)
                tf2 = counts2.get(term, 0)
                dot_product += tf1 * tf2
                magnitude1 += tf1 ** 2
                magnitude2 += tf2 ** 2
            
            # Prevent division by zero
            if magnitude1 == 0 or magnitude2 == 0:
                return 0
                
            return dot_product / ((magnitude1 ** 0.5) * (magnitude2 ** 0.5))
        
        # Preprocess all guide items and submission items
        guide_tokens = {}
        submission_tokens = {}
        
        for guide_item in guide_items:
            guide_text = guide_item.get('text', '')
            guide_tokens[guide_item.get('id')] = preprocess_text(guide_text)
            
        for submission_item in submission_items:
            submission_text = submission_item.get('text', '')
            submission_tokens[submission_item.get('id')] = preprocess_text(submission_text)
        
        # For each guide item, find the best match in submission items
        for guide_item in guide_items:
            guide_id = guide_item.get('id')
            guide_text_tokens = guide_tokens[guide_id]
            
            best_score = 0
            best_match = None
            
            for submission_item in submission_items:
                # Skip if already mapped
                if any(m.get('submission_id') == submission_item.get('id') for m in mappings):
                    continue
                
                submission_id = submission_item.get('id')
                submission_text_tokens = submission_tokens[submission_id]
                
                # Calculate similarity scores
                jaccard_score = jaccard_similarity(guide_text_tokens, submission_text_tokens)
                cosine_score = cosine_similarity_tokens(guide_text_tokens, submission_text_tokens)
                
                # Combine scores (weighted average favoring cosine similarity)
                combined_score = (0.3 * jaccard_score) + (0.7 * cosine_score)
                
                # Check exact ID match (e.g., "Question 1" matching with "1.")
                id_match = False
                guide_id_match = re.search(r'(\d+)', guide_item.get('text', ''))
                submission_id_match = re.search(r'(\d+)', submission_item.get('text', ''))
                
                if guide_id_match and submission_id_match:
                    if guide_id_match.group(1) == submission_id_match.group(1):
                        id_match = True
                        combined_score = max(combined_score, 0.6)  # Boost score for ID match
                
                # Also match by guide answer and submission answer if available
                if guide_item.get('answer') and submission_item.get('answer'):
                    guide_answer_tokens = preprocess_text(guide_item.get('answer', ''))
                    submission_answer_tokens = preprocess_text(submission_item.get('answer', ''))
                    
                    answer_jaccard = jaccard_similarity(guide_answer_tokens, submission_answer_tokens)
                    answer_cosine = cosine_similarity_tokens(guide_answer_tokens, submission_answer_tokens)
                    
                    answer_score = (0.3 * answer_jaccard) + (0.7 * answer_cosine)
                    
                    # Consider answer similarity in overall score
                    combined_score = (0.7 * combined_score) + (0.3 * answer_score)
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = (submission_item, combined_score)
            
            if best_match and best_score > 0.2:  # Only map if similarity exceeds threshold
                submission_item, match_score = best_match
                mappings.append({
                    "guide_id": guide_item.get('id'),
                    "guide_text": guide_item.get('text'),
                    "guide_answer": guide_item.get('answer', ''),
                    "max_score": guide_item.get('max_score'),  # No default value
                    "submission_id": submission_item.get('id'),
                    "submission_text": submission_item.get('text'),
                    "submission_answer": submission_item.get('answer', ''),
                    "match_score": match_score
                })
        
        return mappings
