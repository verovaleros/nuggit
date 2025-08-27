<!--
  Admin Dashboard Component for Nuggit Frontend
  
  Provides administrative functionality including user management,
  system statistics, and administrative controls.
  Requires admin privileges to access.
-->

<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authStore } from '../lib/stores/authStore.js';
  import { apiClient, ApiError } from '../lib/api/apiClient.js';

  // Auth state
  $: authState = $authStore;
  $: currentUser = authState.user;
  $: isAdmin = currentUser?.is_admin || false;

  // Redirect if not authenticated or not admin
  $: if (authState.isInitialized) {
    if (!authState.isAuthenticated) {
      import('svelte-spa-router').then(({ push }) => {
        sessionStorage.setItem('nuggit_redirect_after_login', window.location.hash);
        push('/login');
      });
    } else if (!isAdmin) {
      import('svelte-spa-router').then(({ push }) => {
        push('/home');
      });
    }
  }

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

      // Check authentication before loading data
      if (!authState.isAuthenticated) {
        error = 'Authentication required. Please log in.';
        push('/login');
        return;
      }

      if (!isAdmin) {
        error = 'Admin privileges required to access this page.';
        push('/home');
        return;
      }

      // Load admin statistics and data
      const [statsResponse, usersResponse, reposResponse] = await Promise.allSettled([
        loadStats(),
        loadUsers(),
        loadRepositories()
      ]);

      if (statsResponse.status === 'fulfilled' && statsResponse.value) {
        stats = statsResponse.value;
      }
      if (usersResponse.status === 'fulfilled' && usersResponse.value) {
        users = usersResponse.value;
      }
      if (reposResponse.status === 'fulfilled' && reposResponse.value) {
        repositories = reposResponse.value;
      }

    } catch (err) {
      console.error('Error loading admin data:', err);
      error = 'Failed to load admin data. Please try again.';
    } finally {
      loading = false;
    }
  }

  async function loadStats() {
    try {
      const response = await apiClient.getAdminStats();
      return {
        totalUsers: response.users.total,
        totalRepositories: response.repositories.total,
        activeUsers: response.users.active,
        verifiedUsers: response.users.verified,
        adminUsers: response.users.admin,
        recentUsers: response.users.recent,
        usersWithRepos: response.repositories.users_with_repos,
        avgStars: response.repositories.avg_stars,
        totalStars: response.repositories.total_stars
      };
    } catch (error) {
      console.error('Error loading admin stats:', error);

      // Handle authentication errors specifically
      if (error.status === 401 || error.status === 403) {
        error = 'Authentication required. Please log in as an administrator.';
        // Redirect to login if not authenticated
        push('/login');
        return null;
      }

      // Handle other errors
      if (error.status >= 500) {
        error = 'Server error occurred while loading statistics. Please try again later.';
      }

      return {
        totalUsers: 0,
        totalRepositories: 0,
        activeUsers: 0,
        verifiedUsers: 0,
        adminUsers: 0,
        recentUsers: 0,
        usersWithRepos: 0,
        avgStars: 0,
        totalStars: 0
      };
    }
  }

  async function loadUsers() {
    try {
      const response = await apiClient.getUsers(1, 50); // Load first 50 users
      return response.users || [];
    } catch (error) {
      console.error('Error loading users:', error);

      // Handle authentication errors specifically
      if (error.status === 401 || error.status === 403) {
        error = 'Authentication required. Please log in as an administrator.';
        push('/login');
        return [];
      }

      // Handle other errors
      if (error.status >= 500) {
        error = 'Server error occurred while loading users. Please try again later.';
      }

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

      // Handle authentication errors specifically
      if (error.status === 401 || error.status === 403) {
        error = 'Authentication required. Please log in as an administrator.';
        push('/login');
        return [];
      }

      // Handle other errors
      if (error.status >= 500) {
        error = 'Server error occurred while loading repositories. Please try again later.';
      }

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
      const user = users.find(u => u.id === userId);
      if (!user) return;

      const updateData = { [field]: !user[field] };
      await apiClient.updateUser(userId, updateData);

      // Update local state
      user[field] = !user[field];
      users = [...users]; // Trigger reactivity

      // Reload stats to reflect changes
      stats = await loadStats();

      console.log(`Successfully toggled ${field} for user ${userId}`);
    } catch (error) {
      console.error(`Error toggling user ${field}:`, error);
      // Optionally show user-friendly error message
      alert(`Failed to update user ${field}. Please try again.`);
    }
  }

  async function refreshData() {
    await loadAdminData();
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
          <div class="section-header">
            <h2>System Overview</h2>
            <button class="btn btn-secondary" on:click={refreshData}>
              🔄 Refresh
            </button>
          </div>

          <!-- User Statistics -->
          <div class="stats-section">
            <h3>User Statistics</h3>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.totalUsers}</div>
                  <div class="stat-label">Total Users</div>
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

              <div class="stat-card">
                <div class="stat-icon">👑</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.adminUsers || 0}</div>
                  <div class="stat-label">Admin Users</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon">🆕</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.recentUsers || 0}</div>
                  <div class="stat-label">New Users (30d)</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Repository Statistics -->
          <div class="stats-section">
            <h3>Repository Statistics</h3>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon">📚</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.totalRepositories}</div>
                  <div class="stat-label">Total Repositories</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon">👤</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.usersWithRepos || 0}</div>
                  <div class="stat-label">Users with Repos</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon">⭐</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.totalStars || 0}</div>
                  <div class="stat-label">Total Stars</div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon">📊</div>
                <div class="stat-content">
                  <div class="stat-number">{stats.avgStars || 0}</div>
                  <div class="stat-label">Avg Stars/Repo</div>
                </div>
              </div>
            </div>
          </div>
        </div>

      {:else if activeTab === 'users'}
        <!-- Users Tab -->
        <div class="users-section">
          <div class="section-header">
            <h2>User Management</h2>
            <div class="user-stats-summary">
              <span class="summary-item">Total: {users.length}</span>
              <span class="summary-item">Active: {users.filter(u => u.is_active).length}</span>
              <span class="summary-item">Verified: {users.filter(u => u.is_verified).length}</span>
            </div>
          </div>

          {#if users.length === 0}
            <div class="empty-state">
              <p>No users found.</p>
            </div>
          {:else}
            <div class="users-table-container">
              <table class="users-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Verified</th>
                    <th>Admin</th>
                    <th>Repositories</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {#each users as user}
                    <tr class:inactive={!user.is_active}>
                      <td>{user.id}</td>
                      <td class="username-cell">
                        <span class="username">{user.username}</span>
                        {#if user.is_admin}
                          <span class="admin-badge">👑</span>
                        {/if}
                      </td>
                      <td class="email-cell">{user.email}</td>
                      <td>
                        <span class="status-badge" class:active={user.is_active} class:inactive={!user.is_active}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <span class="verification-badge" class:verified={user.is_verified} class:unverified={!user.is_verified}>
                          {user.is_verified ? '✅' : '❌'}
                        </span>
                      </td>
                      <td>
                        <span class="admin-status">
                          {user.is_admin ? '👑 Yes' : 'No'}
                        </span>
                      </td>
                      <td class="repo-count">
                        {repositories.filter(r => r.user_id === user.id).length}
                      </td>
                      <td class="date-cell">
                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td class="actions-cell">
                        <div class="action-buttons">
                          <button
                            class="btn btn-sm"
                            class:btn-success={!user.is_active}
                            class:btn-warning={user.is_active}
                            on:click={() => toggleUserStatus(user.id, 'is_active')}
                            title={user.is_active ? 'Deactivate user' : 'Activate user'}
                          >
                            {user.is_active ? '⏸️' : '▶️'}
                          </button>

                          <button
                            class="btn btn-sm btn-info"
                            on:click={() => toggleUserStatus(user.id, 'is_verified')}
                            title={user.is_verified ? 'Unverify user' : 'Verify user'}
                          >
                            {user.is_verified ? '🔓' : '🔒'}
                          </button>

                          <button
                            class="btn btn-sm"
                            class:btn-danger={user.is_admin}
                            class:btn-secondary={!user.is_admin}
                            on:click={() => toggleUserStatus(user.id, 'is_admin')}
                            title={user.is_admin ? 'Remove admin' : 'Make admin'}
                          >
                            {user.is_admin ? '👑➖' : '👑➕'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
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
                    <span class="repo-owner">Owner ID: {repo.user_id}</span>
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

  .stats-section {
    margin-bottom: 3rem;
  }

  .stats-section h3 {
    margin: 0 0 1rem 0;
    color: #555;
    font-size: 1.2rem;
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

  /* User Management Styles */
  .user-stats-summary {
    display: flex;
    gap: 1rem;
    font-size: 0.9rem;
    color: #666;
  }

  .summary-item {
    padding: 0.25rem 0.5rem;
    background: #f8f9fa;
    border-radius: 4px;
  }

  .users-table-container {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  .users-table {
    width: 100%;
    border-collapse: collapse;
  }

  .users-table th,
  .users-table td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid #e1e5e9;
  }

  .users-table th {
    background: #f8f9fa;
    font-weight: 600;
    color: #333;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .users-table tr:hover {
    background: #f8f9fa;
  }

  .users-table tr.inactive {
    opacity: 0.6;
  }

  .username-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .admin-badge {
    font-size: 0.8rem;
  }

  .email-cell {
    font-family: monospace;
    font-size: 0.9rem;
  }

  .status-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .status-badge.active {
    background: #d4edda;
    color: #155724;
  }

  .status-badge.inactive {
    background: #f8d7da;
    color: #721c24;
  }

  .verification-badge {
    font-size: 1.2rem;
  }

  .date-cell {
    font-size: 0.9rem;
    color: #666;
  }

  .actions-cell {
    white-space: nowrap;
  }

  .action-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
    border-radius: 4px;
  }

  .btn-success {
    background: #28a745;
    color: white;
  }

  .btn-warning {
    background: #ffc107;
    color: #212529;
  }

  .btn-info {
    background: #17a2b8;
    color: white;
  }

  .btn-danger {
    background: #dc3545;
    color: white;
  }

  .btn-secondary {
    background: #6c757d;
    color: white;
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
