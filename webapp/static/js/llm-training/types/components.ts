/**
 * Component prop interfaces for LLM Training Page
 */

import {
  LLMModel,
  TrainingConfig,
  TrainingSession,
  TrainingProgress,
  TrainingStatus,
  UploadedFile,
  Document,
  Dataset,
  TrainingReport,
  SessionComparison,
  ValidationResult
} from './index';

// Model Selector Component Props
export interface ModelSelectorProps {
  availableModels: LLMModel[];
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  loading?: boolean;
  disabled?: boolean;
  error?: string;
}

// Document Uploader Component Props
export interface DocumentUploaderProps {
  onFilesUploaded: (files: UploadedFile[]) => void;
  acceptedFormats: string[];
  maxFileSize: number;
  maxFiles?: number;
  disabled?: boolean;
  loading?: boolean;
}

export interface DocumentUploaderState {
  dragActive: boolean;
  uploading: boolean;
  uploadProgress: Record<string, number>;
  errors: Record<string, string>;
}

// Training Configuration Component Props
export interface TrainingConfigProps {
  modelId: string;
  config: TrainingConfig;
  onConfigChange: (config: TrainingConfig) => void;
  validation?: ValidationResult;
  templates?: TrainingConfigTemplate[];
  onSaveTemplate?: (name: string, description: string) => void;
  disabled?: boolean;
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

// Training Progress Component Props
export interface TrainingProgressProps {
  sessionId: string;
  status: TrainingStatus;
  progress: TrainingProgress;
  onCancel?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  showDetails?: boolean;
}

// Document Management Component Props
export interface DocumentManagementProps {
  documents: Document[];
  datasets: Dataset[];
  onDocumentDelete: (documentId: string) => void;
  onDatasetCreate: (name: string, description: string, documentIds: string[]) => void;
  onDatasetUpdate: (datasetId: string, updates: Partial<Dataset>) => void;
  onDatasetDelete: (datasetId: string) => void;
  loading?: boolean;
}

// Training Report Component Props
export interface TrainingReportProps {
  report: TrainingReport;
  session: TrainingSession;
  onExport: (format: string) => void;
  onCompare?: (sessionIds: string[]) => void;
  showComparison?: boolean;
}

// Session Comparison Component Props
export interface SessionComparisonProps {
  comparison: SessionComparison;
  onExport: (format: string) => void;
  onRemoveSession: (sessionId: string) => void;
  onAddSession: (sessionId: string) => void;
}

// Training Page Main Component Props
export interface TrainingPageProps {
  initialModel?: string;
  initialDocuments?: string[];
  initialConfig?: Partial<TrainingConfig>;
}

export interface TrainingPageState {
  selectedModel: string;
  uploadedDocuments: Document[];
  selectedDatasets: string[];
  trainingConfig: TrainingConfig;
  currentSession?: TrainingSession;
  availableModels: LLMModel[];
  datasets: Dataset[];
  loading: boolean;
  error?: string;
}

// Form Component Props
export interface FormFieldProps {
  label: string;
  name: string;
  type?: 'text' | 'number' | 'select' | 'checkbox' | 'textarea';
  value: any;
  onChange: (value: any) => void;
  options?: Array<{ value: any; label: string }>;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  help?: string;
  min?: number;
  max?: number;
  step?: number;
}

// Modal Component Props
export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  closable?: boolean;
}

// Loading Component Props
export interface LoadingProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  overlay?: boolean;
}

// Error Component Props
export interface ErrorDisplayProps {
  error: string | Error;
  onRetry?: () => void;
  onDismiss?: () => void;
  type?: 'error' | 'warning' | 'info';
}

// Chart Component Props
export interface ChartProps {
  type: 'line' | 'bar' | 'pie' | 'scatter';
  data: any[];
  options?: Record<string, any>;
  title?: string;
  height?: number;
  width?: number;
  responsive?: boolean;
}

// Notification Props
export interface NotificationProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
  onClose?: () => void;
  actions?: Array<{
    label: string;
    onClick: () => void;
  }>;
}