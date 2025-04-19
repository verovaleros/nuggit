<script>
  import { onMount } from 'svelte';

  let repoId = null;
  let repo = null;
  let loading = true;
  let error = null;

  let tags = '';
  let notes = '';
  let saveStatus = '';
  let updateStatus = '';
  let showDeleteConfirm = false;
  let deleteError = '';

  onMount(async () => {
    const hash = window.location.hash;
    const parts = hash.split('/');
    const encodedId = parts[2];

    try {
      repoId = atob(encodedId);
    } catch (err) {
      error = 'Invalid repository ID.';
      loading = false;
      return;
    }

    try {
      const res = await fetch(`http://localhost:8000/repositories/${repoId}`);

      if (!res.ok) {
        throw new Error(await res.text());
      }

      repo = await res.json();
      tags = repo.tags || '';
      notes = repo.notes || '';
    } catch (err) {
      error = `Failed to fetch repository details: ${err.message}`;
      console.error(err);
    } finally {
      loading = false;
    }
  });

  async function saveMetadata() {
    saveStatus = 'Saving...';
    try {
      // Use the metadata endpoint for updating tags and notes
      const res = await fetch(`http://localhost:8000/repositories/${repoId}/metadata`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tags, notes })
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      saveStatus = '✅ Saved!';

      // Clear the status after 3 seconds
      setTimeout(() => {
        saveStatus = '';
      }, 3000);
    } catch (err) {
      console.error(err);
      saveStatus = '❌ Failed to save.';
    }
  }

  async function updateRepository() {
    updateStatus = 'Updating from GitHub...';
    try {
      const res = await fetch(`http://localhost:8000/repositories/${repoId}`, {
        method: 'PUT'
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();
      repo = data.repository;
      updateStatus = '✅ Repository updated!';

      // Update the tags and notes from the updated repository
      tags = repo.tags || '';
      notes = repo.notes || '';

      // Clear the status after 3 seconds
      setTimeout(() => {
        updateStatus = '';
      }, 3000);
    } catch (err) {
      console.error(err);
      updateStatus = `❌ Failed to update: ${err.message}`;
    }
  }

  async function deleteRepository() {
    try {
      const res = await fetch(`http://localhost:8000/repositories/${repoId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      // Redirect to home page after successful deletion
      window.location.hash = '#/';
    } catch (err) {
      console.error(err);
      deleteError = `Failed to delete repository: ${err.message}`;
      showDeleteConfirm = false;
    }
  }

  function confirmDelete() {
    showDeleteConfirm = true;
  }

  function cancelDelete() {
    showDeleteConfirm = false;
    deleteError = '';
  }
</script>

<style>
  .container {
    max-width: 960px;
    margin: 2rem auto;
    font-family: sans-serif;
  }

  h1, h2 {
    text-align: center;
    margin-bottom: 1.5rem;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
    box-shadow: 0 0 8px rgba(0, 0, 0, 0.1);
  }

  th, td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid #eee;
  }

  th {
    background-color: #1f2937;
    color: white;
    width: 30%;
  }

  td {
    background-color: #fff;
  }

  input, textarea {
    width: 100%;
    padding: 0.5rem;
    font-family: inherit;
    font-size: 1rem;
    border: 1px solid #ccc;
    border-radius: 6px;
  }

  button {
    padding: 0.6rem 1.2rem;
    font-weight: bold;
    background-color: #1f2937;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
  }

  button:hover {
    background-color: #374151;
  }

  .error {
    color: red;
    text-align: center;
  }

  .save-status, .update-status {
    margin-top: 0.5rem;
    text-align: center;
    font-style: italic;
  }

  .action-buttons {
    display: flex;
    justify-content: center;
    gap: 1rem;
    margin-top: 1rem;
  }

  .update-button {
    background-color: #4f46e5;
  }

  .update-button:hover {
    background-color: #4338ca;
  }

  .delete-button {
    background-color: #ef4444;
  }

  .delete-button:hover {
    background-color: #dc2626;
  }

  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
  }

  .modal {
    background-color: white;
    padding: 2rem;
    border-radius: 8px;
    max-width: 500px;
    width: 90%;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .modal h3 {
    margin-top: 0;
    color: #ef4444;
  }

  .modal-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
  }

  .cancel-button {
    background-color: #6b7280;
  }

  .confirm-button {
    background-color: #ef4444;
  }

  .nav-back {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }
  .nav-back button {
    padding: 0.6rem 1.2rem;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .nav-back button:hover {
    background-color: #e5e7eb;
  }

  .nav-back .add-repo {
    background-color: #1f2937;
    color: white;
  }

  .nav-back .add-repo:hover {
    background-color: #374151;
  }
</style>

<div class="container">
  <div class="nav-back">
    <button on:click={() => (window.location.hash = '#/')}>&larr; Back to Home</button>
    <button class="add-repo" on:click={() => (window.location.hash = '#/?tab=add')}>➕ Add Repo</button>
  </div>
  {#if loading}
    <h1>Loading repository data…</h1>
  {:else if error}
    <p class="error">{error}</p>
  {:else if repo}
    <h1>📦 {repo.name}</h1>

    <table>
      <tbody>
        <tr><th>Full ID</th><td>{repo.id}</td></tr>
        <tr><th>Description</th><td>{repo.description}</td></tr>
        <tr><th>License</th><td>{repo.license}</td></tr>
        <tr><th>Stars</th><td>{repo.stars}</td></tr>
        <tr><th>Forks</th><td>{repo.forks}</td></tr>
        <tr><th>Issues</th><td>{repo.issues}</td></tr>
        <tr><th>Contributors</th><td>{repo.contributors}</td></tr>
        <tr><th>Total Commits</th><td>{repo.commits}</td></tr>
        <tr><th>Last Commit</th><td>{repo.last_commit}</td></tr>
        <tr><th>Created At</th><td>{repo.created_at}</td></tr>
        <tr><th>Updated At</th><td>{repo.updated_at}</td></tr>
        <tr><th>Last Synced</th><td>{repo.last_synced}</td></tr>
        <tr><th>Topics</th><td>{repo.topics}</td></tr>
        <tr>
          <th>Tags</th>
          <td><input type="text" bind:value={tags} placeholder="Comma-separated tags" /></td>
        </tr>
        <tr>
          <th>Notes</th>
          <td><textarea bind:value={notes} rows="4" placeholder="Write your notes here…"></textarea></td>
        </tr>
        <tr><th>GitHub</th><td><a href={repo.url} target="_blank">{repo.url}</a></td></tr>
      </tbody>
    </table>

    <div style="text-align: center; margin-top: 1rem;">
      <button on:click={saveMetadata}>💾 Save Tags & Notes</button>
      {#if saveStatus}<p class="save-status">{saveStatus}</p>{/if}
    </div>

    <div class="action-buttons">
      <button class="update-button" on:click={updateRepository}>🔄 Update from GitHub</button>
      <button class="delete-button" on:click={confirmDelete}>🗑️ Delete Repository</button>
    </div>
    {#if updateStatus}<p class="update-status">{updateStatus}</p>{/if}

    {#if showDeleteConfirm}
      <div class="modal-overlay">
        <div class="modal">
          <h3>⚠️ Delete Repository</h3>
          <p>Are you sure you want to delete <strong>{repo.name}</strong>?</p>
          <p>This action cannot be undone. The repository will be removed from the database, but the actual GitHub repository will not be affected.</p>

          {#if deleteError}
            <p class="error">{deleteError}</p>
          {/if}

          <div class="modal-buttons">
            <button class="cancel-button" on:click={cancelDelete}>Cancel</button>
            <button class="confirm-button" on:click={deleteRepository}>Delete</button>
          </div>
        </div>
      </div>
    {/if}

    <h2>🕘 Recent Commits</h2>
    {#if repo.recent_commits.length > 0}
      <table>
        <thead>
          <tr>
            <th>SHA</th>
            <th>Author</th>
            <th>Date</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {#each repo.recent_commits as commit}
            <tr>
              <td>{commit.sha}</td>
              <td>{commit.author}</td>
              <td>{commit.date}</td>
              <td>{commit.message}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p style="text-align: center;">No recent commits found.</p>
    {/if}
  {/if}
</div>
