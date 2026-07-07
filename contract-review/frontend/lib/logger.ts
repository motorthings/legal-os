/**
 * Logging utility for frontend
 * Provides structured logging with environment-aware output and Sentry integration
 */

import type { ErrorInfo } from 'react';

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerOptions {
  isDevelopment?: boolean;
}

class Logger {
  private isDevelopment: boolean;

  constructor(options: LoggerOptions = {}) {
    this.isDevelopment = options.isDevelopment ?? process.env.NODE_ENV === 'development';
  }

  /**
   * Debug-level logging (only in development)
   */
  debug(...args: unknown[]): void {
    if (this.isDevelopment) {
      console.debug('[DEBUG]', ...args);
    }
  }

  /**
   * Info-level logging (only in development)
   */
  info(...args: unknown[]): void {
    if (this.isDevelopment) {
      console.info('[INFO]', ...args);
    }
  }

  /**
   * Warning-level logging (always logged)
   */
  warn(...args: unknown[]): void {
    console.warn('[WARN]', ...args);

    // Send warnings to Sentry in production
    if (!this.isDevelopment && typeof window !== 'undefined') {
      this.sendToSentry(args[0], { level: 'warning' });
    }
  }

  /**
   * Error-level logging (always logged, sent to Sentry in production)
   */
  error(...args: unknown[]): void {
    console.error('[ERROR]', ...args);

    // Send to Sentry in production
    if (!this.isDevelopment && typeof window !== 'undefined') {
      this.sendToSentry(args[0], {
        level: 'error',
        extra: args[1] ? { context: args[1] } : undefined
      });
    }
  }

  /**
   * Error logging specifically for React Error Boundaries
   * Includes component stack information for better debugging
   */
  errorWithReactInfo(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ERROR]', error, errorInfo);

    // Send to Sentry with React context in production
    if (!this.isDevelopment && typeof window !== 'undefined') {
      this.sendToSentry(error, {
        level: 'error',
        contexts: {
          react: {
            componentStack: errorInfo.componentStack,
          },
        },
        tags: {
          source: 'error-boundary',
        },
      });
    }
  }

  /**
   * Internal method to send errors to Sentry
   * Uses dynamic import to avoid bundling Sentry in development
   */
  private sendToSentry(error: unknown, options?: {
    level?: 'warning' | 'error' | 'fatal';
    contexts?: any;
    extra?: Record<string, unknown>;
    tags?: Record<string, string>;
  }): void {
    // Only send if Sentry DSN is configured
    if (!process.env.NEXT_PUBLIC_SENTRY_DSN) {
      return;
    }

    // Dynamically import Sentry to avoid bundling it in dev
    import('@sentry/nextjs')
      .then((Sentry) => {
        if (error instanceof Error) {
          Sentry.captureException(error, {
            level: options?.level || 'error',
            contexts: options?.contexts,
            extra: options?.extra,
            tags: options?.tags,
          });
        } else {
          // Capture non-Error objects as messages
          Sentry.captureMessage(String(error), {
            level: options?.level || 'error',
            extra: { originalError: error, ...options?.extra },
            tags: options?.tags,
          });
        }
      })
      .catch((err) => {
        // Silently fail if Sentry can't be loaded
        console.warn('Failed to load Sentry:', err);
      });
  }
}

// Export singleton instance
export const logger = new Logger();

// Export class for testing
export { Logger };
