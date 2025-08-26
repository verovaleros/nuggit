/**
 * Authentication Store for Nuggit Frontend
 * 
 * Manages global authentication state including user data, tokens,
 * and authentication operations. Provides persistent storage and
 * automatic token refresh capabilities.
 */

import { writable } from 'svelte/store';
import { push } from 'svelte-spa-router';

// Storage keys for persistence
const STORAGE_KEYS = {
  TOKEN: 'nuggit_access_token',
  REFRESH_TOKEN: 'nuggit_refresh_token',
  USER: 'nuggit_user',
  REMEMBER_ME: 'nuggit_remember_me'
};

// API base URL - should be configurable via environment
const API_BASE_URL = 'http://localhost:8001';

/**
 * Initial authentication state
 */
const initialState = {
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  isInitialized: false
};

/**
 * Create the authentication store with methods
 */
function createAuthStore() {
  const { subscribe, set, update } = writable(initialState);

  return {
    subscribe,

    /**
     * Initialize auth state from localStorage on app startup
     */
    async initialize() {
      update(state => ({ ...state, isLoading: true }));

      try {
        const token = localStorage.getItem(STORAGE_KEYS.TOKEN);
        const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
        const userStr = localStorage.getItem(STORAGE_KEYS.USER);
        const rememberMe = localStorage.getItem(STORAGE_KEYS.REMEMBER_ME) === 'true';

        if (token && userStr) {
          const user = JSON.parse(userStr);
          
          // Verify token is still valid by checking user profile
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });

          if (response.ok) {
            const currentUser = await response.json();
            update(state => ({
              ...state,
              user: currentUser,
              token,
              refreshToken,
              isAuthenticated: true,
              isLoading: false,
              error: null,
              isInitialized: true
            }));
          } else {
            // Token is invalid, clear storage
            this.clearStorage();
            update(state => ({
              ...initialState,
              isInitialized: true
            }));
          }
        } else {
          update(state => ({
            ...initialState,
            isInitialized: true
          }));
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        this.clearStorage();
        update(state => ({
          ...initialState,
          error: 'Failed to initialize authentication',
          isInitialized: true
        }));
      }
    },

    /**
     * Login user with email/username and password
     */
    async login(credentials) {
      update(state => ({ ...state, isLoading: true, error: null }));

      try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(credentials)
        });

        const data = await response.json();

        if (response.ok) {
          const { access_token, refresh_token, user } = data;
          
          // Store tokens and user data
          this.setAuthData(access_token, refresh_token, user, credentials.remember_me);
          
          update(state => ({
            ...state,
            user,
            token: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null
          }));

          // Redirect to home page after successful login
          push('/home');

          return { success: true, user };
        } else {
          const errorMessage = data.message || 'Login failed';
          update(state => ({
            ...state,
            isLoading: false,
            error: errorMessage
          }));
          return { success: false, error: errorMessage };
        }
      } catch (error) {
        console.error('Login error:', error);
        const errorMessage = 'Network error. Please try again.';
        update(state => ({
          ...state,
          isLoading: false,
          error: errorMessage
        }));
        return { success: false, error: errorMessage };
      }
    },

    /**
     * Register new user
     */
    async register(userData) {
      update(state => ({ ...state, isLoading: true, error: null }));

      try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(userData)
        });

        const data = await response.json();

        if (response.ok) {
          update(state => ({
            ...state,
            isLoading: false,
            error: null
          }));
          return { success: true, message: data.message };
        } else {
          const errorMessage = data.message || 'Registration failed';
          update(state => ({
            ...state,
            isLoading: false,
            error: errorMessage
          }));
          return { success: false, error: errorMessage };
        }
      } catch (error) {
        console.error('Registration error:', error);
        const errorMessage = 'Network error. Please try again.';
        update(state => ({
          ...state,
          isLoading: false,
          error: errorMessage
        }));
        return { success: false, error: errorMessage };
      }
    },

    /**
     * Logout user and clear all auth data
     */
    logout() {
      this.clearStorage();
      set({
        ...initialState,
        isInitialized: true  // Keep initialized state to prevent re-initialization
      });
      push('/');
    },

    /**
     * Refresh access token using refresh token
     */
    async refreshToken() {
      const currentState = this.getCurrentState();
      if (!currentState.refreshToken) {
        this.logout();
        return false;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            refresh_token: currentState.refreshToken
          })
        });

        if (response.ok) {
          const data = await response.json();
          const newToken = data.access_token;
          
          // Update token in storage and state
          localStorage.setItem(STORAGE_KEYS.TOKEN, newToken);
          update(state => ({
            ...state,
            token: newToken,
            error: null
          }));
          
          return true;
        } else {
          // Refresh token is invalid, logout user
          this.logout();
          return false;
        }
      } catch (error) {
        console.error('Token refresh error:', error);
        this.logout();
        return false;
      }
    },

    /**
     * Clear authentication error
     */
    clearError() {
      update(state => ({ ...state, error: null }));
    },

    /**
     * Store authentication data in localStorage
     */
    setAuthData(token, refreshToken, user, rememberMe = false) {
      localStorage.setItem(STORAGE_KEYS.TOKEN, token);
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
      localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, rememberMe.toString());
    },

    /**
     * Clear all authentication data from localStorage
     */
    clearStorage() {
      Object.values(STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key);
      });
    },

    /**
     * Get current state (for internal use)
     */
    getCurrentState() {
      let currentState;
      subscribe(state => currentState = state)();
      return currentState;
    },

    /**
     * Check if user has admin privileges
     */
    isAdmin() {
      const state = this.getCurrentState();
      return state.user?.is_admin || false;
    },

    /**
     * Get current user
     */
    getUser() {
      const state = this.getCurrentState();
      return state.user;
    },

    /**
     * Get current token
     */
    getToken() {
      const state = this.getCurrentState();
      return state.token;
    },

    /**
     * Update user profile data
     */
    updateUser(updatedUserData) {
      update(state => {
        const newUser = { ...state.user, ...updatedUserData };

        // Update localStorage
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(newUser));

        return {
          ...state,
          user: newUser
        };
      });
    }
  };
}

// Export the auth store instance
export const authStore = createAuthStore();
