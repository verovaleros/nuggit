/**
 * API Client for Nuggit Frontend
 * 
 * Centralized HTTP client with automatic authentication header injection,
 * token refresh on 401 responses, error handling, and request/response
 * interceptors. Replaces direct fetch calls throughout the application.
 */

import { authStore } from '../stores/authStore.js';
import { push } from 'svelte-spa-router';

// API configuration
const API_CONFIG = {
  BASE_URL: 'http://localhost:8001',
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000 // 1 second
};

/**
 * HTTP status codes
 */
const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500
};

/**
 * API Client class with authentication and error handling
 */
class ApiClient {
  constructor(baseURL = API_CONFIG.BASE_URL) {
    this.baseURL = baseURL;
    this.isRefreshing = false;
    this.failedQueue = [];
  }

  /**
   * Make authenticated HTTP request
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = await this.buildRequestConfig(options);



    try {
      const response = await this.fetchWithTimeout(url, config);
      return await this.handleResponse(response, endpoint, options);
    } catch (error) {
      return this.handleError(error, endpoint, options);
    }
  }

  /**
   * Build request configuration with auth headers
   */
  async buildRequestConfig(options) {
    const token = authStore.getToken();
    
    const config = {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    // Add authentication header if token exists
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  }

  /**
   * Fetch with timeout support
   */
  async fetchWithTimeout(url, config) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);

