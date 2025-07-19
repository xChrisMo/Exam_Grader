# Exam Grader API Documentation

## Overview

The Exam Grader API provides a comprehensive REST API for managing marking guides, submissions, and AI-powered grading operations. The API follows RESTful principles and uses standardized response formats.

## Base URL

```
http://localhost:5000/api/v1
```

## Authentication

The API supports two authentication methods:

1. **Session-based Authentication**: Used by the web application
2. **API Key Authentication**: For programmatic access (future implementation)

### Session Authentication

Most endpoints require user authentication through the web application's session system.

### API Key Authentication (Future)

API key authentication will be supported by including the API key in the request header:

```
X-API-Key: your-api-key-here
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default**: 100 requests per hour per user/IP
- **Specific endpoints**: May have different limits (documented per endpoint)
- **Rate limit headers**: Included in responses

## Response Format

All API responses follow a standardized format:

### Success Response

```json
{
  "status": "success",
  "data": {
    // Response data
  },
  "message": "Operation completed successfully",
  "metadata": {
    "request_id": "req_123456789",
    "processing_time": 0.045,
    "timestamp": "2023-12-01T12:00:00Z"
  }
}
```

### Error Response

```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "details": [
    {
      "field": "name",
      "message": "Name is required",
      "code": "REQUIRED_FIELD"
    }
  ],
  "metadata": {
    "request_id": "req_123456789",
    "processing_time": 0.012,
    "timestamp": "2023-12-01T12:00:00Z"
  }
}
```

### Paginated Response

```json
{
  "status": "success",
  "data": [
    // Array of items
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5,
    "has_next": true,
    "has_prev": false
  },
  "metadata": {
    "request_id": "req_123456789",
    "processing_time": 0.089,
    "timestamp": "2023-12-01T12:00:00Z"
  }
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Request validation failed |
| `AUTHENTICATION_REQUIRED` | Authentication is required |
| `AUTHORIZATION_FAILED` | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | Requested resource not found |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable |
| `PROCESSING_ERROR` | Internal processing error |

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Rate Limit**: None

**Response**:
```json
{
  "status": "success",
  "data": {
    "status": "healthy",
    "timestamp": 1701432000.123,
    "version": "1.0.0"
  }
}
```

### API Information

#### GET /info

Get API information and available endpoints.

**Rate Limit**: 50 requests per hour

**Response**:
```json
{
  "status": "success",
  "data": {
    "name": "Exam Grader API",
    "version": "1.0.0",
    "description": "AI-powered exam grading and assessment platform",
    "endpoints": {
      "health": "/api/v1/health",
      "info": "/api/v1/info",
      "guides": "/api/v1/guides",
      "submissions": "/api/v1/submissions",
      "processing": "/api/v1/processing",
      "upload": "/api/v1/upload"
    }
  }
}
```

## Marking Guides

### List Marking Guides

#### GET /guides

Retrieve all marking guides for the authenticated user.

**Authentication**: Required
**Rate Limit**: 100 requests per hour

**Query Parameters**:
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)
- `search` (string, optional): Search term for guide names
- `status` (string, optional): Filter by status (`active`, `archived`)

**Example Request**:
```
GET /api/v1/guides?page=1&per_page=10&search=math&status=active
```

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Mathematics Final Exam",
      "subject": "Mathematics",
      "total_marks": 100,
      "is_active": true,
      "created_at": "2023-12-01T10:00:00Z",
      "updated_at": "2023-12-01T11:00:00Z",
      "submission_count": 25,
      "file_path": "/uploads/guides/math_guide.pdf",
      "content_preview": "Question 1: Solve the following equation..."
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### Get Marking Guide

#### GET /guides/{guide_id}

Retrieve a specific marking guide by ID.

**Authentication**: Required
**Rate Limit**: 200 requests per hour

**Path Parameters**:
- `guide_id` (integer): Marking guide ID

