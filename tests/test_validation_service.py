"""
Unit tests for ValidationService

Tests the comprehensive validation functionality for datasets,
training configurations, and model outputs.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.validation_service import ValidationService
from src.database.models import LLMDataset, LLMDocument, LLMDatasetDocument

class TestValidationService:
    """Test cases for ValidationService"""
    
    @pytest.fixture
    def service(self):
        """Create ValidationService instance for testing"""
        return ValidationService()
    
    @pytest.fixture
    def mock_dataset(self):
        """Create mock dataset for testing"""
        dataset = Mock(spec=LLMDataset)
        dataset.id = 'test-dataset-id'
        dataset.name = 'Test Dataset'
        dataset.user_id = 'test-user-id'
        return dataset
    
    @pytest.fixture
    def mock_documents(self):
        """Create mock documents for testing"""
        docs = []
        for i in range(3):
            doc = Mock(spec=LLMDocument)
            doc.id = f'doc-{i}'
            doc.name = f'document_{i}.txt'
            doc.file_type = 'txt'
            doc.file_size = 1024 * (i + 1)
            doc.word_count = 100 * (i + 1)
            doc.character_count = 500 * (i + 1)
            doc.text_content = f'This is test content for document {i}. ' * 20
            doc.extracted_text = True
            doc.validation_status = 'valid'
            doc.content_quality_score = 0.7 + (i * 0.1)
            docs.append(doc)
        return docs
    
    def test_initialization(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, 'validation_rules')
        assert 'dataset' in service.validation_rules
        assert 'training_config' in service.validation_rules
        assert 'model_output' in service.validation_rules
    
    @patch('src.services.validation_service.db')
    @patch('src.services.validation_service.LLMDatasetDocument')
    def test_validate_dataset_integrity_success(self, mock_dataset_doc, mock_db, service, mock_dataset, mock_documents):
        """Test successful dataset validation"""
        # Setup mocks
        mock_db.session.get.return_value = mock_dataset
        
        mock_dataset_docs = [Mock() for _ in range(3)]
        for i, dd in enumerate(mock_dataset_docs):
            dd.document_id = f'doc-{i}'
        mock_dataset_doc.query.filter_by.return_value.all.return_value = mock_dataset_docs
        
        # Mock document retrieval
        def mock_get_doc(model, doc_id):
            if model == LLMDocument:
                return mock_documents[int(doc_id.split('-')[1])]
            return mock_dataset
        
        mock_db.session.get.side_effect = mock_get_doc
        
        # Execute
        result = service.validate_dataset_integrity('test-dataset-id')
        
        # Verify
        assert result['valid'] is True
        assert result['score'] > 0.5
        assert isinstance(result['errors'], list)
        assert isinstance(result['warnings'], list)
        assert isinstance(result['recommendations'], list)
        assert 'details' in result
    
    @patch('src.services.validation_service.db')
    def test_validate_dataset_integrity_not_found(self, mock_db, service):
        """Test dataset validation with non-existent dataset"""
        mock_db.session.get.return_value = None
        
        result = service.validate_dataset_integrity('invalid-dataset-id')
        
        assert result['valid'] is False
        assert 'Dataset not found' in result['errors']
        assert result['score'] == 0.0
    
    @patch('src.services.validation_service.db')
    @patch('src.services.validation_service.LLMDatasetDocument')
    def test_validate_dataset_integrity_insufficient_documents(self, mock_dataset_doc, mock_db, service, mock_dataset):
        """Test dataset validation with insufficient documents"""
        # Setup mocks - only 2 documents (below minimum of 5)
        mock_db.session.get.return_value = mock_dataset
        mock_dataset_doc.query.filter_by.return_value.all.return_value = [Mock(), Mock()]
        
        # Mock document retrieval with minimal documents
        mock_docs = [Mock(spec=LLMDocument) for _ in range(2)]
        for i, doc in enumerate(mock_docs):
            doc.word_count = 50  # Low word count
            doc.file_size = 512
            doc.file_type = 'txt'
            doc.name = f'doc_{i}.txt'
            doc.extracted_text = True
            doc.validation_status = 'valid'
        
        def mock_get_doc(model, doc_id):
            if model == LLMDocument:
                return mock_docs[0] if 'doc-0' in str(doc_id) else mock_docs[1]
            return mock_dataset
        
        mock_db.session.get.side_effect = mock_get_doc
        
        # Execute
        result = service.validate_dataset_integrity('test-dataset-id')
        
        # Verify
        assert result['valid'] is False
        assert any('documents' in error for error in result['errors'])
        assert any('words' in error for error in result['errors'])
    
    def test_validate_training_config_success(self, service):
        """Test successful training configuration validation"""
        config = {
            'name': 'Test Training Job',
            'model_id': 'test-model',
            'dataset_id': 'test-dataset',
            'epochs': 10,
            'batch_size': 8,
            'learning_rate': 0.0001,
            'max_tokens': 512
        }
        
        # Mock dataset validation
        with patch.object(service, 'validate_dataset_integrity') as mock_dataset_val:
            mock_dataset_val.return_value = {
                'valid': True,
                'warnings': [],
                'errors': []
            }
            
            result = service.validate_training_config(config)
            
            assert result['valid'] is True
            assert len(result['errors']) == 0
            assert 'normalized_config' in result
            assert result['normalized_config']['epochs'] == 10
    
    def test_validate_training_config_invalid_epochs(self, service):
        """Test training config validation with invalid epochs"""
        config = {
            'name': 'Test Training Job',
            'model_id': 'test-model',
            'dataset_id': 'test-dataset',
            'epochs': 0,  # Invalid: below minimum
            'batch_size': 8,
            'learning_rate': 0.0001,
            'max_tokens': 512
        }
        
        with patch.object(service, 'validate_dataset_integrity') as mock_dataset_val:
            mock_dataset_val.return_value = {'valid': True, 'warnings': [], 'errors': []}
            
            result = service.validate_training_config(config)
            
            assert result['valid'] is False
            assert any('Epochs must be at least' in error for error in result['errors'])
    
    def test_validate_training_config_high_epochs_warning(self, service):
        """Test training config validation with high epochs (warning)"""
        config = {
            'name': 'Test Training Job',
            'model_id': 'test-model',
            'dataset_id': 'test-dataset',
            'epochs': 75,  # High but valid
            'batch_size': 8,
            'learning_rate': 0.0001,
            'max_tokens': 512
        }
        
        with patch.object(service, 'validate_dataset_integrity') as mock_dataset_val:
            mock_dataset_val.return_value = {'valid': True, 'warnings': [], 'errors': []}
            
            result = service.validate_training_config(config)
            
            assert result['valid'] is True
            assert any('overfitting' in warning for warning in result['warnings'])
    
    def test_validate_training_config_invalid_learning_rate(self, service):
        """Test training config validation with invalid learning rate"""
        config = {
            'name': 'Test Training Job',
            'model_id': 'test-model',
            'dataset_id': 'test-dataset',
            'epochs': 10,
            'batch_size': 8,
            'learning_rate': 0.1,  # Too high
            'max_tokens': 512
        }
        
        with patch.object(service, 'validate_dataset_integrity') as mock_dataset_val:
            mock_dataset_val.return_value = {'valid': True, 'warnings': [], 'errors': []}
            
            result = service.validate_training_config(config)
            
            assert result['valid'] is False
            assert any('Learning rate cannot exceed' in error for error in result['errors'])
    
    def test_validate_training_config_missing_required_fields(self, service):
        """Test training config validation with missing required fields"""
        config = {
            'name': 'Test Training Job',
            # Missing model_id and dataset_id
            'epochs': 10,
            'batch_size': 8,
            'learning_rate': 0.0001,
            'max_tokens': 512
        }
        
        result = service.validate_training_config(config)
        
        assert result['valid'] is False
        assert any('Model ID is required' in error for error in result['errors'])
        assert any('Dataset ID is required' in error for error in result['errors'])
    
    def test_validate_model_output_success(self, service):
        """Test successful model output validation"""
        output_data = {
            'accuracy': 0.85,
            'loss': 0.15,
            'confidence_scores': [0.8, 0.9, 0.7, 0.85, 0.92],
            'training_time': 3600,
            'model_size': '1.2GB'
        }
        
        result = service.validate_model_output('test-model', output_data)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['quality_score'] > 0.5
        assert isinstance(result['recommendations'], list)
    
    def test_validate_model_output_missing_metrics(self, service):
        """Test model output validation with missing required metrics"""
        output_data = {
            'training_time': 3600,
            # Missing accuracy and loss
        }
        
        result = service.validate_model_output('test-model', output_data)
        
        assert result['valid'] is False
        assert any('Missing required metric: accuracy' in error for error in result['errors'])
        assert any('Missing required metric: loss' in error for error in result['errors'])
    
    def test_validate_model_output_invalid_accuracy(self, service):
        """Test model output validation with invalid accuracy"""
        output_data = {
            'accuracy': 1.5,  # Invalid: > 1.0
            'loss': 0.15,
        }
        
        result = service.validate_model_output('test-model', output_data)
        
        assert result['valid'] is False
        assert any('Accuracy must be between 0 and 1' in error for error in result['errors'])
    
    def test_validate_model_output_low_accuracy_warning(self, service):
        """Test model output validation with low accuracy (warning)"""
        output_data = {
            'accuracy': 0.3,  # Low accuracy
            'loss': 0.8,
        }
        
        result = service.validate_model_output('test-model', output_data)
        
        assert result['valid'] is True
        assert any('Low accuracy' in warning for warning in result['warnings'])
    
    def test_validate_model_output_high_accuracy_warning(self, service):
        """Test model output validation with suspiciously high accuracy"""
        output_data = {
            'accuracy': 0.98,  # Very high accuracy
            'loss': 0.01,
        }
        
        result = service.validate_model_output('test-model', output_data)
        
        assert result['valid'] is True
        assert any('overfitting' in warning for warning in result['warnings'])
    
    def test_validate_model_output_invalid_confidence_scores(self, service):
        """Test model output validation with invalid confidence scores"""
        output_data = {
            'accuracy': 0.85,
            'loss': 0.15,
            'confidence_scores': [0.8, 1.2, -0.1, 0.85]  # Invalid scores
        }
        
        result = service.validate_model_output('test-model', output_data)
        
        assert result['valid'] is False
        assert any('Confidence scores must be between 0 and 1' in error for error in result['errors'])
    
    def test_check_data_quality_good_documents(self, service):
        """Test data quality check with good quality documents"""
        documents = [
            "This is a well-written document with proper structure. It contains multiple sentences and good vocabulary. The content is meaningful and well-organized.",
            "Another high-quality document with excellent content. It demonstrates good writing skills and provides valuable information. The structure is clear and coherent.",
            "A third document that maintains the quality standard. It has proper grammar, good sentence structure, and meaningful content throughout."
        ]
        
        result = service.check_data_quality(documents)
        
        assert result['overall_quality'] in ['good', 'excellent']
        assert result['quality_score'] > 0.6
        assert len(result['document_scores']) == 3
    
    def test_check_data_quality_poor_documents(self, service):
        """Test data quality check with poor quality documents"""
        documents = [
            "a a a a a",  # Very repetitive
            "short",      # Too short
            "no punctuation here just words"  # No structure
        ]
        
        result = service.check_data_quality(documents)
        
        assert result['overall_quality'] in ['poor', 'fair']
        assert result['quality_score'] < 0.6
        assert len(result['issues']) > 0
    
    def test_check_data_quality_empty_documents(self, service):
        """Test data quality check with empty document list"""
        documents = []
        
        result = service.check_data_quality(documents)
        
        assert result['overall_quality'] == 'poor'
        assert result['quality_score'] == 0.0
        assert 'No valid documents found' in result['issues']
    
    def test_calculate_document_quality_score_good_content(self, service):
        """Test document quality score calculation for good content"""
        content = """
        This is a well-structured document with multiple sentences. 
        It contains proper punctuation and formatting. The content is 
        substantial and provides meaningful information. There are 
        multiple paragraphs with good sentence structure.
        
        This second paragraph continues the theme. It maintains good
        quality throughout the document. The vocabulary is diverse
        and the content is coherent.
        """
        
        score = service._calculate_document_quality_score(content, len(content.split()))
        
        assert score > 0.6
        assert score <= 1.0
    
    def test_calculate_document_quality_score_poor_content(self, service):
        """Test document quality score calculation for poor content"""
        content = "a a a a a"  # Very short and repetitive
        
        score = service._calculate_document_quality_score(content, len(content.split()))
        
        assert score < 0.4
    
    def test_calculate_document_quality_score_empty_content(self, service):
        """Test document quality score calculation for empty content"""
        content = ""
        
        score = service._calculate_document_quality_score(content, 0)
        
        assert score == 0.0
    
    def test_identify_document_issues(self, service):
        """Test document issue identification"""
        # Content with multiple issues
        content = "short"  # Too short
        issues = service._identify_document_issues(content)
        assert 'Very short content' in issues
        
        # Content with no punctuation
        content = "this has no punctuation at all just words"
        issues = service._identify_document_issues(content)
        assert 'No sentence punctuation' in issues
        
        # Content with excessive repetition
        content = "word word word word word word word word word word"
        issues = service._identify_document_issues(content)
        assert 'Excessive word repetition' in issues
        
        # Empty content
        content = ""
        issues = service._identify_document_issues(content)
        assert 'Empty content' in issues
    
    def test_generate_dataset_recommendations(self, service):
        """Test dataset recommendation generation"""
        validation_result = {
            'score': 0.4,  # Low score
            'errors': ['Dataset has only 3 documents, minimum required is 5'],
            'warnings': ['Dataset has 500 words, consider adding more'],
            'details': {
                'content_analysis': {
                    'avg_quality_score': 0.3,
                    'quality_distribution': {'low': 5, 'medium': 2, 'high': 1}
                }
            }
        }
        
        recommendations = service._generate_dataset_recommendations(validation_result)
        
        assert len(recommendations) > 0
        assert any('quality' in rec.lower() for rec in recommendations)
    
    def test_generate_config_recommendations(self, service):
        """Test training config recommendation generation"""
        config = {
            'epochs': 2,  # Low
            'batch_size': 32,  # High
            'learning_rate': 0.01  # High
        }
        
        validation_result = {'warnings': [], 'errors': []}
        
        recommendations = service._generate_config_recommendations(config, validation_result)
        
        assert len(recommendations) > 0
        assert any('epochs' in rec.lower() for rec in recommendations)
        assert any('learning rate' in rec.lower() for rec in recommendations)
    
    def test_generate_model_recommendations(self, service):
        """Test model recommendation generation"""
        output_data = {
            'accuracy': 0.4,  # Low
            'loss': 2.0,      # High
            'confidence_scores': [0.3, 0.4, 0.2, 0.5]  # Low confidence
        }
        
        validation_result = {'warnings': [], 'errors': []}
        
        recommendations = service._generate_model_recommendations(output_data, validation_result)
        
        assert len(recommendations) > 0
        assert any('accuracy' in rec.lower() for rec in recommendations)
        assert any('loss' in rec.lower() or 'convergence' in rec.lower() for rec in recommendations)

class TestValidationServiceIntegration:
    """Integration tests for ValidationService"""
    
    @pytest.fixture
    def service(self):
        """Create ValidationService instance for integration testing"""
        return ValidationService()
    
    def test_full_validation_workflow(self, service):
        """Test complete validation workflow"""
        # This would test the entire validation process
        
        # For now, just verify service initialization
        assert service is not None
        assert hasattr(service, 'validation_rules')
    
    def test_validation_rules_consistency(self, service):
        """Test that validation rules are consistent and complete"""
        rules = service.validation_rules
        
        # Check that all required rule categories exist
        assert 'dataset' in rules
        assert 'training_config' in rules
        assert 'model_output' in rules
        
        # Check that dataset rules have required fields
        dataset_rules = rules['dataset']
        assert 'min_documents' in dataset_rules
        assert 'min_total_words' in dataset_rules
        assert 'supported_formats' in dataset_rules
        
        # Check that training config rules have required fields
        config_rules = rules['training_config']
        assert 'min_epochs' in config_rules
        assert 'max_epochs' in config_rules
        assert 'min_learning_rate' in config_rules
        assert 'max_learning_rate' in config_rules

if __name__ == '__main__':
    pytest.main([__file__])