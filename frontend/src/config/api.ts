/**
 * CLARIUS Frontend - Centralized API Configuration & Utility Module
 * 
 * Provides environment-aware API URL generation and reusable fetch helpers
 * with automatic authorization header injection.
 */

export const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Returns full URL for an API endpoint path.
 * @param path Endpoint path (e.g. '/analytics/stream' or 'auth/login')
 */
export function getApiUrl(path: string): string {
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

/**
 * Reusable fetch wrapper with authorization header injection and standard JSON handling.
 * @param path Endpoint path or full URL
 * @param options Standard RequestInit fetch options
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const url = path.startsWith('http://') || path.startsWith('https://') ? path : getApiUrl(path);
  const token = localStorage.getItem('token');

  const headers = new Headers(options.headers || {});
  
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  return fetch(url, {
    ...options,
    headers
  });
}