**Response**:
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Mathematics Final Exam",
    "subject": "Mathematics",
    "total_marks": 100,
    "is_active": true,
    "created_at": "2023-12-01T10:00:00Z",
    "updated_at": "2023-12-01T11:00:00Z",
    "file_path": "/uploads/guides/math_guide.pdf",
    "content": "Full marking guide content...",
    "statistics": {
      "total_submissions": 25,
      "completed_submissions": 20,
      "processing_submissions": 3,
      "failed_submissions": 2
    }
  }
}
```

### Create Marking Guide

#### POST /guides

Create a new marking guide.

**Authentication**: Required
**Rate Limit**: 20 requests per hour

**Request Body**:
```json
{
  "name": "Physics Midterm",
  "subject": "Physics",
  "total_marks": 150,
  "content": "Marking guide content..."
}
```

**Required Fields**:
- `name` (string): Guide name (3-100 characters)
- `subject` (string): Subject name (2+ characters)

**Optional Fields**:
- `total_marks` (integer): Total marks (default: 100)
- `content` (string): Guide content

**Response** (201 Created):
```json
{
  "status": "success",
  "data": {
    "id": 2,
    "name": "Physics Midterm",
    "subject": "Physics",
    "total_marks": 150,
    "is_active": true,
    "created_at": "2023-12-01T12:00:00Z",
    "content": "Marking guide content..."
  },
  "message": "Marking guide created successfully"
}
```

## Submissions

### List Submissions

#### GET /submissions

Retrieve submissions for the authenticated user's marking guides.

**Authentication**: Required
**Rate Limit**: 100 requests per hour

**Query Parameters**:
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)
- `guide_id` (integer, optional): Filter by marking guide ID
- `status` (string, optional): Filter by processing status
- `search` (string, optional): Search term for student names

**Example Request**:
```
GET /api/v1/submissions?guide_id=1&status=completed&search=john
```

**Response**:
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "student_name": "John Doe",
      "student_id": "12345",
      "processing_status": "completed",
      "created_at": "2023-12-01T09:00:00Z",
      "updated_at": "2023-12-01T09:30:00Z",
      "file_path": "/uploads/submissions/john_doe_exam.pdf",
      "marking_guide": {
        "id": 1,
        "name": "Mathematics Final Exam",
        "subject": "Mathematics"
      },
      "latest_result": {
        "total_score": 85.5,
        "letter_grade": "B+",
        "created_at": "2023-12-01T09:30:00Z"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

## Processing

### Start Batch Processing

#### POST /processing/batch

Start batch processing of submissions.

**Authentication**: Required
**Rate Limit**: 10 requests per hour

**Request Body**:
```json
{
  "guide_id": 1,
  "submission_ids": [1, 2, 3, 4, 5],
  "options": {
    "priority": "high",
    "notify_completion": true
  }
}
```

**Required Fields**:
- `guide_id` (integer): Marking guide ID
- `submission_ids` (array): List of submission IDs

**Optional Fields**:
- `options` (object): Processing options

**Response** (202 Accepted):
```json
{
  "status": "success",
  "data": {
    "task_id": "batch_20231201_120000_1",
    "status": "started",
    "guide_id": 1,
    "submission_count": 5,
    "estimated_completion": "5-10 minutes"
  },
  "message": "Batch processing started successfully"
}
```

### Get Processing Status

#### GET /processing/status/{task_id}

Get the status of a processing task.

**Authentication**: Required
**Rate Limit**: 200 requests per hour

**Path Parameters**:
- `task_id` (string): Processing task ID

**Response**:
```json
{
  "status": "success",
  "data": {
    "task_id": "batch_20231201_120000_1",
    "status": "processing",
    "progress": {
      "current": 3,
      "total": 5,
      "percentage": 60
    },
    "started_at": "2023-12-01T12:00:00Z",
    "estimated_completion": "3 minutes remaining",
    "results": {
      "completed": 3,
      "failed": 0,
      "pending": 2
    }
  }
}
```

**Task Status Values**:
- `started`: Task has been initiated
- `processing`: Task is currently running
- `completed`: Task completed successfully
- `failed`: Task failed with errors
- `cancelled`: Task was cancelled

## Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "details": [
    {
      "field": "name",
      "message": "Name must be at least 3 characters long",
      "code": "MIN_LENGTH"
    }
  ]
}
```

#### 401 Unauthorized
```json
{
  "status": "error",
  "error_code": "AUTHENTICATION_REQUIRED",
  "message": "Authentication required"
}
```

#### 403 Forbidden
```json
{
  "status": "error",
  "error_code": "AUTHORIZATION_FAILED",
  "message": "Access forbidden"
}
```

#### 404 Not Found
```json
{
  "status": "error",
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Resource not found"
}
```

#### 429 Rate Limit Exceeded
```json
{
  "status": "error",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded: 100 requests per 3600 seconds",
  "retry_after": 3600
}
```

#### 500 Internal Server Error
```json
{
  "status": "error",
  "error_code": "PROCESSING_ERROR",
  "message": "An unexpected error occurred"
}
```

#### 503 Service Unavailable
```json
{
  "status": "error",
  "error_code": "SERVICE_UNAVAILABLE",
  "message": "AI processing service is not available"
}
```

## CORS Support

The API supports Cross-Origin Resource Sharing (CORS) for the following origins:
- `http://localhost:3000` (Development frontend)
- `http://localhost:5000` (Local development)

**Allowed Methods**: GET, POST, PUT, DELETE, OPTIONS
**Allowed Headers**: Content-Type, Authorization, X-API-Key
**Credentials**: Supported

## SDK and Examples

### JavaScript/Node.js Example

```javascript
// Fetch marking guides
const response = await fetch('/api/v1/guides', {
  method: 'GET',
  credentials: 'include', // Include session cookies
  headers: {
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
if (data.status === 'success') {
  console.log('Guides:', data.data);
} else {
  console.error('Error:', data.message);
}
```

### Python Example

```python
import requests

# Create a new marking guide
response = requests.post(
    'http://localhost:5000/api/v1/guides',
    json={
        'name': 'Chemistry Test',
        'subject': 'Chemistry',
        'total_marks': 80
    },
    # Include session cookies if using session auth
    cookies=session_cookies
)

if response.status_code == 201:
    data = response.json()
    print(f"Created guide: {data['data']['name']}")
else:
    print(f"Error: {response.json()['message']}")
```

### cURL Example

```bash
# Get API information
curl -X GET "http://localhost:5000/api/v1/info" \
  -H "Content-Type: application/json"

# Create marking guide
curl -X POST "http://localhost:5000/api/v1/guides" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Biology Quiz",
    "subject": "Biology",
    "total_marks": 50
  }'
```

## Changelog

### Version 1.0.0 (2023-12-01)
- Initial API release
- Marking guides management endpoints
- Submissions listing and filtering
- Batch processing capabilities
- Standardized response format
- Rate limiting and CORS support
- Comprehensive error handling
- API documentation

## Support

For API support and questions:
- Check the error response details for specific issues
- Review the API logs for debugging information
- Ensure proper authentication and rate limit compliance
- Verify request format and required fields