import * as Sentry from "@sentry/nextjs";

/**
 * Sentry Client Configuration for Browser/Frontend
 *
 * Note: You may see a browser console warning about "non-passive event listeners"
 * from Sentry's auto-instrumentation. This is a known low-priority performance
 * warning from the Sentry SDK and does not affect functionality. It only impacts
 * mobile touch scrolling slightly. This will be resolved in future Sentry updates.
 */

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Adjust this value in production, or use tracesSampler for greater control
  tracesSampleRate: 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Replay configuration
  replaysOnErrorSampleRate: 1.0,
  replaysSessionSampleRate: 0.1,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  // Filter out sensitive data
  beforeSend(event) {
    // Remove sensitive headers
    if (event.request?.headers) {
      delete event.request.headers['authorization'];
      delete event.request.headers['cookie'];
    }

    return event;
  },

  // Environment
  environment: process.env.NODE_ENV || 'development',

  // Ignore specific errors
  ignoreErrors: [
    // Network errors
    'NetworkError',
    'Network request failed',
    'Failed to fetch',

    // Browser extensions
    'ResizeObserver loop limit exceeded',
    'Non-Error promise rejection captured',
    'Cannot create item with duplicate id',
    /chrome-extension:\/\//,
    /No tab with id:/,
  ],
});
