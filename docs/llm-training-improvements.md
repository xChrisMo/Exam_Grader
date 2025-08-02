# LLM Training System

## Overview

The LLM training system allows users to train AI models for grading student submissions.

## Basic Workflow

1. **Upload Training Guide** - Upload marking guides and training materials
2. **Create Training Job** - Configure and start model training
3. **Test Model** - Upload test submissions to validate model performance
4. **Generate Report** - Get performance analysis and results

## Usage

### Training a Model

1. Navigate to the LLM Training page
2. Upload your marking guide using the "Upload Guide" button
3. Create a training job by selecting your guide and model type
4. Wait for training to complete

### Testing a Model

1. Upload test submissions with expected scores
2. Run the test to process submissions with your trained model
3. Review accuracy and performance metrics
4. Generate detailed reports

## API Endpoints

### Basic Operations

- `POST /llm_training/upload_guide` - Upload training guide
- `POST /llm_training/create_job` - Create training job
- `POST /llm_training/upload_test_submission` - Upload test submission
- `POST /llm_training/generate_report` - Generate performance report

### Data Retrieval

- `GET /llm_training/guides` - List training guides
- `GET /llm_training/jobs` - List training jobs
- `GET /llm_training/test_submissions` - List test submissions
- `GET /llm_training/reports` - List generated reports

## Configuration

Supported file formats: PDF, DOCX, TXT, MD
Maximum file size: 50MB
Supported models: GPT-3.5 Turbo, GPT-4, DeepSeek Chat

## Troubleshooting

**File upload fails**: Check file format and size limits
**Training job fails**: Verify training guide is properly uploaded
**Test results inaccurate**: Ensure sufficient training data and proper marking guide

For additional support, check the application logs or contact support.