<!--
  Admin Dashboard Component for Nuggit Frontend
  
  Provides administrative functionality including user management,
  system statistics, and administrative controls.
  Requires admin privileges to access.
-->

<script>
  import { onMount } from 'svelte';
  import { authStore } from '../lib/stores/authStore.js';
  import { apiClient, ApiError } from '../lib/api/apiClient.js';

  // Auth state
  $: authState = $authStore;
  $: currentUser = authState.user;
  $: isAdmin = currentUser?.is_admin || false;

  // Component state
  let loading = true;
  let error = null;
  let stats = {
    totalUsers: 0,
    totalRepositories: 0,
    activeUsers: 0,
    verifiedUsers: 0
  };
  let users = [];
  let repositories = [];

  // UI state
  let activeTab = 'overview';
  let showUserModal = false;
  let selectedUser = null;

  onMount(async () => {
    if (!isAdmin) {
      error = 'Access denied. Admin privileges required.';
      loading = false;
      return;
    }

    await loadAdminData();
  });

  async function loadAdminData() {
    try {
      loading = true;
      error = null;

      // Load admin statistics and data
      // Note: These endpoints would need to be implemented in the backend
      const [statsResponse, usersResponse, reposResponse] = await Promise.allSettled([
        loadStats(),
        loadUsers(),
        loadRepositories()
      ]);

      if (statsResponse.status === 'fulfilled') {
        stats = statsResponse.value;
      }
      if (usersResponse.status === 'fulfilled') {
        users = usersResponse.value;
      }
      if (reposResponse.status === 'fulfilled') {
        repositories = reposResponse.value;
      }

    } catch (err) {
      console.error('Error loading admin data:', err);
      error = 'Failed to load admin data';
    } finally {
      loading = false;
    }
  }

  async function loadStats() {
    // Placeholder for admin stats endpoint
    return {
      totalUsers: users.length || 0,
      totalRepositories: repositories.length || 0,
      activeUsers: users.filter(u => u.is_active).length || 0,
      verifiedUsers: users.filter(u => u.is_verified).length || 0
    };
  }

  async function loadUsers() {
    try {
      // This would be an admin-only endpoint to list all users
      // For now, return empty array as endpoint doesn't exist yet
      return [];
    } catch (error) {
      console.error('Error loading users:', error);
      return [];
    }
  }

  async function loadRepositories() {
    try {
      // Admin users can see all repositories
      const response = await apiClient.getRepositories();
      return response.repositories || [];
    } catch (error) {
      console.error('Error loading repositories:', error);
      return [];
    }
  }

  function switchTab(tab) {
    activeTab = tab;
  }

  function openUserModal(user = null) {
    selectedUser = user;
    showUserModal = true;
  }

  function closeUserModal() {
    showUserModal = false;
    selectedUser = null;
  }

  async function toggleUserStatus(userId, field) {
    try {
      // Placeholder for user management endpoint
      console.log(`Toggle ${field} for user ${userId}`);
      // await apiClient.updateUser(userId, { [field]: !user[field] });
      // await loadUsers();
    } catch (error) {
      console.error(`Error toggling user ${field}:`, error);
    }
  }
</script>

