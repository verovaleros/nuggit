/**
 * Authentication Guards for Nuggit Frontend
 *
 * Protected route wrapper that checks authentication status,
 * redirects to login for unauthenticated users, and validates
 * admin permissions for admin-only routes.
 */

import AuthWrapper from '../../components/AuthWrapper.svelte';

/**
 * Route guard that requires authentication
 * Redirects to login if user is not authenticated
 */
export function requireAuth(component) {
  return (detail) => {
    return {
      component: AuthWrapper,
      props: {
        component: component,
        requireAuth: true
      }
    };
  };
}

/**
 * Route guard that requires admin privileges
 * Redirects to home if user is not admin
 */
export function requireAdmin(component) {
  return (detail) => {
    return {
      component: AuthWrapper,
      props: {
        component: component,
        requireAdmin: true
      }
    };
  };
}

/**
 * Route guard that requires user to be verified
 * Redirects to email verification if user is not verified
 */
export function requireVerified(component) {
  return (detail) => {
    return {
      component: AuthWrapper,
      props: {
        component: component,
        requireAuth: true,
        requireVerified: true
      }
    };
  };
}

/**
 * Route guard that redirects authenticated users away from auth pages
 * Used for login, register pages to prevent authenticated users from accessing them
 */
export function requireGuest(component) {
  return (detail) => {
    return {
      component: AuthWrapper,
      props: {
        component: component,
        requireGuest: true
      }
    };
  };
}

/**
 * Composite guard that requires both authentication and admin privileges
 */
export function requireAuthAndAdmin(component) {
  return requireAuth(requireAdmin(component));
}

/**
 * Composite guard that requires authentication and email verification
 */
export function requireAuthAndVerified(component) {
  return requireAuth(requireVerified(component));
}

/**
 * Utility function to check if user has permission for a specific action
 */
export function hasPermission(permission) {
  const authState = get(authStore);
  
  if (!authState.isAuthenticated || !authState.user) {
    return false;
  }
  
  const user = authState.user;
  
  switch (permission) {
    case 'admin':
      return user.is_admin;
    case 'verified':
      return user.is_verified;
    case 'active':
      return user.is_active;
    case 'manage_users':
      return user.is_admin;
    case 'manage_repositories':
      return user.is_admin;
    case 'view_admin_panel':
      return user.is_admin;
    default:
      return false;
  }
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

/**
 * Higher-order function to create custom route guards
 */
export function createRouteGuard(checkFunction, redirectPath = '/login') {
  return function(component) {
    return function(detail) {
      const authState = get(authStore);
      
      if (!authState.isInitialized) {
        return new Promise((resolve) => {
          const unsubscribe = authStore.subscribe((state) => {
            if (state.isInitialized) {
              unsubscribe();
              if (checkFunction(state)) {
                resolve(component);
              } else {
                if (redirectPath === '/login') {
                  sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
                }
                push(redirectPath);
                resolve(null);
              }
            }
          });
        });
      }
      
      if (checkFunction(authState)) {
        return component;
      } else {
        if (redirectPath === '/login') {
          sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
        }
        push(redirectPath);
        return null;
      }
    };
  };
}

/**
 * Export commonly used guard combinations
 */
export const guards = {
  auth: requireAuth,
  admin: requireAdmin,
  verified: requireVerified,
  guest: requireGuest,
  authAndAdmin: requireAuthAndAdmin,
  authAndVerified: requireAuthAndVerified
};
