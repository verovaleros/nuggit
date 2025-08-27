<script>
  import { formatDateTime, formatRelativeTime } from '../lib/timezone.js';
  import { apiClient } from '../lib/api/apiClient.js';

  let backups = [];
  let isCreatingBackup = false;
  let backupStatus = '';
  let isLoadingBackups = false;

  async function loadBackups() {
    isLoadingBackups = true;
    try {
      const data = await apiClient.request('/health/health/backups');
      backups = data.backups || [];
      console.log('Loaded backups:', backups);
    } catch (error) {
      console.error('Error loading backups:', error);
      backupStatus = 'Error loading backups: ' + error.message;
    } finally {
      isLoadingBackups = false;
    }
  }

  async function createBackup() {
    isCreatingBackup = true;
    backupStatus = 'Creating backup...';

    try {
      const data = await apiClient.request('/health/health/backup', {
        method: 'POST'
      });
      backupStatus = `✅ Backup created successfully: ${data.backup_path}`;
      // Reload backups list
      await loadBackups();
    } catch (error) {
      console.error('Error creating backup:', error);
      backupStatus = `❌ Backup failed: ${error.message}`;
    } finally {
      isCreatingBackup = false;
    }
  }

  async function createAutoBackup() {
    isCreatingBackup = true;
    backupStatus = 'Creating automatic backup...';

    try {
      const data = await apiClient.request('/health/health/backup/auto', {
        method: 'POST'
      });
      backupStatus = `✅ Auto backup created successfully: ${data.backup_path}`;
      // Reload backups list
      await loadBackups();
    } catch (error) {
      console.error('Error creating auto backup:', error);
      backupStatus = `❌ Auto backup failed: ${error.message}`;
    } finally {
      isCreatingBackup = false;
    }
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Load backups when component mounts
  loadBackups();
</script>

<div class="admin-container">
  <h2>🔧 Admin Panel</h2>
  
  <div class="admin-section">
    <h3>📦 Database Backups</h3>
    <p>Create and manage database backups to protect your repository data.</p>
    
    <div class="backup-actions">
      <button 
        class="backup-btn primary" 
        on:click={createBackup} 
        disabled={isCreatingBackup}
      >
        {isCreatingBackup ? '⏳ Creating...' : '💾 Create Backup'}
      </button>
      
      <button 
        class="backup-btn secondary" 
        on:click={createAutoBackup} 
        disabled={isCreatingBackup}
      >
        {isCreatingBackup ? '⏳ Creating...' : '🤖 Auto Backup'}
      </button>
      
      <button 
        class="backup-btn tertiary" 
        on:click={loadBackups} 
        disabled={isLoadingBackups}
      >
        {isLoadingBackups ? '⏳ Loading...' : '🔄 Refresh'}
      </button>
    </div>
    
    {#if backupStatus}
      <div class="backup-status" class:success={backupStatus.includes('✅')} class:error={backupStatus.includes('❌')}>
        {backupStatus}
      </div>
    {/if}
  </div>

  <div class="admin-section">
    <h3>📋 Available Backups</h3>
    
    {#if isLoadingBackups}
      <div class="loading">Loading backups...</div>
    {:else if backups.length === 0}
      <div class="no-backups">No backups found. Create your first backup above.</div>
    {:else}
      <div class="backups-list">
        {#each backups as backup}
          <div class="backup-item">
            <div class="backup-info">
              <div class="backup-name">
                📁 {backup.name}
                {#if backup.compressed}
                  <span class="compressed-badge">📦 Compressed</span>
                {/if}
              </div>
              <div class="backup-details">
                <span class="backup-size">{formatFileSize(backup.size_bytes)}</span>
                <span class="backup-date">
                  {formatDateTime(backup.created)} 
                  ({formatRelativeTime(backup.created)})
                </span>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div class="admin-section">
    <h3>ℹ️ Information</h3>
    <div class="info-grid">
      <div class="info-item">
        <strong>Backup Location:</strong> backups/ directory
      </div>
      <div class="info-item">
        <strong>Auto Cleanup:</strong> Keeps last 10 automatic backups
      </div>
      <div class="info-item">
        <strong>Compression:</strong> Backups are automatically compressed
      </div>
    </div>
  </div>
</div>

<style>
  .admin-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 1rem;
  }

  .admin-section {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .admin-section h3 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    color: #1f2937;
  }

  .backup-actions {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
    flex-wrap: wrap;
  }

  .backup-btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .backup-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .backup-btn.primary {
    background-color: #3b82f6;
    color: white;
  }

  .backup-btn.primary:hover:not(:disabled) {
    background-color: #2563eb;
  }

  .backup-btn.secondary {
    background-color: #10b981;
    color: white;
  }

  .backup-btn.secondary:hover:not(:disabled) {
    background-color: #059669;
  }

  .backup-btn.tertiary {
    background-color: #6b7280;
    color: white;
  }

  .backup-btn.tertiary:hover:not(:disabled) {
    background-color: #4b5563;
  }

  .backup-status {
    padding: 0.75rem;
    border-radius: 6px;
    margin-top: 1rem;
    font-weight: 500;
  }

  .backup-status.success {
    background-color: #d1fae5;
    color: #065f46;
    border: 1px solid #a7f3d0;
  }

  .backup-status.error {
    background-color: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
  }

  .loading, .no-backups {
    text-align: center;
    padding: 2rem;
    color: #6b7280;
    font-style: italic;
  }

  .backups-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .backup-item {
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 1rem;
    background-color: #f9fafb;
  }

  .backup-info {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .backup-name {
    font-weight: 600;
    color: #1f2937;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .compressed-badge {
    background-color: #dbeafe;
    color: #1e40af;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .backup-details {
    display: flex;
    gap: 1rem;
    font-size: 0.875rem;
    color: #6b7280;
  }

  .backup-size {
    font-weight: 500;
  }

  .info-grid {
    display: grid;
    gap: 0.75rem;
  }

  .info-item {
    padding: 0.75rem;
    background-color: #f3f4f6;
    border-radius: 4px;
    font-size: 0.875rem;
  }

  .info-item strong {
    color: #374151;
  }

  @media (max-width: 640px) {
    .backup-actions {
      flex-direction: column;
    }
    
    .backup-details {
      flex-direction: column;
      gap: 0.25rem;
    }
  }
</style>
