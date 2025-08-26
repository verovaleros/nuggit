<!--
  User Settings Component for Nuggit Frontend
  
  Provides user settings management including password change,
  account preferences, and security settings.
-->

<script>
  import { onMount } from 'svelte';
  import { authStore } from '../lib/stores/authStore.js';
  import { apiClient, ApiError } from '../lib/api/apiClient.js';

  // Auth state
  $: authState = $authStore;
  $: currentUser = authState.user;

  // Redirect if not authenticated
  $: if (authState.isInitialized && !authState.isAuthenticated) {
    import('svelte-spa-router').then(({ push }) => {
      sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
      push('/login');
    });
  }

  // Component state
  let loading = false;
  let error = null;
  let success = null;
  let activeSection = 'password';

  // Password change form
  let passwordForm = {
    current_password: '',
    new_password: '',
    confirm_password: ''
  };
  let passwordLoading = false;
  let passwordError = null;
  let passwordSuccess = null;
  let showPasswords = false;

  function switchSection(section) {
    activeSection = section;
    clearMessages();
  }

  function clearMessages() {
    error = null;
    success = null;
    passwordError = null;
    passwordSuccess = null;
  }

  function resetPasswordForm() {
    passwordForm = {
      current_password: '',
      new_password: '',
      confirm_password: ''
    };
    showPasswords = false;
  }

  async function changePassword() {
    try {
      passwordLoading = true;
      passwordError = null;
      passwordSuccess = null;

      // Validate form
      if (!passwordForm.current_password) {
        passwordError = 'Current password is required';
        return;
      }

      if (!passwordForm.new_password) {
        passwordError = 'New password is required';
        return;
      }

      if (passwordForm.new_password.length < 8) {
        passwordError = 'New password must be at least 8 characters long';
        return;
      }

      if (passwordForm.new_password !== passwordForm.confirm_password) {
        passwordError = 'New passwords do not match';
        return;
      }

      if (passwordForm.current_password === passwordForm.new_password) {
        passwordError = 'New password must be different from current password';
        return;
      }

      // Change password
      const response = await apiClient.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      });

      passwordSuccess = response.message || 'Password changed successfully!';
      resetPasswordForm();

      // Clear success message after 5 seconds
      setTimeout(() => {
        passwordSuccess = null;
      }, 5000);

    } catch (err) {
      console.error('Error changing password:', err);
      if (err instanceof ApiError) {
        passwordError = err.message;
      } else {
        passwordError = 'Failed to change password';
      }
    } finally {
      passwordLoading = false;
    }
  }

  function togglePasswordVisibility() {
    showPasswords = !showPasswords;
  }

  function getPasswordStrength(password) {
    if (!password) return { strength: 0, label: '', color: '#ddd' };
    
    let score = 0;
    
    // Length
    if (password.length >= 8) score += 1;
    if (password.length >= 12) score += 1;
    
    // Character types
    if (/[a-z]/.test(password)) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;
    
    if (score <= 2) return { strength: score, label: 'Weak', color: '#dc3545' };
    if (score <= 4) return { strength: score, label: 'Medium', color: '#ffc107' };
    return { strength: score, label: 'Strong', color: '#28a745' };
  }

  $: passwordStrength = getPasswordStrength(passwordForm.new_password);
</script>

