/**
 * API route interfaces and request/response types for LLM Training Page
 */

import {
  LLMModel,
  TrainingConfig,
  TrainingSession,
  Document,
  Dataset,
  TrainingReport,
  SessionComparison,
  ApiResponse,
  PaginatedResponse
} from './index';

// API Endpoints
export const API_ENDPOINTS = {
  // Model Management
  MODELS: '/api/models',
  MODEL_BY_ID: (id: string) => `/api/models/${id}`,
  MODEL_VALIDATE: (id: string) => `/api/models/${id}/validate`,
  MODEL_CAPABILITIES: (id: string) => `/api/models/${id}/capabilities`,

  // Document Management
  DOCUMENTS: '/api/documents',
  DOCUMENT_UPLOAD: '/api/documents/upload',
  DOCUMENT_BY_ID: (id: string) => `/api/documents/${id}`,
  DOCUMENT_DATASETS: '/api/documents/datasets',
  DATASET_BY_ID: (id: string) => `/api/documents/datasets/${id}`,

  // Training Operations
  TRAINING_SESSIONS: '/api/training/sessions',
  TRAINING_SESSION_BY_ID: (id: string) => `/api/training/sessions/${id}`,
  TRAINING_START: (id: string) => `/api/training/sessions/${id}/start`,
  TRAINING_CANCEL: (id: string) => `/api/training/sessions/${id}/cancel`,
  TRAINING_PAUSE: (id: string) => `/api/training/sessions/${id}/pause`,
  TRAINING_RESUME: (id: string) => `/api/training/sessions/${id}/resume`,

  // Reports
  REPORTS: '/api/reports',
  REPORT_BY_SESSION: (sessionId: string) => `/api/reports/session/${sessionId}`,
  REPORT_EXPORT: (reportId: string, format: string) => `/api/reports/${reportId}/export/${format}`,
  REPORT_COMPARE: '/api/reports/compare',

  // WebSocket
  WEBSOCKET: '/ws/training'
} as const;

// Request Types

// Model Management Requests
export interface ModelValidationRequest {
  config: TrainingConfig;
}

export interface ModelValidationResponse {
  isValid: boolean;
  errors: Array<{
    field: string;
    message: string;
    code: string;
  }>;
  warnings: Array<{
    field: string;
    message: string;
    suggestion?: string;
  }>;
  recommendedConfig?: Partial<TrainingConfig>;
}

// Document Management Requests
export interface DocumentUploadRequest {
  files: File[];
  datasetId?: string;
}

export interface DocumentUploadResponse {
  documents: Document[];
  failed: Array<{
    filename: string;
    error: string;
  }>;
}

export interface DatasetCreateRequest {
  name: string;
  description?: string;
  documentIds: string[];
}

export interface DatasetUpdateRequest {
  name?: string;
  description?: string;
  documentIds?: string[];
}

// Training Session Requests
export interface TrainingSessionCreateRequest {
  modelId: string;
  documentIds: string[];
  config: TrainingConfig;
  name?: string;
  description?: string;
}

export interface TrainingSessionUpdateRequest {
  name?: string;
  description?: string;
  config?: TrainingConfig;
}

// Report Requests
export interface ReportGenerateRequest {
  sessionId: string;
  includeCharts?: boolean;
  includeRawData?: boolean;
}

export interface ReportCompareRequest {
  sessionIds: string[];
  metrics?: string[];
}

export interface ReportExportRequest {
  format: 'pdf' | 'json' | 'csv' | 'xlsx';
  includeCharts?: boolean;
  includeRawData?: boolean;
}

// Response Types

// Model Management Responses
export type ModelsListResponse = ApiResponse<LLMModel[]>;
export type ModelDetailsResponse = ApiResponse<LLMModel>;
export type ModelCapabilitiesResponse = ApiResponse<string[]>;

// Document Management Responses
export type DocumentsListResponse = PaginatedResponse<Document>;
export type DocumentDetailsResponse = ApiResponse<Document>;
export type DocumentDeleteResponse = ApiResponse<void>;
export type DatasetsListResponse = ApiResponse<Dataset[]>;
export type DatasetDetailsResponse = ApiResponse<Dataset>;

// Training Session Responses
export type TrainingSessionsListResponse = PaginatedResponse<TrainingSession>;
export type TrainingSessionDetailsResponse = ApiResponse<TrainingSession>;
export type TrainingSessionCreateResponse = ApiResponse<TrainingSession>;
export type TrainingSessionUpdateResponse = ApiResponse<TrainingSession>;
export type TrainingSessionDeleteResponse = ApiResponse<void>;

// Report Responses
export type ReportsListResponse = PaginatedResponse<TrainingReport>;
export type ReportDetailsResponse = ApiResponse<TrainingReport>;
export type ReportGenerateResponse = ApiResponse<TrainingReport>;
export type ReportCompareResponse = ApiResponse<SessionComparison>;
export type ReportExportResponse = ApiResponse<Blob>;

// Query Parameters
export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface DocumentsQueryParams extends PaginationParams {
  datasetId?: string;
  type?: string;
  search?: string;
}

export interface SessionsQueryParams extends PaginationParams {
  modelId?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export interface ReportsQueryParams extends PaginationParams {
  sessionId?: string;
  dateFrom?: string;
  dateTo?: string;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string;
  sessionId: string;
  data: any;
  timestamp: Date;
}

export interface TrainingProgressMessage extends WebSocketMessage {
  type: 'training_progress';
  data: TrainingSession;
}

export interface TrainingStatusMessage extends WebSocketMessage {
  type: 'training_status';
  data: {
    status: string;
    message?: string;
  };
}

export interface TrainingErrorMessage extends WebSocketMessage {
  type: 'training_error';
  data: {
    error: string;
    details?: any;
  };
}

export interface TrainingCompleteMessage extends WebSocketMessage {
  type: 'training_complete';
  data: {
    sessionId: string;
    results: any;
  };
}

// HTTP Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503
} as const;

// API Error Codes
export const API_ERROR_CODES = {
  INVALID_MODEL: 'INVALID_MODEL',
  MODEL_UNAVAILABLE: 'MODEL_UNAVAILABLE',
  INVALID_CONFIG: 'INVALID_CONFIG',
  UPLOAD_FAILED: 'UPLOAD_FAILED',
  FILE_TOO_LARGE: 'FILE_TOO_LARGE',
  UNSUPPORTED_FORMAT: 'UNSUPPORTED_FORMAT',
  TRAINING_FAILED: 'TRAINING_FAILED',
  SESSION_NOT_FOUND: 'SESSION_NOT_FOUND',
  INSUFFICIENT_DOCUMENTS: 'INSUFFICIENT_DOCUMENTS',
  QUOTA_EXCEEDED: 'QUOTA_EXCEEDED',
  RATE_LIMITED: 'RATE_LIMITED'
} as const;