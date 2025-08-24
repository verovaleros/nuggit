<script>
  import { onMount } from 'svelte';
  import Router from 'svelte-spa-router';
  import routes from './routes/routes.js';
  import ErrorBoundary from './components/ErrorBoundary.svelte';
  import Navigation from './components/Navigation.svelte';
  import { authStore } from './lib/stores/authStore.js';

  // Auth state
  $: authState = $authStore;
  $: isInitialized = authState.isInitialized;

  // Global error handler for the app
  function handleAppError(event) {
    console.error('App-level error:', event.detail);
    // Could send to error reporting service here
  }

  function handleRetry() {
    // Force page reload on retry
    window.location.reload();
  }

  // Initialize authentication on app startup
  onMount(async () => {
    try {
      await authStore.initialize();
    } catch (error) {
      console.error('Failed to initialize auth:', error);
    }
  });
</script>

<!-- Show loading screen until auth is initialized -->
{#if !isInitialized}
  <div class="app-loading">
    <div class="loading-container">
      <div class="loading-spinner"></div>
      <p>Initializing Nuggit...</p>
    </div>
  </div>
{:else}
  <ErrorBoundary on:error={handleAppError} on:retry={handleRetry}>
    <div class="app-container">
      <Navigation />
      <main class="main-content">
        <Router {routes} />
      </main>
    </div>
  </ErrorBoundary>
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    background-color: #f8f9fa;
  }

  :global(*) {
    box-sizing: border-box;
  }

  .app-loading {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .loading-container {
    text-align: center;
    color: white;
  }

  .loading-container p {
    margin-top: 1rem;
    font-size: 1.1rem;
    font-weight: 500;
  }

  .loading-spinner {
    width: 3rem;
    height: 3rem;
    border: 4px solid rgba(255, 255, 255, 0.3);
    border-top: 4px solid white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .main-content {
    flex: 1;
    padding-top: 60px; /* Account for fixed navigation */
  }

  /* Global styles for consistent UI */
  :global(.btn) {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  :global(.btn-primary) {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  :global(.btn-primary:hover) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  :global(.btn-secondary) {
    background: #6c757d;
    color: white;
  }

  :global(.btn-secondary:hover) {
    background: #5a6268;
  }

  :global(.btn-danger) {
    background: #dc3545;
    color: white;
  }

  :global(.btn-danger:hover) {
    background: #c82333;
  }

  :global(.btn-success) {
    background: #28a745;
    color: white;
  }

  :global(.btn-success:hover) {
    background: #218838;
  }

  :global(.btn:disabled) {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none !important;
  }

  /* Global form styles */
  :global(.form-control) {
    padding: 0.75rem;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.2s ease;
    width: 100%;
  }

  :global(.form-control:focus) {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  :global(.form-control.error) {
    border-color: #e74c3c;
  }

  /* Global card styles */
  :global(.card) {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
    margin-bottom: 1rem;
  }

  :global(.card-header) {
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e1e5e9;
  }

  :global(.card-title) {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #333;
  }

  /* Global utility classes */
  :global(.text-center) {
    text-align: center;
  }

  :global(.text-muted) {
    color: #6c757d;
  }

  :global(.text-danger) {
    color: #dc3545;
  }

  :global(.text-success) {
    color: #28a745;
  }

  :global(.mb-0) { margin-bottom: 0; }
  :global(.mb-1) { margin-bottom: 0.5rem; }
  :global(.mb-2) { margin-bottom: 1rem; }
  :global(.mb-3) { margin-bottom: 1.5rem; }

  :global(.mt-0) { margin-top: 0; }
  :global(.mt-1) { margin-top: 0.5rem; }
  :global(.mt-2) { margin-top: 1rem; }
  :global(.mt-3) { margin-top: 1.5rem; }

  :global(.d-flex) { display: flex; }
  :global(.align-items-center) { align-items: center; }
  :global(.justify-content-between) { justify-content: space-between; }
  :global(.gap-1) { gap: 0.5rem; }
  :global(.gap-2) { gap: 1rem; }
</style>
