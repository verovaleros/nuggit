<!--
  User Profile Component for Nuggit Frontend
  
  Displays and allows editing of user profile information including
  personal details and account statistics.
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
  let loading = true;
  let saving = false;
  let error = null;
  let success = null;
  let profile = null;
  let repositories = [];
  let isEditing = false;

  // Form data
  let formData = {
    first_name: '',
    last_name: ''
  };

  onMount(async () => {
    if (!authState.isAuthenticated) {
      loading = false;
      return;
    }

    await loadProfile();
    await loadUserRepositories();
  });

  async function loadProfile() {
    try {
      loading = true;
      error = null;
      
      profile = await apiClient.getUserProfile();
      
      // Initialize form data
      formData = {
        first_name: profile.first_name || '',
        last_name: profile.last_name || ''
      };
      
    } catch (err) {
      console.error('Error loading profile:', err);
      error = 'Failed to load profile information';
    } finally {
      loading = false;
    }
  }

  async function loadUserRepositories() {
    try {
      const response = await apiClient.getRepositories();
      repositories = response.repositories || [];
    } catch (err) {
      console.error('Error loading repositories:', err);
      // Don't show error for repositories as it's not critical
    }
  }

  function startEditing() {
    isEditing = true;
    error = null;
    success = null;
  }

  function cancelEditing() {
    isEditing = false;
    // Reset form data
    formData = {
      first_name: profile.first_name || '',
      last_name: profile.last_name || ''
    };
    error = null;
    success = null;
  }

  async function saveProfile() {
    try {
      saving = true;
      error = null;
      success = null;

      // Validate form
      if (!formData.first_name.trim() || !formData.last_name.trim()) {
        error = 'First name and last name are required';
        return;
      }

      // Update profile
      const updatedProfile = await apiClient.updateUserProfile(formData);
      
      // Update local state
      profile = updatedProfile;
      isEditing = false;
      success = 'Profile updated successfully!';

      // Update auth store with new profile data
      authStore.updateUser(updatedProfile);

      // Clear success message after 3 seconds
      setTimeout(() => {
        success = null;
      }, 3000);

    } catch (err) {
      console.error('Error saving profile:', err);
      if (err instanceof ApiError) {
        error = err.message;
      } else {
        error = 'Failed to update profile';
      }
    } finally {
      saving = false;
    }
  }

  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  }

  function getAccountAge() {
    if (!profile?.created_at) return 'N/A';
    const created = new Date(profile.created_at);
    const now = new Date();
    const diffTime = Math.abs(now - created);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 30) {
      return `${diffDays} days`;
    } else if (diffDays < 365) {
      const months = Math.floor(diffDays / 30);
      return `${months} month${months > 1 ? 's' : ''}`;
    } else {
      const years = Math.floor(diffDays / 365);
      return `${years} year${years > 1 ? 's' : ''}`;
    }
  }
</script>

