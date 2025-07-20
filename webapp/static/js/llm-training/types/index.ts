/**
 * Core TypeScript interfaces for LLM Training Page
 */

// Base API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ErrorResponse;
  message?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

// Error Handling Interfaces
export enum ErrorType {
  VALIDATION_ERROR = 'validation_error',
  UPLOAD_ERROR = 'upload_error',
  MODEL_ERROR = 'model_error',
  TRAINING_ERROR = 'training_error',
  API_ERROR = 'api_error',
  NETWORK_ERROR = 'network_error'
}

export interface ErrorResponse {
  type: ErrorType;
  message: string;
  details?: Record<string, any>;
  suggestions?: string[];
}

// LLM Model Interfaces
export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  capabilities: string[];
  maxTokens: number;
  supportedFormats: string[];
  status: 'available' | 'unavailable' | 'maintenance';
  description?: string;
  pricing?: {
    inputTokens: number;
    outputTokens: number;
    currency: string;
  };
}

// Training Configuration Interfaces
export interface TrainingConfig {
  learningRate: number;
  batchSize: number;
  epochs: number;
  temperature?: number;
  maxTokens?: number;
  customParameters: Record<string, any>;
  validationSplit?: number;
  saveCheckpoints?: boolean;
}

export interface TrainingConfigTemplate {
  id: string;
  name: string;
  description: string;
  config: TrainingConfig;
  modelId: string;
  createdAt: Date;
  isDefault: boolean;
}

// Document Interfaces
export interface Document {
  id: string;
  name: string;
  originalName: string;
  size: number;
  type: string;
  content: string;
  metadata: DocumentMetadata;
  datasets: string[];
  status: 'processing' | 'ready' | 'error';
}

export interface DocumentMetadata {
  wordCount: number;
  language: string;
  uploadDate: Date;
  checksum: string;
  encoding?: string;
  extractedPages?: number;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  content: string;
  uploadDate: Date;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  documents: string[];
  createdAt: Date;
  updatedAt: Date;
  statistics: {
    totalDocuments: number;
    totalWords: number;
    totalSize: number;
    languages: string[];
  };
}

// Training Session Interfaces
export interface TrainingSession {
  id: string;
  modelId: string;
  modelName: string;
  documents: string[];
  configuration: TrainingConfig;
  status: TrainingStatus;
  startTime: Date;
  endTime?: Date;
  progress: TrainingProgress;
  results?: TrainingResults;
  error?: string;
  userId?: string;
  name?: string;
  description?: string;
}

export type TrainingStatus = 
  | 'pending' 
  | 'initializing'
  | 'running' 
  | 'completed' 
  | 'failed' 
  | 'cancelled'
  | 'paused';

export interface TrainingProgress {
  completionPercentage: number;
  currentEpoch: number;
  totalEpochs: number;
  loss: number;
  estimatedTimeRemaining: number;
  metrics: Record<string, number>;
  stage: 'preparation' | 'training' | 'validation' | 'finalization';
  lastUpdate: Date;
}

export interface TrainingResults {
  finalLoss: number;
  improvementMetrics: Record<string, number>;
  trainingDuration: number;
  tokensProcessed: number;
  modelPerformance: {
    beforeTraining: PerformanceMetrics;
    afterTraining: PerformanceMetrics;
  };
  sampleOutputs: SampleOutput[];
  checkpoints: TrainingCheckpoint[];
}

export interface PerformanceMetrics {
  accuracy?: number;
  perplexity?: number;
  bleuScore?: number;
  customMetrics: Record<string, number>;
}

export interface SampleOutput {
  input: string;
  beforeOutput: string;
  afterOutput: string;
  improvementScore: number;
}

export interface TrainingCheckpoint {
  epoch: number;
  loss: number;
  metrics: Record<string, number>;
  timestamp: Date;
  modelPath?: string;
}

// Validation Interfaces
export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  message: string;
  code: string;
  value?: any;
}

export interface ValidationWarning {
  field: string;
  message: string;
  suggestion?: string;
}

// Report Interfaces
export interface TrainingReport {
  id: string;
  sessionId: string;
  generatedAt: Date;
  summary: ReportSummary;
  charts: ChartData[];
  exportFormats: string[];
}

export interface ReportSummary {
  modelName: string;
  trainingDuration: number;
  documentsUsed: number;
  finalLoss: number;
  improvementPercentage: number;
  keyInsights: string[];
}

export interface ChartData {
  type: 'line' | 'bar' | 'pie' | 'scatter';
  title: string;
  data: any[];
  options: Record<string, any>;
}

// Comparison Interfaces
export interface SessionComparison {
  sessions: TrainingSession[];
  metrics: ComparisonMetrics;
  recommendations: string[];
  bestPerforming: {
    sessionId: string;
    reason: string;
  };
}

export interface ComparisonMetrics {
  lossComparison: number[];
  durationComparison: number[];
  improvementComparison: number[];
  configurationDifferences: Record<string, any>;
}