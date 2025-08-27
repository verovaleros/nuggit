<script>
  import { onMount, onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';

  export let fallback = null;
  export let showDetails = false;
  
  let hasError = false;
  let error = null;
  let errorInfo = null;
  let errorId = null;

  const dispatch = createEventDispatcher();

  // Generate unique error ID for tracking
  function generateErrorId() {
    return 'err_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  // Global error handler for unhandled promise rejections
  function handleUnhandledRejection(event) {
    console.error('Unhandled promise rejection:', event.reason);
    captureError(event.reason, 'Unhandled Promise Rejection');
    event.preventDefault(); // Prevent default browser behavior
  }

  // Global error handler for JavaScript errors
  function handleGlobalError(event) {
    console.error('Global JavaScript error:', event.error);
    captureError(event.error, 'JavaScript Error');
  }

  // Capture and process errors
  function captureError(err, source = 'Component Error') {
    errorId = generateErrorId();
    error = err;
    errorInfo = {
      source,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      stack: err?.stack || 'No stack trace available'
    };
    hasError = true;

    // Log error details
    console.group(`🚨 Error Boundary - ${errorId}`);
    console.error('Error:', err);
    console.error('Source:', source);
    console.error('Info:', errorInfo);
    console.groupEnd();

    // Dispatch error event for parent components
    dispatch('error', {
      error: err,
      errorInfo,
      errorId
    });
  }

  // Reset error state
  function resetError() {
    hasError = false;
    error = null;
    errorInfo = null;
    errorId = null;
  }

  // Retry function
  function retry() {
    resetError();
    // Force component re-render by dispatching retry event
    dispatch('retry');
  }

  onMount(() => {
    // Add global error listeners
    window.addEventListener('error', handleGlobalError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);
  });

  onDestroy(() => {
    // Clean up global error listeners
    window.removeEventListener('error', handleGlobalError);
    window.removeEventListener('unhandledrejection', handleUnhandledRejection);
  });

  // Export function to manually trigger error capture
  export function captureManualError(err, source = 'Manual Error') {
    captureError(err, source);
  }
</script>

{#if hasError}
  {#if fallback}
    <svelte:component this={fallback} {error} {errorInfo} {errorId} {retry} {resetError} />
  {:else}
    <div class="error-boundary">
      <div class="error-container">
        <div class="error-header">
          <h2>🚨 Something went wrong</h2>
          <p class="error-id">Error ID: {errorId}</p>
        </div>
        
        <div class="error-message">
          <p><strong>Error:</strong> {error?.message || 'An unexpected error occurred'}</p>
          {#if errorInfo?.source}
            <p><strong>Source:</strong> {errorInfo.source}</p>
          {/if}
        </div>

        <div class="error-actions">
          <button class="retry-button" on:click={retry}>
            🔄 Try Again
          </button>
          <button class="details-button" on:click={() => showDetails = !showDetails}>
            {showDetails ? '📄 Hide Details' : '🔍 Show Details'}
          </button>
        </div>

        {#if showDetails && errorInfo}
          <div class="error-details">
            <h3>Error Details</h3>
            <div class="detail-item">
              <strong>Timestamp:</strong> {errorInfo.timestamp}
            </div>
            <div class="detail-item">
              <strong>URL:</strong> {errorInfo.url}
            </div>
            {#if error?.stack}
              <div class="detail-item">
                <strong>Stack Trace:</strong>
                <pre class="stack-trace">{error.stack}</pre>
              </div>
            {/if}
          </div>
        {/if}

        <div class="error-help">
          <p>If this error persists, please:</p>
          <ul>
            <li>Refresh the page</li>
            <li>Clear your browser cache</li>
            <li>Report this error with ID: <code>{errorId}</code></li>
          </ul>
        </div>
      </div>
    </div>
  {/if}
{:else}
  <slot />
{/if}

<style>
  .error-boundary {
    min-height: 400px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    margin: 1rem;
  }

  .error-container {
    max-width: 600px;
    width: 100%;
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .error-header h2 {
    color: #dc2626;
    margin: 0 0 0.5rem 0;
    font-size: 1.5rem;
  }

  .error-id {
    color: #6b7280;
    font-size: 0.875rem;
    margin: 0 0 1rem 0;
    font-family: monospace;
  }

  .error-message {
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1.5rem;
  }

  .error-message p {
    margin: 0.5rem 0;
    color: #991b1b;
  }

  .error-actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .retry-button, .details-button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s;
  }

  .retry-button {
    background-color: #3b82f6;
    color: white;
  }

  .retry-button:hover {
    background-color: #2563eb;
  }

  .details-button {
    background-color: #6b7280;
    color: white;
  }

  .details-button:hover {
    background-color: #4b5563;
  }

  .error-details {
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1.5rem;
  }

  .error-details h3 {
    margin: 0 0 1rem 0;
    color: #374151;
    font-size: 1.125rem;
  }

  .detail-item {
    margin-bottom: 0.75rem;
    color: #4b5563;
  }

  .detail-item strong {
    color: #374151;
  }

  .stack-trace {
    background-color: #1f2937;
    color: #f9fafb;
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 0.75rem;
    overflow-x: auto;
    white-space: pre-wrap;
    margin-top: 0.5rem;
  }

  .error-help {
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 4px;
    padding: 1rem;
  }

  .error-help p {
    margin: 0 0 0.5rem 0;
    color: #1e40af;
    font-weight: 500;
  }

  .error-help ul {
    margin: 0;
    padding-left: 1.5rem;
    color: #1e40af;
  }

  .error-help li {
    margin-bottom: 0.25rem;
  }

  .error-help code {
    background-color: #dbeafe;
    padding: 0.125rem 0.25rem;
    border-radius: 2px;
    font-family: monospace;
    font-size: 0.875rem;
  }
</style>
