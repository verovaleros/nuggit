<!--
  Login Component for Nuggit Frontend
  
  Provides user authentication with email/username and password.
  Includes form validation, loading states, error handling,
  and remember me functionality.
-->

<script>
  import { authStore } from '../../lib/stores/authStore.js';
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';

  // Form data
  let emailOrUsername = '';
  let password = '';
  let rememberMe = false;
  
  // Component state
  let isLoading = false;
  let errors = {};
  let showPassword = false;
  
  // Auth store state
  $: authState = $authStore;
  $: if (authState.isAuthenticated) {
    // Redirect to home if already authenticated
    push('/home');
  }

  /**
   * Validate form inputs
   */
  function validateForm() {
    errors = {};
    
    if (!emailOrUsername.trim()) {
      errors.emailOrUsername = 'Email or username is required';
    }
    
    if (!password) {
      errors.password = 'Password is required';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    }
    
    return Object.keys(errors).length === 0;
  }

  /**
   * Handle form submission
   */
  async function handleSubmit() {
    if (!validateForm()) {
      return;
    }

    isLoading = true;
    errors = {};

    try {
      const result = await authStore.login({
        email_or_username: emailOrUsername.trim(),
        password: password,
        remember_me: rememberMe
      });

      if (result.success) {
        // Redirect to home page on successful login
        push('/home');
      } else {
        // Display error from auth store
        errors.general = result.error;
      }
    } catch (error) {
      console.error('Login error:', error);
      errors.general = 'An unexpected error occurred. Please try again.';
    } finally {
      isLoading = false;
    }
  }

  /**
   * Handle Enter key press
   */
  function handleKeyPress(event) {
    if (event.key === 'Enter') {
      handleSubmit();
    }
  }

  /**
   * Clear specific field error
   */
  function clearFieldError(field) {
    if (errors[field]) {
      errors = { ...errors };
      delete errors[field];
    }
  }

  /**
   * Toggle password visibility
   */
  function togglePasswordVisibility() {
    showPassword = !showPassword;
  }

  // Clear auth store error on component mount
  onMount(() => {
    authStore.clearError();
  });
</script>

<div class="login-container">
  <div class="login-card">
    <div class="login-header">
      <h1>🧠 Welcome to Nuggit</h1>
      <p>Sign in to your account</p>
    </div>

    <form on:submit|preventDefault={handleSubmit} class="login-form">
      <!-- Email/Username Field -->
      <div class="form-group">
        <label for="emailOrUsername">Email or Username</label>
        <input
          id="emailOrUsername"
          type="text"
          bind:value={emailOrUsername}
          on:input={() => clearFieldError('emailOrUsername')}
          on:keypress={handleKeyPress}
          placeholder="Enter your email or username"
          class:error={errors.emailOrUsername}
          disabled={isLoading}
          autocomplete="username"
        />
        {#if errors.emailOrUsername}
          <span class="error-message">{errors.emailOrUsername}</span>
        {/if}
      </div>

      <!-- Password Field -->
      <div class="form-group">
        <label for="password">Password</label>
        <div class="password-input-container">
          {#if showPassword}
            <input
              id="password"
              type="text"
              bind:value={password}
              on:input={() => clearFieldError('password')}
              on:keypress={handleKeyPress}
              placeholder="Enter your password"
              class:error={errors.password}
              disabled={isLoading}
              autocomplete="current-password"
            />
          {:else}
            <input
              id="password"
              type="password"
              bind:value={password}
              on:input={() => clearFieldError('password')}
              on:keypress={handleKeyPress}
              placeholder="Enter your password"
              class:error={errors.password}
              disabled={isLoading}
              autocomplete="current-password"
            />
          {/if}
          <button
            type="button"
            class="password-toggle"
            on:click={togglePasswordVisibility}
            disabled={isLoading}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? '👁️' : '👁️‍🗨️'}
          </button>
        </div>
        {#if errors.password}
          <span class="error-message">{errors.password}</span>
        {/if}
      </div>

      <!-- Remember Me -->
      <div class="form-group checkbox-group">
        <label class="checkbox-label">
          <input
            type="checkbox"
            bind:checked={rememberMe}
            disabled={isLoading}
          />
          <span class="checkbox-text">Remember me for 24 hours</span>
        </label>
      </div>

      <!-- General Error -->
      {#if errors.general || authState.error}
        <div class="error-banner">
          {errors.general || authState.error}
        </div>
      {/if}

      <!-- Submit Button -->
      <button
        type="submit"
        class="login-button"
        disabled={isLoading || !emailOrUsername.trim() || !password}
      >
        {#if isLoading}
          <span class="loading-spinner"></span>
          Signing in...
        {:else}
          Sign In
        {/if}
      </button>
    </form>

    <div class="login-footer">
      <p>
        Don't have an account?
        <a href="#/register" class="register-link">Sign up here</a>
      </p>
      <p>
        <a href="#/forgot-password" class="forgot-password-link">Forgot your password?</a>
      </p>
    </div>
  </div>
</div>

<style>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .login-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    width: 100%;
    max-width: 400px;
  }

  .login-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .login-header h1 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .login-header p {
    margin: 0;
    color: #666;
    font-size: 0.9rem;
  }

  .login-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-group label {
    font-weight: 600;
    color: #333;
    font-size: 0.9rem;
  }

  .form-group input[type="text"],
  .form-group input[type="password"] {
    padding: 0.75rem;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.2s ease;
  }

  .form-group input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .form-group input.error {
    border-color: #e74c3c;
  }

  .password-input-container {
    position: relative;
    display: flex;
    align-items: center;
  }

  .password-input-container input {
    flex: 1;
    padding-right: 3rem;
  }

  .password-toggle {
    position: absolute;
    right: 0.75rem;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.2rem;
    padding: 0.25rem;
    border-radius: 4px;
    transition: background-color 0.2s ease;
  }

  .password-toggle:hover {
    background-color: #f8f9fa;
  }

  .password-toggle:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .checkbox-group {
    flex-direction: row;
    align-items: center;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .checkbox-label input[type="checkbox"] {
    margin: 0;
  }

  .checkbox-text {
    color: #666;
  }

  .error-message {
    color: #e74c3c;
    font-size: 0.8rem;
    margin-top: 0.25rem;
  }

  .error-banner {
    background-color: #fdf2f2;
    border: 1px solid #fca5a5;
    color: #dc2626;
    padding: 0.75rem;
    border-radius: 8px;
    font-size: 0.9rem;
    text-align: center;
  }

  .login-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 0.875rem;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .login-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .login-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .loading-spinner {
    width: 1rem;
    height: 1rem;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .login-footer {
    text-align: center;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e1e5e9;
  }

  .login-footer p {
    margin: 0.5rem 0;
    font-size: 0.9rem;
    color: #666;
  }

  .register-link,
  .forgot-password-link {
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
  }

  .register-link:hover,
  .forgot-password-link:hover {
    text-decoration: underline;
  }

  /* Responsive design */
  @media (max-width: 480px) {
    .login-container {
      padding: 0.5rem;
    }

    .login-card {
      padding: 1.5rem;
    }

    .login-header h1 {
      font-size: 1.5rem;
    }
  }
</style>
