/**
 * Main entry point for LLM Training Page module
 * Exports all types, components, and services
 */

// Core types and interfaces
export * from './types';
export * from './types/components';
export * from './types/services';
export * from './types/api';

// Components
export * from './components';

// Services
export * from './services';

// Constants
export const LLM_TRAINING_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  SUPPORTED_FORMATS: ['.txt', '.pdf', '.docx', '.md', '.json'],
  DEFAULT_BATCH_SIZE: 32,
  DEFAULT_LEARNING_RATE: 0.001,
  DEFAULT_EPOCHS: 10,
  MAX_DOCUMENTS_PER_SESSION: 100,
  WEBSOCKET_RECONNECT_INTERVAL: 5000,
  API_TIMEOUT: 30000,
  PROGRESS_UPDATE_INTERVAL: 1000
} as const;

// Version
export const VERSION = '1.0.0';