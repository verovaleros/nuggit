/**
 * Authentication Guards for Nuggit Frontend
 *
 * Protected route wrapper that checks authentication status,
 * redirects to login for unauthenticated users, and validates
 * admin permissions for admin-only routes.
 */

import { get } from 'svelte/store';
import { push } from 'svelte-spa-router';
import { authStore } from '../stores/authStore.js';

/**
 * Route guard that requires authentication
 * Redirects to login if user is not authenticated
 */
export function requireAuth(component) {
  return (detail) => {
    const authState = get(authStore);

    // If auth is not initialized, allow component to render and handle auth internally
    if (!authState.isInitialized) {
      return component;
    }

    // Auth is initialized, check authentication
    if (!authState.isAuthenticated) {
      // Store the intended route for redirect after login
      sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
      push('/login');
      return component; // Return component instead of null to avoid Svelte errors
    }

    return component;
  };
}

/**
 * Route guard that requires admin privileges
 * Redirects to home if user is not admin
 */
export function requireAdmin(component) {
  return (detail) => {
    const authState = get(authStore);

    // If auth is not initialized, allow component to render and handle auth internally
    if (!authState.isInitialized) {
      return component;
    }

    // Auth is initialized, check authentication and admin status
    if (!authState.isAuthenticated) {
      sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
      push('/login');
      return component;
    }

    if (!authState.user?.is_admin) {
      // User is authenticated but not admin, redirect to home
      push('/home');
      return component;
    }

    return component;
  };
}

/**
 * Route guard that requires user to be verified
 * Redirects to email verification if user is not verified
 */
export function requireVerified(component) {
  return (detail) => {
    const authState = get(authStore);

    // If auth is not initialized, allow component to render and handle auth internally
    if (!authState.isInitialized) {
      return component;
    }

    // Auth is initialized, check authentication and verification
    if (!authState.isAuthenticated) {
      sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
      push('/login');
      return component;
    }

    if (!authState.user?.is_verified) {
      // User is authenticated but not verified
      push('/verify-email');
      return component;
    }

    return component;
  };
}

/**
 * Route guard that redirects authenticated users away from auth pages
 * Used for login, register pages to prevent authenticated users from accessing them
 */
export function requireGuest(component) {
  return (detail) => {
    const authState = get(authStore);

    // If auth is not initialized, allow component to render and handle auth internally
    if (!authState.isInitialized) {
      return component;
    }

    // Auth is initialized, check authentication
    if (authState.isAuthenticated) {
      // User is authenticated, redirect to home
      push('/home');
      return component;
    }

    return component;
  };
}

/**
 * Utility function to get redirect URL after login
 */
export function getRedirectAfterLogin() {
  const redirectUrl = sessionStorage.getItem('nuggit_redirect_after_login');
  sessionStorage.removeItem('nuggit_redirect_after_login');
  return redirectUrl || '#/';
}

/**
 * Utility function to handle post-login redirect
 */
export function handlePostLoginRedirect() {
  const redirectUrl = getRedirectAfterLogin();
  if (redirectUrl && redirectUrl !== '#/login' && redirectUrl !== '#/register') {
    // Remove the hash if present and navigate
    const cleanUrl = redirectUrl.startsWith('#') ? redirectUrl.substring(1) : redirectUrl;
    push(cleanUrl);
  } else {
    push('/');
  }
}
