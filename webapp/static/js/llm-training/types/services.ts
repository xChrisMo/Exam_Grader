/**
 * Service interfaces for LLM Training Page
 */

import {
  LLMModel,
  TrainingConfig,
  TrainingSession,
  Document,
  Dataset,
  UploadedFile,
  ValidationResult,
  TrainingReport,
  SessionComparison,
  ApiResponse
} from './index';

// Model Manager Service Interface
export interface ModelManagerService {
  getAvailableModels(): Promise<LLMModel[]>;
  getModelById(modelId: string): Promise<LLMModel>;
  validateConfiguration(modelId: string, config: TrainingConfig): Promise<ValidationResult>;
  initializeTraining(
    modelId: string, 
    documents: string[], 
    config: TrainingConfig
  ): Promise<TrainingSession>;
  getModelCapabilities(modelId: string): Promise<string[]>;
  checkModelAvailability(modelId: string): Promise<boolean>;
}

// Document Processing Service Interface
export interface DocumentProcessorService {
  processUpload(file: File): Promise<UploadedFile>;
  extractText(file: File): Promise<string>;
  validateFormat(file: File): Promise<ValidationResult>;
  createDataset(documents: string[], name: string, description?: string): Promise<Dataset>;
  getDocuments(): Promise<Document[]>;
  getDocument(documentId: string): Promise<Document>;
  deleteDocument(documentId: string): Promise<void>;
  updateDocument(documentId: string, updates: Partial<Document>): Promise<Document>;
  getDatasets(): Promise<Dataset[]>;
  updateDataset(datasetId: string, updates: Partial<Dataset>): Promise<Dataset>;
  deleteDataset(datasetId: string): Promise<void>;
}

// Training Engine Service Interface
export interface TrainingEngineService {
  createSession(
    modelId: string,
    documents: string[],
    config: TrainingConfig,
    name?: string,
    description?: string
  ): Promise<TrainingSession>;
  getSession(sessionId: string): Promise<TrainingSession>;
  getAllSessions(): Promise<TrainingSession[]>;
  startTraining(sessionId: string): Promise<void>;
  cancelTraining(sessionId: string): Promise<void>;
  pauseTraining(sessionId: string): Promise<void>;
  resumeTraining(sessionId: string): Promise<void>;
  getTrainingProgress(sessionId: string): Promise<TrainingSession>;
  deleteSession(sessionId: string): Promise<void>;
}

// Report Generator Service Interface
export interface ReportGeneratorService {
  generateReport(sessionId: string): Promise<TrainingReport>;
  getReport(reportId: string): Promise<TrainingReport>;
  exportReport(reportId: string, format: string): Promise<Blob>;
  compareSessions(sessionIds: string[]): Promise<SessionComparison>;
  getHistoricalReports(): Promise<TrainingReport[]>;
  deleteReport(reportId: string): Promise<void>;
}

// WebSocket Service Interface
export interface WebSocketService {
  connect(sessionId: string): void;
  disconnect(): void;
  onProgressUpdate(callback: (progress: TrainingSession) => void): void;
  onStatusChange(callback: (status: string) => void): void;
  onError(callback: (error: string) => void): void;
  isConnected(): boolean;
}

// API Client Service Interface
export interface ApiClientService {
  get<T>(endpoint: string, params?: Record<string, any>): Promise<ApiResponse<T>>;
  post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>>;
  put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>>;
  delete<T>(endpoint: string): Promise<ApiResponse<T>>;
  upload<T>(endpoint: string, file: File, onProgress?: (progress: number) => void): Promise<ApiResponse<T>>;
  setAuthToken(token: string): void;
  getAuthToken(): string | null;
}

// Configuration Service Interface
export interface ConfigurationService {
  saveTemplate(template: TrainingConfigTemplate): Promise<void>;
  getTemplates(modelId?: string): Promise<TrainingConfigTemplate[]>;
  deleteTemplate(templateId: string): Promise<void>;
  getDefaultConfig(modelId: string): Promise<TrainingConfig>;
  validateConfig(modelId: string, config: TrainingConfig): Promise<ValidationResult>;
}

// Storage Service Interface
export interface StorageService {
  setItem(key: string, value: any): void;
  getItem<T>(key: string): T | null;
  removeItem(key: string): void;
  clear(): void;
  exists(key: string): boolean;
}

// Notification Service Interface
export interface NotificationService {
  success(message: string, duration?: number): void;
  error(message: string, duration?: number): void;
  warning(message: string, duration?: number): void;
  info(message: string, duration?: number): void;
  clear(): void;
}

// Event Service Interface
export interface EventService {
  on(event: string, callback: Function): void;
  off(event: string, callback: Function): void;
  emit(event: string, data?: any): void;
  once(event: string, callback: Function): void;
}

// Service Factory Interface
export interface ServiceFactory {
  createModelManager(): ModelManagerService;
  createDocumentProcessor(): DocumentProcessorService;
  createTrainingEngine(): TrainingEngineService;
  createReportGenerator(): ReportGeneratorService;
  createWebSocketService(): WebSocketService;
  createApiClient(): ApiClientService;
  createConfigurationService(): ConfigurationService;
  createStorageService(): StorageService;
  createNotificationService(): NotificationService;
  createEventService(): EventService;
}

// Service Configuration Interface
export interface ServiceConfig {
  apiBaseUrl: string;
  websocketUrl: string;
  maxFileSize: number;
  supportedFormats: string[];
  defaultTimeout: number;
  retryAttempts: number;
  authRequired: boolean;
}