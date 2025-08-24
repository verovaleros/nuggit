<!--
  Authentication Wrapper Component
  
  Wraps components that require authentication and handles redirects
  without causing Svelte component resolution errors.
-->

<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authStore } from '../lib/stores/authStore.js';

  export let component;
  export let requireAuth = false;
  export let requireAdmin = false;
  export let requireGuest = false;

  // Auth state
  $: authState = $authStore;
  $: isAuthenticated = authState.isAuthenticated;
  $: isInitialized = authState.isInitialized;
  $: user = authState.user;

  let shouldRender = false;
  let redirecting = false;

  // Check authentication and authorization
  $: {
    if (isInitialized && !redirecting) {
      if (requireGuest && isAuthenticated) {
        // Guest-only route but user is authenticated
        redirecting = true;
        push('/home');
        shouldRender = false;
      } else if (requireAuth && !isAuthenticated) {
        // Auth required but user not authenticated
        redirecting = true;
        sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
        push('/login');
        shouldRender = false;
      } else if (requireAdmin && (!isAuthenticated || !user?.is_admin)) {
        // Admin required but user not admin
        redirecting = true;
        if (!isAuthenticated) {
          sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
          push('/login');
        } else {
          push('/home');
        }
        shouldRender = false;
      } else {
        // All checks passed
        shouldRender = true;
        redirecting = false;
      }
    } else if (!isInitialized) {
      // Auth not initialized yet, don't render
      shouldRender = false;
    }
  }
</script>

{#if !isInitialized}
  <div class="auth-loading">
    <div class="loading-spinner"></div>
    <p>Loading...</p>
  </div>
{:else if shouldRender && component}
  <svelte:component this={component} />
{:else if redirecting}
  <div class="auth-redirecting">
    <div class="loading-spinner"></div>
    <p>Redirecting...</p>
  </div>
{/if}

<style>
  .auth-loading,
  .auth-redirecting {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    gap: 1rem;
  }

  .loading-spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #f3f4f6;
    border-top: 3px solid #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  p {
    color: #6b7280;
    font-size: 0.875rem;
  }
</style>
