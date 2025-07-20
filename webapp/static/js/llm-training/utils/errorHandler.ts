/**
 * Error handling utilities for LLM Training Page
 */

import { ErrorType, ErrorResponse } from '../types';

export class LLMTrainingError extends Error {
  public readonly type: ErrorType;
  public readonly details?: Record<string, any>;
  public readonly suggestions?: string[];

  constructor(
    type: ErrorType,
    message: string,
    details?: Record<string, any>,
    suggestions?: string[]
  ) {
    super(message);
    this.name = 'LLMTrainingError';
    this.type = type;
    this.details = details;
    this.suggestions = suggestions;
  }

  static fromApiError(error: ErrorResponse): LLMTrainingError {
    return new LLMTrainingError(
      error.type,
      error.message,
      error.details,
      error.suggestions
    );
  }

  toErrorResponse(): ErrorResponse {
    return {
      type: this.type,
      message: this.message,
      details: this.details,
      suggestions: this.suggestions
    };
  }
}

export const ErrorHandler = {
  /**
   * Handle API errors and convert to LLMTrainingError
   */
  handleApiError(error: any): LLMTrainingError {
    if (error instanceof LLMTrainingError) {
      return error;
    }

    if (error.response?.data?.error) {
      return LLMTrainingError.fromApiError(error.response.data.error);
    }

    if (error.code === 'NETWORK_ERROR') {
      return new LLMTrainingError(
        ErrorType.NETWORK_ERROR,
        'Network connection failed. Please check your internet connection.',
        { originalError: error.message },
        ['Check your internet connection', 'Try again in a few moments']
      );
    }

    return new LLMTrainingError(
      ErrorType.API_ERROR,
      error.message || 'An unexpected error occurred',
      { originalError: error }
    );
  },

  /**
   * Handle file upload errors
   */
  handleUploadError(file: File, error: any): LLMTrainingError {
    if (error.code === 'FILE_TOO_LARGE') {
      return new LLMTrainingError(
        ErrorType.UPLOAD_ERROR,
        `File "${file.name}" is too large. Maximum size is 50MB.`,
        { fileName: file.name, fileSize: file.size },
        ['Compress the file', 'Split into smaller files']
      );
    }

    if (error.code === 'UNSUPPORTED_FORMAT') {
      return new LLMTrainingError(
        ErrorType.UPLOAD_ERROR,
        `File format "${file.type}" is not supported.`,
        { fileName: file.name, fileType: file.type },
        ['Convert to a supported format (.txt, .pdf, .docx, .md, .json)']
      );
    }

    return new LLMTrainingError(
      ErrorType.UPLOAD_ERROR,
      `Failed to upload "${file.name}": ${error.message}`,
      { fileName: file.name, originalError: error }
    );
  },

  /**
   * Handle validation errors
   */
  handleValidationError(field: string, message: string, value?: any): LLMTrainingError {
    return new LLMTrainingError(
      ErrorType.VALIDATION_ERROR,
      `Validation failed for ${field}: ${message}`,
      { field, value },
      ['Check the input value', 'Refer to the field requirements']
    );
  },

  /**
   * Handle training errors
   */
  handleTrainingError(sessionId: string, error: any): LLMTrainingError {
    return new LLMTrainingError(
      ErrorType.TRAINING_ERROR,
      `Training session ${sessionId} failed: ${error.message}`,
      { sessionId, originalError: error },
      ['Check training configuration', 'Verify document quality', 'Try with different parameters']
    );
  },

  /**
   * Get user-friendly error message
   */
  getUserMessage(error: LLMTrainingError): string {
    switch (error.type) {
      case ErrorType.NETWORK_ERROR:
        return 'Connection problem. Please check your internet and try again.';
      case ErrorType.UPLOAD_ERROR:
        return 'File upload failed. Please check the file and try again.';
      case ErrorType.VALIDATION_ERROR:
        return 'Please check your input and correct any errors.';
      case ErrorType.TRAINING_ERROR:
        return 'Training failed. Please review your configuration and try again.';
      case ErrorType.MODEL_ERROR:
        return 'Model is currently unavailable. Please try a different model.';
      default:
        return 'Something went wrong. Please try again.';
    }
  },

  /**
   * Get error suggestions for user
   */
  getSuggestions(error: LLMTrainingError): string[] {
    return error.suggestions || [
      'Try refreshing the page',
      'Check your internet connection',
      'Contact support if the problem persists'
    ];
  }
};