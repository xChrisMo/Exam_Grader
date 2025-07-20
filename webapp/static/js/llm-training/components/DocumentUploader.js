/**
 * Document Uploader Component for LLM Training
 * Specialized uploader for training documents with validation and processing
 */

class DocumentUploader {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? docum