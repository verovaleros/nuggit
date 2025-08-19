<script>
  import Router from 'svelte-spa-router';
  import routes from './routes/routes.js';
  import ErrorBoundary from './components/ErrorBoundary.svelte';

  // Global error handler for the app
  function handleAppError(event) {
    console.error('App-level error:', event.detail);
    // Could send to error reporting service here
  }

  function handleRetry() {
    // Force page reload on retry
    window.location.reload();
  }
</script>

<ErrorBoundary on:error={handleAppError} on:retry={handleRetry}>
  <Router {routes} />
</ErrorBoundary>
