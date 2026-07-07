/**
 * Application configuration
 * Centralized configuration values for the frontend application
 */

/**
 * Backend API base URL
 * Uses NEXT_PUBLIC_API_URL from environment variables
 * Falls back to localhost for development if not set
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
