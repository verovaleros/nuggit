<!--
  Email Verification Component for Nuggit Frontend
  
  Handles email verification when users click the verification link
  from their email. Extracts the token from URL parameters and
  calls the verification API endpoint.
-->

<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { apiClient, ApiError } from '../../lib/api/apiClient.js';

  // Component state
  let loading = true;
  let success = false;
  let error = null;
  let message = '';

  /**
   * Extract token from URL parameters and verify email
   */
  onMount(async () => {
    try {
      // Get token from URL parameters - try both query params and hash params
      let token = null;

      // First try standard query parameters (e.g., /verify-email?token=abc123)
      const searchParams = new URLSearchParams(window.location.search);
      token = searchParams.get('token');

      // Fallback to hash-based parameters (e.g., /#/verify-email?token=abc123)
      if (!token && window.location.hash.includes('?')) {
        const hashParams = new URLSearchParams(window.location.hash.split('?')[1]);
        token = hashParams.get('token');
      }

      if (!token) {
        throw new Error('Verification token not found in URL. Please check that you clicked the correct link from your email.');
      }

      // Validate token format (basic check)
      if (token.length < 10) {
        throw new Error('Invalid verification token format. Please use the link from your email.');
      }

      console.log('Verifying email with token:', token.substring(0, 8) + '...');

      // Call verification API
      const response = await apiClient.post('/auth/verify-email', {
        token: token
      });

      if (response.success) {
        success = true;
        message = response.message || 'Email verified successfully! You can now log in.';
        
        // Redirect to login page after 3 seconds
        setTimeout(() => {
          push('/login');
        }, 3000);
      } else {
        throw new Error(response.message || 'Email verification failed');
      }

    } catch (err) {
      console.error('Email verification error:', err);

      if (err instanceof ApiError) {
        // Handle specific API errors
        if (err.status === 400) {
          error = 'Invalid or expired verification token. Please request a new verification email.';
        } else if (err.status === 404) {
          error = 'Verification token not found. The link may have expired or already been used.';
        } else if (err.status >= 500) {
          error = 'Server error occurred. Please try again later or contact support.';
        } else {
          error = err.message || 'Email verification failed. Please try again.';
        }
      } else {
        // Handle client-side errors (token parsing, network issues, etc.)
        if (err.message.includes('token not found')) {
          error = 'No verification token found in the URL. Please make sure you clicked the correct link from your email.';
        } else if (err.message.includes('Invalid verification token format')) {
          error = err.message;
        } else if (err.name === 'TypeError' || err.message.includes('fetch')) {
          error = 'Network error. Please check your internet connection and try again.';
        } else {
          error = err.message || 'An unexpected error occurred during email verification. Please try again.';
        }
      }
    } finally {
      loading = false;
    }
  });

  /**
   * Redirect to login page
   */
  function goToLogin() {
    push('/login');
  }

  /**
   * Redirect to registration page
   */
  function goToRegister() {
    push('/register');
  }
</script>

<div class="verify-email-container">
  <div class="verify-email-card">
    <div class="verify-email-header">
      <h1>Email Verification</h1>
    </div>

    <div class="verify-email-content">
      {#if loading}
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Verifying your email address...</p>
        </div>
      {:else if success}
        <div class="success-state">
          <div class="success-icon">✅</div>
          <h2>Email Verified Successfully!</h2>
          <p class="success-message">{message}</p>
          <p class="redirect-info">You will be redirected to the login page in a few seconds.</p>
          
          <div class="action-buttons">
            <button class="btn btn-primary" on:click={goToLogin}>
              Go to Login Now
            </button>
          </div>
        </div>
      {:else if error}
        <div class="error-state">
          <div class="error-icon">❌</div>
          <h2>Email Verification Failed</h2>
          <p class="error-message">{error}</p>
          
          <div class="help-text">
            <p>This could happen if:</p>
            <ul>
              <li>The verification link has expired (links expire after 24 hours)</li>
              <li>The verification link has already been used</li>
              <li>The verification link is invalid or incomplete</li>
              <li>You didn't click the link directly from your email</li>
              <li>There was a network error during verification</li>
            </ul>
            <p><strong>What to do:</strong></p>
            <ul>
              <li>Try clicking the verification link in your email again</li>
              <li>Check your spam/junk folder for the verification email</li>
              <li>If the link has expired, register again to get a new verification email</li>
            </ul>
          </div>
          
          <div class="action-buttons">
            <button class="btn btn-secondary" on:click={goToRegister}>
              Register Again
            </button>
            <button class="btn btn-primary" on:click={goToLogin}>
              Try to Login
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .verify-email-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
  }

  .verify-email-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    max-width: 500px;
    width: 100%;
    overflow: hidden;
  }

  .verify-email-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    text-align: center;
  }

  .verify-email-header h1 {
    margin: 0;
    font-size: 1.8rem;
    font-weight: 600;
  }

  .verify-email-content {
    padding: 40px 30px;
    text-align: center;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .success-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
  }

  .success-icon,
  .error-icon {
    font-size: 4rem;
    margin-bottom: 10px;
  }

  .success-state h2 {
    color: #28a745;
    margin: 0;
    font-size: 1.5rem;
  }

  .error-state h2 {
    color: #dc3545;
    margin: 0;
    font-size: 1.5rem;
  }

  .success-message,
  .error-message {
    color: #666;
    font-size: 1.1rem;
    line-height: 1.5;
    margin: 0;
  }

  .redirect-info {
    color: #888;
    font-size: 0.9rem;
    margin: 10px 0;
  }

  .help-text {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    text-align: left;
  }

  .help-text p {
    margin: 0 0 10px 0;
    font-weight: 600;
    color: #495057;
  }

  .help-text ul {
    margin: 0;
    padding-left: 20px;
    color: #6c757d;
  }

  .help-text li {
    margin-bottom: 5px;
  }

  .action-buttons {
    display: flex;
    gap: 15px;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 30px;
  }

  .btn {
    padding: 12px 24px;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    display: inline-block;
    min-width: 120px;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
  }

  .btn-secondary {
    background: #6c757d;
    color: white;
  }

  .btn-secondary:hover {
    background: #5a6268;
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(108, 117, 125, 0.4);
  }

  @media (max-width: 480px) {
    .verify-email-container {
      padding: 10px;
    }
    
    .verify-email-content {
      padding: 30px 20px;
    }
    
    .action-buttons {
      flex-direction: column;
    }
    
    .btn {
      width: 100%;
    }
  }
</style>
