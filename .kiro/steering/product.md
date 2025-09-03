# Product Overview

## Exam Grader - AI-Powered Assessment Platform

An AI-powered educational assessment platform that automatically grades exam submissions by comparing student answers against marking guides. The system supports OCR for handwritten submissions and uses advanced LLM technology for intelligent grading.

### Core Features
- **Multi-format Support**: PDF, Word documents, and images
- **OCR Processing**: Handwritten text extraction using multiple OCR engines
- **AI Grading**: LLM-powered answer comparison and scoring
- **Progress Tracking**: Real-time processing updates via WebSocket
- **User Management**: Authentication and session handling
- **Results Export**: PDF and JSON report generation
- **Responsive UI**: Mobile-friendly interface with Tailwind CSS

### Processing Pipeline
1. Upload marking guide with grading criteria
2. Upload student submissions (various formats)
3. OCR processing to extract text from images
4. Answer mapping to match student answers to guide questions
5. AI grading using LLM comparison
6. Generate detailed feedback and scores

### Current Status
Production-ready system with comprehensive security, performance monitoring, and configuration management. The codebase has been analyzed and optimized with all critical issues resolved.

### Target Users
- Educational institutions
- Teachers and instructors
- Assessment coordinators
- Academic administrators