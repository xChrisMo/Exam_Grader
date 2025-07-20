/**
 * Utility functions and helpers for LLM Training Page
 */

export * from './errorHandler';

// File utilities
export const FileUtils = {
  /**
   * Format file size in human readable format
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  /**
   * Check if file type is supported
   */
  isSupportedFormat(file: File, supportedFormats: string[]): boolean {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    return supportedFormats.includes(extension);
  },

  /**
   * Generate unique file ID
   */
  generateFileId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }
};

// Date utilities
export const DateUtils = {
  /**
   * Format date for display
   */
  formatDate(date: Date): string {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  },

  /**
   * Get relative time string
   */
  getRelativeTime(date: Date): string {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minutes ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays < 7) return `${diffDays} days ago`;
    
    return DateUtils.formatDate(date);
  },

  /**
   * Format duration in seconds to human readable
   */
  formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  }
};

// Training utilities
export const TrainingUtils = {
  /**
   * Calculate estimated time remaining
   */
  calculateETA(progress: number, startTime: Date): number {
    if (progress <= 0) return 0;
    
    const elapsed = (Date.now() - startTime.getTime()) / 1000;
    const rate = progress / elapsed;
    const remaining = (100 - progress) / rate;
    
    return Math.max(0, remaining);
  },

  /**
   * Get status color for UI
   */
  getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      'pending': 'gray',
      'initializing': 'blue',
      'running': 'green',
      'completed': 'green',
      'failed': 'red',
      'cancelled': 'orange',
      'paused': 'yellow'
    };
    return colors[status] || 'gray';
  },

  /**
   * Validate training configuration
   */
  validateConfig(config: any): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!config.learningRate || config.learningRate <= 0) {
      errors.push('Learning rate must be greater than 0');
    }

    if (!config.batchSize || config.batchSize <= 0) {
      errors.push('Batch size must be greater than 0');
    }

    if (!config.epochs || config.epochs <= 0) {
      errors.push('Epochs must be greater than 0');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }
};

// API utilities
export const ApiUtils = {
  /**
   * Build query string from parameters
   */
  buildQueryString(params: Record<string, any>): string {
    const searchParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    
    return searchParams.toString();
  },

  /**
   * Get authorization header
   */
  getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
};