<div class="admin-container">
  <div class="admin-header">
    <h1>🛠️ Admin Dashboard</h1>
    <p>System administration and user management</p>
  </div>

  {#if !isAdmin}
    <div class="access-denied">
      <div class="access-denied-card">
        <h2>🚫 Access Denied</h2>
        <p>You need administrator privileges to access this page.</p>
        <a href="#/" class="btn btn-primary">Return to Home</a>
      </div>
    </div>
  {:else if loading}
    <div class="loading">
      <div class="loading-spinner"></div>
      <p>Loading admin data...</p>
    </div>
  {:else if error}
    <div class="error">
      <p>{error}</p>
      <button class="btn btn-primary" on:click={loadAdminData}>Retry</button>
    </div>
  {:else}
    <!-- Admin Navigation -->
    <nav class="admin-nav">
      <button 
        class="nav-button" 
        class:active={activeTab === 'overview'}
        on:click={() => switchTab('overview')}
      >
        📊 Overview
      </button>
      <button 
        class="nav-button" 
        class:active={activeTab === 'users'}
        on:click={() => switchTab('users')}
      >
        👥 Users
      </button>
      <button 
        class="nav-button" 
        class:active={activeTab === 'repositories'}
        on:click={() => switchTab('repositories')}
      >
        📚 Repositories
      </button>
      <button 
        class="nav-button" 
        class:active={activeTab === 'settings'}
        on:click={() => switchTab('settings')}
      >
        ⚙️ Settings
      </button>
    </nav>

    <!-- Admin Content -->
    <div class="admin-content">
      {#if activeTab === 'overview'}
        <!-- Overview Tab -->
        <div class="overview-section">
          <h2>System Overview</h2>
          
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">👥</div>
              <div class="stat-content">
                <div class="stat-number">{stats.totalUsers}</div>
                <div class="stat-label">Total Users</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">📚</div>
              <div class="stat-content">
                <div class="stat-number">{stats.totalRepositories}</div>
                <div class="stat-label">Repositories</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">✅</div>
              <div class="stat-content">
                <div class="stat-number">{stats.activeUsers}</div>
                <div class="stat-label">Active Users</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">🔐</div>
              <div class="stat-content">
                <div class="stat-number">{stats.verifiedUsers}</div>
                <div class="stat-label">Verified Users</div>
              </div>
            </div>
          </div>
        </div>

      {:else if activeTab === 'users'}
        <!-- Users Tab -->
        <div class="users-section">
          <div class="section-header">
            <h2>User Management</h2>
            <button class="btn btn-primary" on:click={() => openUserModal()}>
              ➕ Add User
            </button>
          </div>
          
          {#if users.length === 0}
            <div class="empty-state">
              <p>No users found. User management endpoints need to be implemented.</p>
            </div>
          {:else}
            <div class="users-table">
              <!-- User table would go here -->
              <p>User management table will be implemented when backend endpoints are ready.</p>
            </div>
          {/if}
        </div>

      {:else if activeTab === 'repositories'}
        <!-- Repositories Tab -->
        <div class="repositories-section">
          <div class="section-header">
            <h2>Repository Management</h2>
            <p>Total: {repositories.length} repositories</p>
          </div>
          
          {#if repositories.length === 0}
            <div class="empty-state">
              <p>No repositories found.</p>
            </div>
          {:else}
            <div class="repositories-grid">
              {#each repositories as repo}
                <div class="repo-card">
                  <h3>{repo.name}</h3>
                  <p class="repo-id">{repo.id}</p>
                  <p class="repo-description">{repo.description || 'No description'}</p>
                  <div class="repo-meta">
                    <span class="repo-owner">Owner ID: {repo.owner_id}</span>
                    <span class="repo-stars">⭐ {repo.stars || 0}</span>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>

      {:else if activeTab === 'settings'}
        <!-- Settings Tab -->
        <div class="settings-section">
          <h2>System Settings</h2>
          <div class="settings-placeholder">
            <p>System settings panel will be implemented in future updates.</p>
            <ul>
              <li>Email configuration</li>
              <li>GitHub API settings</li>
              <li>System maintenance</li>
              <li>Backup management</li>
            </ul>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .admin-container {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 1rem;
    font-family: sans-serif;
  }

  .admin-header {
    text-align: center;
    margin-bottom: 2rem;
  }

  .admin-header h1 {
    margin: 0 0 0.5rem 0;
    color: #333;
    font-size: 2rem;
  }

  .admin-header p {
    margin: 0;
    color: #666;
    font-size: 1.1rem;
  }

  .access-denied {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 60vh;
  }

  .access-denied-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    padding: 3rem;
    text-align: center;
    max-width: 400px;
  }

  .access-denied-card h2 {
    color: #dc3545;
    margin-bottom: 1rem;
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

  .admin-nav {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    border-bottom: 1px solid #e1e5e9;
    padding-bottom: 1rem;
  }

  .nav-button {
    padding: 0.75rem 1.5rem;
    border: none;
    background: transparent;
    color: #666;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-weight: 500;
  }

  .nav-button:hover {
    background: #f8f9fa;
    color: #333;
  }

  .nav-button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .stat-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .stat-icon {
    font-size: 2rem;
  }

  .stat-number {
    font-size: 2rem;
    font-weight: 700;
    color: #333;
  }

  .stat-label {
    color: #666;
    font-size: 0.9rem;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  .section-header h2 {
    margin: 0;
    color: #333;
  }

  .empty-state {
    text-align: center;
    padding: 3rem;
    color: #666;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .repositories-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .repo-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
  }

  .repo-card h3 {
    margin: 0 0 0.5rem 0;
    color: #333;
  }

  .repo-id {
    font-family: monospace;
    color: #666;
    font-size: 0.9rem;
    margin: 0 0 1rem 0;
  }

  .repo-description {
    color: #666;
    margin: 0 0 1rem 0;
    line-height: 1.5;
  }

  .repo-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.9rem;
    color: #666;
  }

  .settings-placeholder {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    padding: 2rem;
  }

  .settings-placeholder ul {
    margin-top: 1rem;
    padding-left: 1.5rem;
  }

  .settings-placeholder li {
    margin-bottom: 0.5rem;
    color: #666;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    cursor: pointer;
    border: none;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  /* Responsive design */
  @media (max-width: 768px) {
    .admin-nav {
      flex-wrap: wrap;
    }

    .nav-button {
      flex: 1;
      min-width: 120px;
    }

    .section-header {
      flex-direction: column;
      gap: 1rem;
      align-items: stretch;
    }

    .stats-grid {
      grid-template-columns: 1fr;
    }

    .repositories-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
