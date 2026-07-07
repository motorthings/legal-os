/**
 * API utilities for making authenticated requests
 */

import { supabase } from './supabase';
import { API_BASE_URL } from './config';
import { logger } from './logger';
import type { ApiResponse } from '@/types';

const API_BASE = API_BASE_URL;

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
  timeout?: number; // Timeout in milliseconds
}

/**
 * Custom error class for API errors
 */
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Make an authenticated API request
 * Automatically adds the JWT token from Supabase auth
 */
export async function authenticatedFetch(
  endpoint: string,
  options: RequestOptions = {}
): Promise<Response> {
  // Get current session
  const {
    data: { session },
  } = await supabase.auth.getSession();

  // For demo: Allow requests without auth (backend will handle authorization)
  // In production, you'd enforce authentication here
  const headers: Record<string, string> = {
    ...options.headers,
  };

  // Only add Content-Type if body is not FormData (browser will set it automatically for FormData)
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  // Add authorization header if session exists
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  }

  // Make the request
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;

  // Add timeout to prevent hanging requests (default 30s, configurable via options.timeout)
  const controller = new AbortController();
  const timeoutMs = options.timeout || 30000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout - please try again');
    }
    throw error;
  }
}

/**
 * Helper to handle API response and errors
 */
async function handleResponse<T = unknown>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: Record<string, unknown> = {};
    try {
      errorData = await response.json();
    } catch {
      // Response body is not JSON
      errorData = { message: await response.text() };
    }

    throw new APIError(
      (errorData.detail as string) || (errorData.message as string) || `Request failed with status ${response.status}`,
      response.status,
      errorData
    );
  }

  // Try to parse JSON, return empty object if no content
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return await response.json();
  }

  return {} as T;
}

/**
 * Make a GET request with authentication
 * @throws {APIError} If the request fails
 */
export async function apiGet<T = unknown>(endpoint: string): Promise<T> {
  const response = await authenticatedFetch(endpoint, { method: 'GET' });
  return handleResponse<T>(response);
}

/**
 * Make a POST request with authentication
 * @param options.timeout - Optional timeout in milliseconds (default 30s)
 * @throws {APIError} If the request fails
 */
export async function apiPost<T = unknown>(
  endpoint: string,
  data?: Record<string, unknown>,
  options?: { timeout?: number }
): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
    timeout: options?.timeout,
  });
  return handleResponse<T>(response);
}

/**
 * Make a PUT request with authentication
 * @throws {APIError} If the request fails
 */
export async function apiPut<T = unknown>(endpoint: string, data?: Record<string, unknown>): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
  return handleResponse<T>(response);
}

/**
 * Make a PATCH request with authentication
 * @throws {APIError} If the request fails
 */
export async function apiPatch<T = unknown>(endpoint: string, data?: Record<string, unknown>): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'PATCH',
    body: data ? JSON.stringify(data) : undefined,
  });
  return handleResponse<T>(response);
}

/**
 * Make a DELETE request with authentication
 * @throws {APIError} If the request fails
 */
export async function apiDelete<T = unknown>(endpoint: string, data?: Record<string, unknown>): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'DELETE',
    body: data ? JSON.stringify(data) : undefined,
  });
  return handleResponse<T>(response);
}

/**
 * Make a POST request with FormData (for file uploads)
 * @param options.timeout - Optional timeout in milliseconds (default 60s for uploads)
 * @throws {APIError} If the request fails
 */
export async function apiPostFormData<T = unknown>(
  endpoint: string,
  formData: FormData,
  options?: { timeout?: number }
): Promise<T> {
  const response = await authenticatedFetch(endpoint, {
    method: 'POST',
    body: formData,
    timeout: options?.timeout || 60000, // 60s default for file uploads
  });
  return handleResponse<T>(response);
}
