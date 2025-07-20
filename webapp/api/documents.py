"""
Document management API routes for LLM Training Page
"""

import logging
from flask import jsonify, request, current_app
from werkzeug.exceptions import BadRequest
from . import api_bp
from ..types.api_responses import ApiResponse, ErrorResponse, ErrorType
from src.services.document_processor_service import DocumentProcessorService
from src.models.document_models import FileUpload

logger = logging.getLogger(__name__)

# Initialize document processor service
document_service = DocumentProcessorService()


@api_bp.route('/documents', methods=['GET'])
def get_documents():
    """Get list of uploaded documents with optional filtering and pagination"""
    try:
        # Get query parameters
        search = request.args.get('search', '').strip()
        doc_type = request.args.get('type', '').strip()
        dataset_id = request.args.get('dataset', '').strip()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        # Get all documents
        documents = document_service.list_documents()
        
        # Apply filters
        if search:
            documents = [doc for doc in documents 
                        if search.lower() in doc.name.lower() or 
                           search.lower() in doc.original_name.lower()]
        
        if doc_type:
            documents = [doc for doc in documents if doc.document_type.value == doc_type]
        
        if dataset_id:
            documents = [doc for doc in documents if dataset_id in doc.datasets]
        
        # Apply pagination
        total = len(documents)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = documents[start_idx:end_idx]
        
        # Convert to dict format
        result_docs = [doc.to_dict() for doc in paginated_docs]
        
        # Add pagination info
        pagination = {
            'page': page,
            'limit': limit,
            'total': total,
            'totalPages': (total + limit - 1) // limit
        }
        
        return jsonify({
            'success': True,
            'data': result_docs,
            'pagination': pagination
        })
        
    except ValueError as e:
        logger.error(f"Invalid pagination parameters: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.VALIDATION_ERROR, "Invalid pagination parameters")
        )), 400
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to retrieve documents")
        )), 500


@api_bp.route('/documents/upload', methods=['POST'])
def upload_documents():
    """Upload new documents"""
    try:
        if 'files' not in request.files:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.UPLOAD_ERROR, "No files provided")
            )), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.UPLOAD_ERROR, "No files selected")
            )), 400
        
        uploaded_documents = []
        failed_uploads = []
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                # Create FileUpload object
                file_upload = FileUpload(
                    filename=file.filename,
                    content=file.read(),
                    content_type=file.content_type or 'application/octet-stream',
                    size=len(file.read())
                )
                
                # Reset file pointer and read again for processing
                file.seek(0)
                file_upload.content = file.read()
                
                # Process the file
                result = document_service.process_file_upload(file_upload)
                
                if result.success and result.document:
                    uploaded_documents.append(result.document.to_dict())
                else:
                    failed_uploads.append({
                        'filename': file.filename,
                        'error': result.error_message or "Unknown error",
                        'warnings': result.warnings
                    })
                    
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                failed_uploads.append({
                    'filename': file.filename,
                    'error': f"Processing failed: {str(e)}",
                    'warnings': []
                })
        
        return jsonify(ApiResponse.success({
            'documents': uploaded_documents,
            'failed': failed_uploads,
            'summary': {
                'total': len(files),
                'successful': len(uploaded_documents),
                'failed': len(failed_uploads)
            }
        }))
        
    except Exception as e:
        logger.error(f"Error in document upload: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.UPLOAD_ERROR, "Upload processing failed")
        )), 500


@api_bp.route('/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get specific document details"""
    try:
        document = document_service.get_document(document_id)
        
        if not document:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.API_ERROR, "Document not found")
            )), 404
        
        return jsonify(ApiResponse.success(document.to_dict()))
        
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to retrieve document")
        )), 500


@api_bp.route('/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete a document"""
    try:
        success = document_service.delete_document(document_id)
        
        if not success:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.API_ERROR, "Document not found")
            )), 404
        
        return jsonify(ApiResponse.success(None, "Document deleted successfully"))
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to delete document")
        )), 500


@api_bp.route('/documents/bulk-delete', methods=['POST'])
def bulk_delete_documents():
    """Delete multiple documents"""
    try:
        data = request.get_json()
        if not data or 'document_ids' not in data:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.VALIDATION_ERROR, "Document IDs required")
            )), 400
        
        document_ids = data['document_ids']
        if not isinstance(document_ids, list):
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.VALIDATION_ERROR, "Document IDs must be a list")
            )), 400
        
        deleted_count = 0
        failed_deletions = []
        
        for doc_id in document_ids:
            try:
                success = document_service.delete_document(doc_id)
                if success:
                    deleted_count += 1
                else:
                    failed_deletions.append({
                        'document_id': doc_id,
                        'error': 'Document not found'
                    })
            except Exception as e:
                failed_deletions.append({
                    'document_id': doc_id,
                    'error': str(e)
                })
        
        return jsonify(ApiResponse.success({
            'deleted_count': deleted_count,
            'failed_deletions': failed_deletions,
            'total_requested': len(document_ids)
        }))
        
    except Exception as e:
        logger.error(f"Error in bulk delete: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Bulk deletion failed")
        )), 500


@api_bp.route('/documents/datasets', methods=['GET'])
def get_datasets():
    """Get list of document datasets"""
    try:
        datasets = document_service.list_datasets()
        
        # Get statistics for each dataset
        result_datasets = []
        for dataset in datasets:
            dataset_dict = dataset.to_dict()
            stats = document_service.get_dataset_statistics(dataset.id)
            if stats:
                dataset_dict['statistics'] = stats
            result_datasets.append(dataset_dict)
        
        return jsonify(ApiResponse.success(result_datasets))
        
    except Exception as e:
        logger.error(f"Error retrieving datasets: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to retrieve datasets")
        )), 500


