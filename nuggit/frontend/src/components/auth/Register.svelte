<!--
  Register Component for Nuggit Frontend
  
  Provides user registration with email, username, password fields,
  client-side validation, password confirmation, and email verification
  flow initiation.
-->

<script>
  import { authStore } from '../../lib/stores/authStore.js';
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';

  // Form data
  let email = '';
  let username = '';
  let firstName = '';
  let lastName = '';
  let password = '';
  let confirmPassword = '';
  
  // Component state
  let isLoading = false;
  let errors = {};
  let showPassword = false;
  let showConfirmPassword = false;
  let registrationSuccess = false;
  
  // Auth store state
  $: authState = $authStore;
  $: if (authState.isAuthenticated) {
    // Redirect to home if already authenticated
    push('/home');
  }

  /**
   * Validate email format
   */
  function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * Validate username format
   */
  function isValidUsername(username) {
    const usernameRegex = /^[a-zA-Z0-9_-]{3,20}$/;
    return usernameRegex.test(username);
  }

  /**
   * Validate password strength
   */
  function isValidPassword(password) {
    // At least 8 characters, one uppercase, one lowercase, one number
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/;
    return passwordRegex.test(password);
  }

  /**
   * Validate form inputs
   */
  function validateForm() {
    errors = {};
    
    // Email validation
    if (!email.trim()) {
      errors.email = 'Email is required';
    } else if (!isValidEmail(email.trim())) {
      errors.email = 'Please enter a valid email address';
    }
    
    // Username validation
    if (!username.trim()) {
      errors.username = 'Username is required';
    } else if (!isValidUsername(username.trim())) {
      errors.username = 'Username must be 3-20 characters, letters, numbers, _ or - only';
    }
    
    // First name validation
    if (!firstName.trim()) {
      errors.firstName = 'First name is required';
    } else if (firstName.trim().length < 2) {
      errors.firstName = 'First name must be at least 2 characters';
    }
    
    // Last name validation
    if (!lastName.trim()) {
      errors.lastName = 'Last name is required';
    } else if (lastName.trim().length < 2) {
      errors.lastName = 'Last name must be at least 2 characters';
    }
    
    // Password validation
    if (!password) {
      errors.password = 'Password is required';
    } else if (!isValidPassword(password)) {
      errors.password = 'Password must be at least 8 characters with uppercase, lowercase, and number';
    }
    
    // Confirm password validation
    if (!confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
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
      const result = await authStore.register({
        email: email.trim(),
        username: username.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        password: password
      });

      if (result.success) {
        registrationSuccess = true;
        // Clear form
        email = '';
        username = '';
        firstName = '';
        lastName = '';
        password = '';
        confirmPassword = '';
      } else {
        // Display error from auth store
        errors.general = result.error;
      }
    } catch (error) {
      console.error('Registration error:', error);
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

  /**
   * Toggle confirm password visibility
   */
  function toggleConfirmPasswordVisibility() {
    showConfirmPassword = !showConfirmPassword;
  }

  /**
   * Navigate to login
   */
  function goToLogin() {
    push('/login');
  }

  // Clear auth store error on component mount
  onMount(() => {
    authStore.clearError();
  });
</script>

<div class="register-container">
  <div class="register-card">
    {#if registrationSuccess}
      <!-- Success Message -->
      <div class="success-message">
        <div class="success-icon">✅</div>
        <h2>Registration Successful!</h2>
        <p>
          We've sent a verification email to <strong>{email}</strong>.
          Please check your inbox and click the verification link to activate your account.
        </p>
        <div class="success-actions">
          <button class="login-button" on:click={goToLogin}>
            Go to Login
          </button>
          <p class="resend-info">
            Didn't receive the email? Check your spam folder or 
            <a href="#/resend-verification" class="resend-link">resend verification email</a>
          </p>
        </div>
      </div>
    {:else}
      <!-- Registration Form -->
      <div class="register-header">
        <h1>🧠 Join Nuggit</h1>
        <p>Create your account to start managing repositories</p>
      </div>

      <form on:submit|preventDefault={handleSubmit} class="register-form">
        <!-- Email Field -->
        <div class="form-group">
          <label for="email">Email Address</label>
          <input
            id="email"
            type="email"
            bind:value={email}
            on:input={() => clearFieldError('email')}
            on:keypress={handleKeyPress}
            placeholder="Enter your email address"
            class:error={errors.email}
            disabled={isLoading}
            autocomplete="email"
          />
          {#if errors.email}
            <span class="error-message">{errors.email}</span>
          {/if}
        </div>

        <!-- Username Field -->
        <div class="form-group">
          <label for="username">Username</label>
          <input
            id="username"
            type="text"
            bind:value={username}
            on:input={() => clearFieldError('username')}
            on:keypress={handleKeyPress}
            placeholder="Choose a username"
            class:error={errors.username}
            disabled={isLoading}
            autocomplete="username"
          />
          {#if errors.username}
            <span class="error-message">{errors.username}</span>
          {/if}
        </div>

        <!-- Name Fields -->
        <div class="form-row">
          <div class="form-group">
            <label for="firstName">First Name</label>
            <input
              id="firstName"
              type="text"
              bind:value={firstName}
              on:input={() => clearFieldError('firstName')}
              on:keypress={handleKeyPress}
              placeholder="First name"
              class:error={errors.firstName}
              disabled={isLoading}
              autocomplete="given-name"
            />
            {#if errors.firstName}
              <span class="error-message">{errors.firstName}</span>
            {/if}
          </div>

          <div class="form-group">
            <label for="lastName">Last Name</label>
            <input
              id="lastName"
              type="text"
              bind:value={lastName}
              on:input={() => clearFieldError('lastName')}
              on:keypress={handleKeyPress}
              placeholder="Last name"
              class:error={errors.lastName}
              disabled={isLoading}
              autocomplete="family-name"
            />
            {#if errors.lastName}
              <span class="error-message">{errors.lastName}</span>
            {/if}
          </div>
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
                placeholder="Create a strong password"
                class:error={errors.password}
                disabled={isLoading}
                autocomplete="new-password"
              />
            {:else}
              <input
                id="password"
                type="password"
                bind:value={password}
                on:input={() => clearFieldError('password')}
                on:keypress={handleKeyPress}
                placeholder="Create a strong password"
                class:error={errors.password}
                disabled={isLoading}
                autocomplete="new-password"
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

        <!-- Confirm Password Field -->
        <div class="form-group">
          <label for="confirmPassword">Confirm Password</label>
          <div class="password-input-container">
            {#if showConfirmPassword}
              <input
                id="confirmPassword"
                type="text"
                bind:value={confirmPassword}
                on:input={() => clearFieldError('confirmPassword')}
                on:keypress={handleKeyPress}
                placeholder="Confirm your password"
                class:error={errors.confirmPassword}
                disabled={isLoading}
                autocomplete="new-password"
              />
            {:else}
              <input
                id="confirmPassword"
                type="password"
                bind:value={confirmPassword}
                on:input={() => clearFieldError('confirmPassword')}
                on:keypress={handleKeyPress}
                placeholder="Confirm your password"
                class:error={errors.confirmPassword}
                disabled={isLoading}
                autocomplete="new-password"
              />
            {/if}
            <button
              type="button"
              class="password-toggle"
              on:click={toggleConfirmPasswordVisibility}
              disabled={isLoading}
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
            >
              {showConfirmPassword ? '👁️' : '👁️‍🗨️'}
            </button>
          </div>
          {#if errors.confirmPassword}
            <span class="error-message">{errors.confirmPassword}</span>
          {/if}
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
          class="register-button"
          disabled={isLoading || !email.trim() || !username.trim() || !firstName.trim() || !lastName.trim() || !password || !confirmPassword}
        >
          {#if isLoading}
            <span class="loading-spinner"></span>
            Creating Account...
          {:else}
            Create Account
          {/if}
        </button>
      </form>

      <div class="register-footer">
        <p>
          Already have an account?
          <a href="#/login" class="login-link">Sign in here</a>
        </p>
      </div>
    {/if}
  </div>
</div>

<style>
  .register-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  .register-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    padding: 2rem;
    width: 100%;
    max-width: 500px;
  }

  .register-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .register-header h1 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .register-header p {
    margin: 0;
    color: #666;
    font-size: 0.9rem;
  }

  .register-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .form-group label {
    font-weight: 600;
    color: #333;
    font-size: 0.9rem;
  }

  .form-group input[type="text"],
  .form-group input[type="email"],
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

  .register-button {
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

  .register-button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .register-button:disabled {
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

  .register-footer {
    text-align: center;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #e1e5e9;
  }

  .register-footer p {
    margin: 0;
    font-size: 0.9rem;
    color: #666;
  }

  .login-link {
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
  }

  .login-link:hover {
    text-decoration: underline;
  }

  /* Success Message Styles */
  .success-message {
    text-align: center;
    padding: 2rem 0;
  }

  .success-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
  }

  .success-message h2 {
    color: #22c55e;
    margin: 0 0 1rem 0;
    font-size: 1.5rem;
  }

  .success-message p {
    color: #666;
    line-height: 1.6;
    margin-bottom: 2rem;
  }

  .success-actions {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    align-items: center;
  }

  .login-button {
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
    color: white;
    border: none;
    padding: 0.875rem 2rem;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .login-button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
  }

  .resend-info {
    font-size: 0.8rem;
    color: #666;
    margin: 0;
  }

  .resend-link {
    color: #667eea;
    text-decoration: none;
    font-weight: 600;
  }

  .resend-link:hover {
    text-decoration: underline;
  }

  /* Responsive design */
  @media (max-width: 600px) {
    .register-container {
      padding: 0.5rem;
    }

    .register-card {
      padding: 1.5rem;
    }

    .register-header h1 {
      font-size: 1.5rem;
    }

    .form-row {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
  }
</style>