<div class="profile-container">
  <div class="profile-header">
    <h1>👤 My Profile</h1>
    <p>Manage your account information and preferences</p>
  </div>

  {#if loading}
    <div class="loading">
      <div class="loading-spinner"></div>
      <p>Loading profile...</p>
    </div>
  {:else if !authState.isAuthenticated}
    <div class="error">
      <p>Please log in to view your profile.</p>
    </div>
  {:else if profile}
    <!-- Profile Information -->
    <div class="profile-content">
      <div class="profile-card">
        <div class="card-header">
          <h2>Personal Information</h2>
          {#if !isEditing}
            <button class="btn btn-secondary" on:click={startEditing}>
              ✏️ Edit
            </button>
          {/if}
        </div>

        {#if error}
          <div class="alert alert-error">
            {error}
          </div>
        {/if}

        {#if success}
          <div class="alert alert-success">
            {success}
          </div>
        {/if}

        <div class="profile-form">
          {#if isEditing}
            <!-- Edit Mode -->
            <div class="form-group">
              <label for="first_name">First Name</label>
              <input
                type="text"
                id="first_name"
                bind:value={formData.first_name}
                placeholder="Enter your first name"
                disabled={saving}
              />
            </div>

            <div class="form-group">
              <label for="last_name">Last Name</label>
              <input
                type="text"
                id="last_name"
                bind:value={formData.last_name}
                placeholder="Enter your last name"
                disabled={saving}
              />
            </div>

            <div class="form-actions">
              <button 
                class="btn btn-primary" 
                on:click={saveProfile}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button 
                class="btn btn-secondary" 
                on:click={cancelEditing}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          {:else}
            <!-- View Mode -->
            <div class="profile-info">
              <div class="info-item">
                <label>First Name</label>
                <span>{profile.first_name || 'Not set'}</span>
              </div>

              <div class="info-item">
                <label>Last Name</label>
                <span>{profile.last_name || 'Not set'}</span>
              </div>

              <div class="info-item">
                <label>Username</label>
                <span>{profile.username}</span>
              </div>

              <div class="info-item">
                <label>Email</label>
                <span>{profile.email}</span>
              </div>
            </div>
          {/if}
        </div>
      </div>

      <!-- Account Statistics -->
      <div class="stats-card">
        <h2>Account Statistics</h2>
        
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-icon">📚</div>
            <div class="stat-content">
              <div class="stat-number">{repositories.length}</div>
              <div class="stat-label">Repositories</div>
            </div>
          </div>

          <div class="stat-item">
            <div class="stat-icon">📅</div>
            <div class="stat-content">
              <div class="stat-number">{getAccountAge()}</div>
              <div class="stat-label">Account Age</div>
            </div>
          </div>

          <div class="stat-item">
            <div class="stat-icon">✅</div>
            <div class="stat-content">
              <div class="stat-number">{profile.is_verified ? 'Yes' : 'No'}</div>
              <div class="stat-label">Email Verified</div>
            </div>
          </div>

          <div class="stat-item">
            <div class="stat-icon">👑</div>
            <div class="stat-content">
              <div class="stat-number">{profile.is_admin ? 'Yes' : 'No'}</div>
              <div class="stat-label">Admin User</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Account Details -->
      <div class="details-card">
        <h2>Account Details</h2>
        
        <div class="details-grid">
          <div class="detail-item">
            <label>Member Since</label>
            <span>{formatDate(profile.created_at)}</span>
          </div>

          <div class="detail-item">
            <label>Last Updated</label>
            <span>{formatDate(profile.updated_at)}</span>
          </div>

          <div class="detail-item">
            <label>Last Login</label>
            <span>{formatDate(profile.last_login_at)}</span>
          </div>

          <div class="detail-item">
            <label>Account Status</label>
            <span class="status-badge" class:active={profile.is_active}>
              {profile.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </div>
    </div>
  {:else}
    <div class="error">
      <p>Failed to load profile information.</p>
      <button class="btn btn-primary" on:click={loadProfile}>Retry</button>
    </div>
  {/if}
</div>

<style>
  .profile-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }

  .profile-header {
    text-align: center;
    margin-bottom: 3rem;
  }

  .profile-header h1 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 2.5rem;
  }

  .profile-header p {
    margin: 0;
    color: #666;
    font-size: 1.1rem;
  }

  .loading {
    text-align: center;
    padding: 3rem 0;
  }

  .loading-spinner {
    width: 3rem;
    height: 3rem;
    border: 4px solid #e1e5e9;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error {
    text-align: center;
    padding: 2rem;
    color: #dc3545;
  }

  .profile-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    grid-template-areas:
      "profile stats"
      "profile details";
  }

  .profile-card {
    grid-area: profile;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
  }

  .stats-card {
    grid-area: stats;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
  }

  .details-card {
    grid-area: details;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .card-header h2 {
    margin: 0;
    color: #333;
    font-size: 1.5rem;
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

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #333;
  }

  .form-group input {
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

  .form-actions {
    display: flex;
    gap: 1rem;
    margin-top: 2rem;
  }

  .profile-info {
    display: grid;
    gap: 1.5rem;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    border-bottom: 1px solid #e1e5e9;
  }

  .info-item:last-child {
    border-bottom: none;
  }

  .info-item label {
    font-weight: 600;
    color: #555;
  }

  .info-item span {
    color: #333;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 8px;
  }

  .stat-icon {
    font-size: 2rem;
  }

  .stat-content {
    flex: 1;
  }

  .stat-number {
    font-size: 1.5rem;
    font-weight: 700;
    color: #333;
    margin-bottom: 0.25rem;
  }

  .stat-label {
    font-size: 0.9rem;
    color: #666;
  }

  .details-grid {
    display: grid;
    gap: 1rem;
  }

  .detail-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #e1e5e9;
  }

  .detail-item:last-child {
    border-bottom: none;
  }

  .detail-item label {
    font-weight: 600;
    color: #555;
  }

  .detail-item span {
    color: #333;
  }

  .status-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    font-size: 0.9rem;
    font-weight: 500;
    background: #f8d7da;
    color: #721c24;
  }

  .status-badge.active {
    background: #d4edda;
    color: #155724;
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
    .profile-container {
      padding: 1rem;
    }

    .profile-content {
      grid-template-columns: 1fr;
      grid-template-areas:
        "profile"
        "stats"
        "details";
    }

    .stats-grid {
      grid-template-columns: 1fr;
    }

    .form-actions {
      flex-direction: column;
    }

    .card-header {
      flex-direction: column;
      gap: 1rem;
      align-items: stretch;
    }
  }
</style>