<div class="settings-container">
  <div class="settings-header">
    <h1>⚙️ Settings</h1>
    <p>Manage your account settings and preferences</p>
  </div>

  {#if !authState.isAuthenticated}
    <div class="error">
      <p>Please log in to access settings.</p>
    </div>
  {:else}
    <div class="settings-content">
      <!-- Settings Navigation -->
      <nav class="settings-nav">
        <button 
          class="nav-button" 
          class:active={activeSection === 'password'}
          on:click={() => switchSection('password')}
        >
          🔒 Password
        </button>
        <button 
          class="nav-button" 
          class:active={activeSection === 'security'}
          on:click={() => switchSection('security')}
        >
          🛡️ Security
        </button>
        <button 
          class="nav-button" 
          class:active={activeSection === 'preferences'}
          on:click={() => switchSection('preferences')}
        >
          🎨 Preferences
        </button>
      </nav>

      <!-- Settings Sections -->
      <div class="settings-main">
        {#if activeSection === 'password'}
          <!-- Password Change Section -->
          <div class="settings-section">
            <div class="section-header">
              <h2>Change Password</h2>
              <p>Update your account password to keep your account secure</p>
            </div>

            {#if passwordError}
              <div class="alert alert-error">
                {passwordError}
              </div>
            {/if}

            {#if passwordSuccess}
              <div class="alert alert-success">
                {passwordSuccess}
              </div>
            {/if}

            <form on:submit|preventDefault={changePassword} class="password-form">
              <div class="form-group">
                <label for="current_password">Current Password</label>
                <div class="password-input">
                  {#if showPasswords}
                    <input
                      type="text"
                      id="current_password"
                      bind:value={passwordForm.current_password}
                      placeholder="Enter your current password"
                      disabled={passwordLoading}
                      required
                    />
                  {:else}
                    <input
                      type="password"
                      id="current_password"
                      bind:value={passwordForm.current_password}
                      placeholder="Enter your current password"
                      disabled={passwordLoading}
                      required
                    />
                  {/if}
                </div>
              </div>

              <div class="form-group">
                <label for="new_password">New Password</label>
                <div class="password-input">
                  {#if showPasswords}
                    <input
                      type="text"
                      id="new_password"
                      bind:value={passwordForm.new_password}
                      placeholder="Enter your new password"
                      disabled={passwordLoading}
                      required
                    />
                  {:else}
                    <input
                      type="password"
                      id="new_password"
                      bind:value={passwordForm.new_password}
                      placeholder="Enter your new password"
                      disabled={passwordLoading}
                      required
                    />
                  {/if}
                </div>
                
                {#if passwordForm.new_password}
                  <div class="password-strength">
                    <div class="strength-bar">
                      <div 
                        class="strength-fill" 
                        style="width: {(passwordStrength.strength / 6) * 100}%; background-color: {passwordStrength.color}"
                      ></div>
                    </div>
                    <span class="strength-label" style="color: {passwordStrength.color}">
                      {passwordStrength.label}
                    </span>
                  </div>
                {/if}
              </div>

              <div class="form-group">
                <label for="confirm_password">Confirm New Password</label>
                <div class="password-input">
                  {#if showPasswords}
                    <input
                      type="text"
                      id="confirm_password"
                      bind:value={passwordForm.confirm_password}
                      placeholder="Confirm your new password"
                      disabled={passwordLoading}
                      required
                    />
                  {:else}
                    <input
                      type="password"
                      id="confirm_password"
                      bind:value={passwordForm.confirm_password}
                      placeholder="Confirm your new password"
                      disabled={passwordLoading}
                      required
                    />
                  {/if}
                </div>
              </div>

              <div class="form-group">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    bind:checked={showPasswords}
                  />
                  Show passwords
                </label>
              </div>

              <div class="form-actions">
                <button 
                  type="submit" 
                  class="btn btn-primary"
                  disabled={passwordLoading}
                >
                  {passwordLoading ? 'Changing Password...' : 'Change Password'}
                </button>
                <button 
                  type="button" 
                  class="btn btn-secondary"
                  on:click={resetPasswordForm}
                  disabled={passwordLoading}
                >
                  Reset Form
                </button>
              </div>
            </form>

            <div class="password-tips">
              <h3>Password Requirements</h3>
              <ul>
                <li>At least 8 characters long</li>
                <li>Include uppercase and lowercase letters</li>
                <li>Include at least one number</li>
                <li>Include at least one special character</li>
                <li>Different from your current password</li>
              </ul>
            </div>
          </div>

        {:else if activeSection === 'security'}
          <!-- Security Section -->
          <div class="settings-section">
            <div class="section-header">
              <h2>Security Settings</h2>
              <p>Manage your account security and login preferences</p>
            </div>

            <div class="security-info">
              <div class="info-card">
                <h3>Account Status</h3>
                <div class="status-grid">
                  <div class="status-item">
                    <span class="status-label">Email Verified</span>
                    <span class="status-value {currentUser?.is_verified ? 'verified' : 'unverified'}">
                      {currentUser?.is_verified ? '✅ Verified' : '❌ Not Verified'}
                    </span>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Account Active</span>
                    <span class="status-value {currentUser?.is_active ? 'active' : 'inactive'}">
                      {currentUser?.is_active ? '✅ Active' : '❌ Inactive'}
                    </span>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Admin User</span>
                    <span class="status-value">
                      {currentUser?.is_admin ? '👑 Yes' : '👤 No'}
                    </span>
                  </div>
                </div>
              </div>

              <div class="info-card">
                <h3>Login Information</h3>
                <div class="login-info">
                  <div class="info-item">
                    <span class="info-label">Username</span>
                    <span class="info-value">{currentUser?.username}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Email</span>
                    <span class="info-value">{currentUser?.email}</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Last Login</span>
                    <span class="info-value">
                      {currentUser?.last_login_at ? new Date(currentUser.last_login_at).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

        {:else if activeSection === 'preferences'}
          <!-- Preferences Section -->
          <div class="settings-section">
            <div class="section-header">
              <h2>Preferences</h2>
              <p>Customize your Nuggit experience</p>
            </div>

            <div class="preferences-info">
              <div class="info-card">
                <h3>Coming Soon</h3>
                <p>User preferences and customization options will be available in a future update.</p>
                
                <div class="planned-features">
                  <h4>Planned Features:</h4>
                  <ul>
                    <li>🌙 Dark mode toggle</li>
                    <li>📧 Email notification preferences</li>
                    <li>🏷️ Default repository tags</li>
                    <li>📊 Dashboard layout preferences</li>
                    <li>🔔 Activity notifications</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .settings-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }

  .settings-header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .settings-header h1 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 2.5rem;
  }

  .settings-header p {
    margin: 0;
    color: #666;
    font-size: 1.1rem;
  }

  .error {
    text-align: center;
    padding: 2rem;
    color: #dc3545;
  }

  .settings-content {
    display: grid;
    grid-template-columns: 250px 1fr;
    gap: 2rem;
  }

  .settings-nav {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .nav-button {
    padding: 1rem;
    border: none;
    background: white;
    border-radius: 8px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 1rem;
    color: #666;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .nav-button:hover {
    background: #f8f9fa;
    transform: translateY(-1px);
  }

  .nav-button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .settings-main {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
  }

  .settings-section {
    max-width: 600px;
  }

  .section-header {
    margin-bottom: 2rem;
  }

  .section-header h2 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 1.8rem;
  }

  .section-header p {
    margin: 0;
    color: #666;
    font-size: 1rem;
  }

  .alert {
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
  }

  .alert-error {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
  }

  .alert-success {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
  }

  .password-form {
    margin-bottom: 2rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #333;
  }

  .password-input {
    position: relative;
  }

  .form-group input[type="text"],
  .form-group input[type="password"] {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.2s ease;
  }

  .form-group input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  }

  .form-group input:disabled {
    background: #f8f9fa;
    cursor: not-allowed;
  }

  .password-strength {
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .strength-bar {
    flex: 1;
    height: 4px;
    background: #e1e5e9;
    border-radius: 2px;
    overflow: hidden;
  }

  .strength-fill {
    height: 100%;
    transition: all 0.3s ease;
  }

  .strength-label {
    font-size: 0.9rem;
    font-weight: 500;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-weight: normal !important;
  }

  .checkbox-label input[type="checkbox"] {
    width: auto;
  }

  .form-actions {
    display: flex;
    gap: 1rem;
    margin-top: 2rem;
  }

  .password-tips {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1.5rem;
    margin-top: 2rem;
  }

  .password-tips h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.2rem;
  }

  .password-tips ul {
    margin: 0;
    padding-left: 1.5rem;
    color: #666;
  }

  .password-tips li {
    margin-bottom: 0.5rem;
  }

  .security-info,
  .preferences-info {
    display: grid;
    gap: 2rem;
  }

  .info-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1.5rem;
  }

  .info-card h3 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.3rem;
  }

  .status-grid {
    display: grid;
    gap: 1rem;
  }

  .status-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #e1e5e9;
  }

  .status-item:last-child {
    border-bottom: none;
  }

  .status-label {
    font-weight: 600;
    color: #555;
  }

  .status-value {
    font-weight: 500;
  }

  .status-value.verified,
  .status-value.active {
    color: #28a745;
  }

  .status-value.unverified,
  .status-value.inactive {
    color: #dc3545;
  }

  .login-info {
    display: grid;
    gap: 1rem;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #e1e5e9;
  }

  .info-item:last-child {
    border-bottom: none;
  }

  .info-label {
    font-weight: 600;
    color: #555;
  }

  .info-value {
    color: #333;
    font-family: monospace;
    font-size: 0.9rem;
  }

  .planned-features {
    margin-top: 1.5rem;
  }

  .planned-features h4 {
    margin: 0 0 1rem 0;
    color: #333;
    font-size: 1.1rem;
  }

  .planned-features ul {
    margin: 0;
    padding-left: 1.5rem;
    color: #666;
  }

  .planned-features li {
    margin-bottom: 0.5rem;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .btn-secondary {
    background: #6c757d;
    color: white;
  }

  .btn-secondary:hover:not(:disabled) {
    background: #5a6268;
    transform: translateY(-1px);
  }

  /* Responsive design */
  @media (max-width: 768px) {
    .settings-container {
      padding: 1rem;
    }

    .settings-content {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .settings-nav {
      flex-direction: row;
      overflow-x: auto;
      gap: 0.5rem;
      padding-bottom: 0.5rem;
    }

    .nav-button {
      white-space: nowrap;
      min-width: 120px;
    }

    .form-actions {
      flex-direction: column;
    }

    .password-strength {
      flex-direction: column;
      align-items: stretch;
      gap: 0.5rem;
    }
  }
</style>