@api_bp.route('/documents/datasets', methods=['POST'])
def create_dataset():
    """Create new document dataset"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.VALIDATION_ERROR, "Request data required")
            )), 400
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.VALIDATION_ERROR, "Dataset name is required")
            )), 400
        
        description = data.get('description', '').strip()
        document_ids = data.get('document_ids', [])
        
        # Validate document IDs if provided
        if document_ids and not isinstance(document_ids, list):
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.VALIDATION_ERROR, "Document IDs must be a list")
            )), 400
        
        # Create dataset
        dataset = document_service.create_dataset(name, description, document_ids)
        
        # Get statistics
        dataset_dict = dataset.to_dict()
        stats = document_service.get_dataset_statistics(dataset.id)
        if stats:
            dataset_dict['statistics'] = stats
        
        return jsonify(ApiResponse.success(dataset_dict, "Dataset created successfully"))
        
    except Exception as e:
        logger.error(f"Error creating dataset: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to create dataset")
        )), 500


@api_bp.route('/documents/datasets/<dataset_id>', methods=['GET'])
def get_dataset(dataset_id):
    """Get specific dataset details"""
    try:
        dataset = document_service.get_dataset(dataset_id)
        
        if not dataset:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.API_ERROR, "Dataset not found")
            )), 404
        
        # Get dataset with statistics
        dataset_dict = dataset.to_dict()
        stats = document_service.get_dataset_statistics(dataset_id)
        if stats:
            dataset_dict['statistics'] = stats
        
        # Get documents in dataset
        documents = []
        for doc_id in dataset.document_ids:
            doc = document_service.get_document(doc_id)
            if doc:
                documents.append(doc.to_dict())
        
        dataset_dict['documents'] = documents
        
        return jsonify(ApiResponse.success(dataset_dict))
        
    except Exception as e:
        logger.error(f"Error retrieving dataset {dataset_id}: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to retrieve dataset")
        )), 500


@api_bp.route('/documents/datasets/<dataset_id>', methods=['PUT'])
def update_dataset(dataset_id):
    """Update dataset"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.VALIDATION_ERROR, "Request data required")
            )), 400
        
        dataset = document_service.get_dataset(dataset_id)
        if not dataset:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.API_ERROR, "Dataset not found")
            )), 404
        
        # Update dataset properties
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify(ApiResponse.error(
                    ErrorResponse(ErrorType.VALIDATION_ERROR, "Dataset name cannot be empty")
                )), 400
            dataset.name = name
        
        if 'description' in data:
            dataset.description = data['description'].strip()
        
        # Handle document operations
        if 'document_ids' in data:
            # Replace all documents
            new_doc_ids = data['document_ids']
            if not isinstance(new_doc_ids, list):
                return jsonify(ApiResponse.error(
                    ErrorResponse(ErrorType.VALIDATION_ERROR, "Document IDs must be a list")
                )), 400
            
            # Remove all current documents
            for doc_id in dataset.document_ids.copy():
                document_service.remove_document_from_dataset(dataset_id, doc_id)
            
            # Add new documents
            for doc_id in new_doc_ids:
                document_service.add_document_to_dataset(dataset_id, doc_id)
        
        elif 'add_documents' in data:
            # Add specific documents
            doc_ids_to_add = data['add_documents']
            if not isinstance(doc_ids_to_add, list):
                return jsonify(ApiResponse.error(
                    ErrorResponse(ErrorType.VALIDATION_ERROR, "Documents to add must be a list")
                )), 400
            
            for doc_id in doc_ids_to_add:
                document_service.add_document_to_dataset(dataset_id, doc_id)
        
        elif 'remove_documents' in data:
            # Remove specific documents
            doc_ids_to_remove = data['remove_documents']
            if not isinstance(doc_ids_to_remove, list):
                return jsonify(ApiResponse.error(
                    ErrorResponse(ErrorType.VALIDATION_ERROR, "Documents to remove must be a list")
                )), 400
            
            for doc_id in doc_ids_to_remove:
                document_service.remove_document_from_dataset(dataset_id, doc_id)
        
        # Get updated dataset with statistics
        updated_dataset = document_service.get_dataset(dataset_id)
        dataset_dict = updated_dataset.to_dict()
        stats = document_service.get_dataset_statistics(dataset_id)
        if stats:
            dataset_dict['statistics'] = stats
        
        return jsonify(ApiResponse.success(dataset_dict, "Dataset updated successfully"))
        
    except Exception as e:
        logger.error(f"Error updating dataset {dataset_id}: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to update dataset")
        )), 500


@api_bp.route('/documents/datasets/<dataset_id>', methods=['DELETE'])
def delete_dataset(dataset_id):
    """Delete dataset"""
    try:
        success = document_service.delete_dataset(dataset_id)
        
        if not success:
            return jsonify(ApiResponse.error(
                ErrorResponse(ErrorType.API_ERROR, "Dataset not found")
            )), 404
        
        return jsonify(ApiResponse.success(None, "Dataset deleted successfully"))
        
    except Exception as e:
        logger.error(f"Error deleting dataset {dataset_id}: {str(e)}")
        return jsonify(ApiResponse.error(
            ErrorResponse(ErrorType.API_ERROR, "Failed to delete dataset")
        )), 500