<!--
  Navigation Component for Nuggit Frontend
  
  Auth-aware navigation bar with login/logout buttons, user menu,
  and conditional display based on authentication status.
  Includes user avatar and dropdown menu.
-->

<script>
  import { authStore } from '../lib/stores/authStore.js';
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';

  // Auth state
  $: authState = $authStore;
  $: isAuthenticated = authState.isAuthenticated;
  $: user = authState.user;
  $: isAdmin = user?.is_admin || false;

  // Component state
  let showUserMenu = false;
  let userMenuRef;

  /**
   * Handle logout
   */
  function handleLogout() {
    authStore.logout();
    showUserMenu = false;
  }

  /**
   * Toggle user menu
   */
  function toggleUserMenu() {
    showUserMenu = !showUserMenu;
  }

  /**
   * Navigate to route
   */
  function navigateTo(route) {
    push(route);
    showUserMenu = false;
  }

  /**
   * Close user menu when clicking outside
   */
  function handleClickOutside(event) {
    if (userMenuRef && !userMenuRef.contains(event.target)) {
      showUserMenu = false;
    }
  }

  /**
   * Handle escape key to close menu
   */
  function handleKeydown(event) {
    if (event.key === 'Escape') {
      showUserMenu = false;
    }
  }

  // Add event listeners for closing menu
  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeydown);

    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleKeydown);
    };
  });
</script>

<nav class="navbar">
  <div class="navbar-container">
    <!-- Logo and Brand -->
    <div class="navbar-brand">
      <a href="#/" class="brand-link">
        <span class="brand-icon">🧠</span>
        <span class="brand-text">Nuggit</span>
      </a>
    </div>

    <!-- Navigation Links -->
    <div class="navbar-nav">
      {#if isAuthenticated}
        <!-- Authenticated Navigation -->
        <a href="#/" class="nav-link">
          <span class="nav-icon">🏠</span>
          Repositories
        </a>
        
        {#if isAdmin}
          <a href="#/admin" class="nav-link">
            <span class="nav-icon">⚙️</span>
            Admin
          </a>
        {/if}
      {/if}
    </div>

    <!-- User Menu / Auth Buttons -->
    <div class="navbar-actions">
      {#if isAuthenticated}
        <!-- User Menu -->
        <div class="user-menu" bind:this={userMenuRef}>
          <button class="user-menu-trigger" on:click={toggleUserMenu}>
            <div class="user-avatar">
              {user?.first_name?.[0]?.toUpperCase() || '?'}
            </div>
            <span class="user-name">
              {user?.first_name || 'User'}
            </span>
            <span class="dropdown-arrow" class:open={showUserMenu}>▼</span>
          </button>

          {#if showUserMenu}
            <div class="user-menu-dropdown">
              <div class="user-info">
                <div class="user-details">
                  <div class="user-full-name">
                    {user?.first_name} {user?.last_name}
                  </div>
                  <div class="user-email">
                    {user?.email}
                  </div>
                  {#if isAdmin}
                    <div class="user-role">
                      <span class="admin-badge">Admin</span>
                    </div>
                  {/if}
                </div>
              </div>

              <div class="menu-divider"></div>

              <div class="menu-items">
                <button class="menu-item" on:click={() => navigateTo('/profile')}>
                  <span class="menu-icon">👤</span>
                  Profile
                </button>
                
                <button class="menu-item" on:click={() => navigateTo('/settings')}>
                  <span class="menu-icon">⚙️</span>
                  Settings
                </button>

                {#if isAdmin}
                  <button class="menu-item" on:click={() => navigateTo('/admin')}>
                    <span class="menu-icon">🛠️</span>
                    Admin Panel
                  </button>
                {/if}
              </div>

              <div class="menu-divider"></div>

              <div class="menu-items">
                <button class="menu-item logout" on:click={handleLogout}>
                  <span class="menu-icon">🚪</span>
                  Sign Out
                </button>
              </div>
            </div>
          {/if}
        </div>
      {:else}
        <!-- Authentication Buttons -->
        <div class="auth-buttons">
          <a href="#/login" class="btn btn-outline">
            Sign In
          </a>
          <a href="#/register" class="btn btn-primary">
            Sign Up
          </a>
        </div>
      {/if}
    </div>
  </div>
</nav>

<style>
  .navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: white;
    border-bottom: 1px solid #e1e5e9;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    z-index: 1000;
    height: 60px;
  }

  .navbar-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .navbar-brand {
    display: flex;
    align-items: center;
  }

  .brand-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    text-decoration: none;
    color: #333;
    font-weight: 700;
    font-size: 1.25rem;
  }

  .brand-icon {
    font-size: 1.5rem;
  }

  .brand-text {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .navbar-nav {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .nav-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    text-decoration: none;
    color: #666;
    border-radius: 8px;
    transition: all 0.2s ease;
    font-weight: 500;
  }

  .nav-link:hover {
    background-color: #f8f9fa;
    color: #333;
  }

  .nav-icon {
    font-size: 1.1rem;
  }

  .navbar-actions {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  /* User Menu Styles */
  .user-menu {
    position: relative;
  }

  .user-menu-trigger {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem;
    background: none;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .user-menu-trigger:hover {
    background-color: #f8f9fa;
  }

  .user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.9rem;
  }

  .user-name {
    font-weight: 500;
    color: #333;
  }

  .dropdown-arrow {
    font-size: 0.8rem;
    color: #666;
    transition: transform 0.2s ease;
  }

  .dropdown-arrow.open {
    transform: rotate(180deg);
  }

  .user-menu-dropdown {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 0.5rem;
    background: white;
    border: 1px solid #e1e5e9;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    min-width: 250px;
    overflow: hidden;
    z-index: 1001;
  }

  .user-info {
    padding: 1rem;
    background: #f8f9fa;
  }

  .user-details {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .user-full-name {
    font-weight: 600;
    color: #333;
  }

  .user-email {
    font-size: 0.85rem;
    color: #666;
  }

  .user-role {
    margin-top: 0.5rem;
  }

  .admin-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .menu-divider {
    height: 1px;
    background: #e1e5e9;
  }

  .menu-items {
    padding: 0.5rem 0;
  }

  .menu-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.2s ease;
    font-size: 0.9rem;
    color: #333;
  }

  .menu-item:hover {
    background-color: #f8f9fa;
  }

  .menu-item.logout {
    color: #dc3545;
  }

  .menu-item.logout:hover {
    background-color: #fdf2f2;
  }

  .menu-icon {
    font-size: 1rem;
    width: 1.2rem;
    text-align: center;
  }

  /* Auth Buttons */
  .auth-buttons {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    cursor: pointer;
    border: none;
  }

  .btn-outline {
    background: transparent;
    color: #667eea;
    border: 2px solid #667eea;
  }

  .btn-outline:hover {
    background: #667eea;
    color: white;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .navbar-container {
      padding: 0 0.75rem;
    }

    .navbar-nav {
      display: none;
    }

    .user-name {
      display: none;
    }

    .auth-buttons {
      gap: 0.5rem;
    }

    .btn {
      padding: 0.4rem 0.8rem;
      font-size: 0.85rem;
    }

    .user-menu-dropdown {
      min-width: 200px;
      right: -1rem;
    }
  }

  @media (max-width: 480px) {
    .brand-text {
      display: none;
    }
  }
</style>