    try {
      const response = await fetch(url, {
        ...config,
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /**
   * Handle HTTP response
   */
  async handleResponse(response, endpoint, originalOptions) {
    // Handle 401 Unauthorized - attempt token refresh
    if (response.status === HTTP_STATUS.UNAUTHORIZED) {
      return await this.handleUnauthorized(endpoint, originalOptions);
    }

    // Handle other error status codes
    if (!response.ok) {
      const errorData = await this.parseErrorResponse(response);
      throw new ApiError(response.status, errorData.message || 'Request failed', errorData);
    }

    // Parse successful response
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  }

  /**
   * Handle 401 Unauthorized responses with token refresh
   */
  async handleUnauthorized(endpoint, originalOptions) {
    // If already refreshing, queue the request
    if (this.isRefreshing) {
      return new Promise((resolve, reject) => {
        this.failedQueue.push({ resolve, reject, endpoint, options: originalOptions });
      });
    }

    this.isRefreshing = true;

    try {
      const refreshSuccess = await authStore.refreshToken();
      
      if (refreshSuccess) {
        // Process queued requests
        this.processQueue(null);
        // Retry original request
        return await this.request(endpoint, originalOptions);
      } else {
        // Refresh failed, redirect to login
        this.processQueue(new Error('Authentication failed'));
        push('/login');
        throw new ApiError(HTTP_STATUS.UNAUTHORIZED, 'Authentication required');
      }
    } catch (error) {
      this.processQueue(error);
      push('/login');
      throw error;
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Process queued requests after token refresh
   */
  processQueue(error) {
    this.failedQueue.forEach(({ resolve, reject, endpoint, options }) => {
      if (error) {
        reject(error);
      } else {
        resolve(this.request(endpoint, options));
      }
    });
    
    this.failedQueue = [];
  }

  /**
   * Parse error response
   */
  async parseErrorResponse(response) {
    try {
      const errorData = await response.json();



      return errorData;
    } catch {
      const fallbackMessage = `HTTP ${response.status}: ${response.statusText}`;



      return { message: fallbackMessage };
    }
  }

  /**
   * Handle request errors
   */
  handleError(error, endpoint, options) {
    console.error(`API request failed: ${endpoint}`, error);
    
    if (error.name === 'AbortError') {
      throw new ApiError(0, 'Request timeout');
    }
    
    if (error instanceof ApiError) {
      throw error;
    }
    
    throw new ApiError(0, 'Network error. Please check your connection.');
  }

  // ============================================================================
  // AUTHENTICATION ENDPOINTS
  // ============================================================================

  /**
   * Login user
   */
  async login(credentials) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials)
    });
  }

  /**
   * Register user
   */
  async register(userData) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData)
    });
  }

  /**
   * Get current user profile
   */
  async getUserProfile() {
    return this.request('/auth/me');
  }

  /**
   * Update current user profile
   */
  async updateUserProfile(profileData) {
    return this.request('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(profileData)
    });
  }

  /**
   * Change password
   */
  async changePassword(passwordData) {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(passwordData)
    });
  }

  /**
   * Get current user profile
   */
  async getCurrentUser() {
    return this.request('/auth/me');
  }

  /**
   * Refresh access token
   */
  async refreshToken(refreshToken) {
    return this.request('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken })
    });
  }

  // ============================================================================
  // REPOSITORY ENDPOINTS
  // ============================================================================

  /**
   * Get all repositories
   */
  async getRepositories() {
    return this.request('/repositories/');
  }

  /**
   * Get repository by ID
   */
  async getRepository(repoId) {
    const encodedId = encodeURIComponent(repoId);
    return this.request(`/repositories/${encodedId}`);
  }

  /**
   * Add new repository
   */
  async addRepository(repoData) {
    return this.request('/repositories/', {
      method: 'POST',
      body: JSON.stringify(repoData)
    });
  }

  /**
   * Update repository
   */
  async updateRepository(repoId, updateData) {
    const encodedId = encodeURIComponent(repoId);
    return this.request(`/repositories/${encodedId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData)
    });
  }

  /**
   * Batch import repositories
   */
  async batchImportRepositories(batchData) {
    return this.request('/repositories/batch', {
      method: 'POST',
      body: JSON.stringify(batchData)
    });
  }

  /**
   * Update repository metadata
   */
  async updateRepositoryMetadata(repoId, metadata) {
    const encodedId = encodeURIComponent(repoId);
    return this.request(`/repositories/${encodedId}/metadata/`, {
      method: 'PUT',
      body: JSON.stringify(metadata)
    });
  }

  /**
   * Delete repository
   */
  async deleteRepository(repoId) {
    const encodedId = encodeURIComponent(repoId);
    return this.request(`/repositories/${encodedId}`, {
      method: 'DELETE'
    });
  }

  /**
   * Get repository commits
   */
  async getRepositoryCommits(repoId, limit = 10) {
    const encodedId = encodeURIComponent(repoId);
    return this.request(`/repositories/${encodedId}/commits/?limit=${limit}`);
  }

  /**
   * Add repository comment
   */
  async addRepositoryComment(repoId, commentData) {
    const encodedId = encodeURIComponent(repoId);
    return this.request(`/repositories/${encodedId}/comments`, {
      method: 'POST',
      body: JSON.stringify(commentData)
    });
  }

  // ============================================================================
  // ADMIN ENDPOINTS
  // ============================================================================

  /**
   * Get all users (admin only)
   */
  async getUsers(page = 1, perPage = 20, search = null, isActive = null) {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString()
    });

    if (search) params.append('search', search);
    if (isActive !== null) params.append('is_active', isActive.toString());

    return this.request(`/auth/admin/users?${params}`);
  }

  /**
   * Get user details (admin only)
   */
  async getUserDetails(userId) {
    return this.request(`/auth/admin/users/${userId}`);
  }

  /**
   * Update user (admin only)
   */
  async updateUser(userId, updateData) {
    return this.request(`/auth/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(updateData)
    });
  }

  /**
   * Get admin statistics
   */
  async getAdminStats() {
    return this.request('/auth/admin/stats');
  }

  /**
   * Get system health
   */
  async getSystemHealth() {
    return this.request('/health/health');
  }

  /**
   * Get backups (admin only)
   */
  async getBackups() {
    return this.request('/health/health/backups');
  }
}

/**
 * Custom API Error class
 */
class ApiError extends Error {
  constructor(status, message, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export { ApiError };
