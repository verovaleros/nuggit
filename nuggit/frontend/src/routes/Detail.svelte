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

  // Comments
  let newComment = '';
  let commentAuthor = 'Anonymous';
  let commentStatus = '';
  let addingComment = false;

  // Collapsible sections
  let commentsCollapsed = true;
  let commitsCollapsed = true;
  let versionsCollapsed = true;

  // Version tracker
  let newVersion = '';
  let versionReleaseDate = '';
  let versionDescription = '';
  let versionStatus = '';
  let addingVersion = false;

  // Version comparison
  let showComparison = false;
  let selectedVersion1 = null;
  let selectedVersion2 = null;
  let comparisonResult = null;
  let comparisonError = null;
  let loadingComparison = false;

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
      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      // Fetch repository details
      const res = await fetch(`http://localhost:8000/repositories/${encodedRepoId}`);

      if (!res.ok) {
        throw new Error(await res.text());
      }

      repo = await res.json();
      tags = repo.tags || '';
      notes = repo.notes || '';

      // Fetch versions using the new API endpoint
      try {
        const versionsRes = await fetch(`http://localhost:8000/api/get-versions?repo_id=${encodedRepoId}`);

        if (versionsRes.ok) {
          const versions = await versionsRes.json();
          repo.versions = versions;
          console.log('Versions fetched successfully:', versions);
        } else {
          console.error('Failed to fetch versions:', await versionsRes.text());
        }
      } catch (versionsErr) {
        console.error('Error fetching versions:', versionsErr);
      }
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
      // Use the metadata endpoint for updating tags
      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      const res = await fetch(`http://localhost:8000/repositories/${encodedRepoId}/metadata`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tags, notes: '' }) // Keep notes parameter for API compatibility
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
      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      const res = await fetch(`http://localhost:8000/repositories/${encodedRepoId}`, {
        method: 'PUT'
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      // Parse the response from the update endpoint
      const updateData = await res.json();
      console.log('Update response:', updateData);

      // After successful update, fetch the repository details again to get the latest data
      // including comments and recent commits
      try {
        // Encode the repository ID for the URL
        const encodedRepoId = encodeURIComponent(repoId);

        const detailRes = await fetch(`http://localhost:8000/repositories/${encodedRepoId}`);

        if (!detailRes.ok) {
          throw new Error(await detailRes.text());
        }

        // Update the repository data with the latest information
        repo = await detailRes.json();
        console.log('Updated repository details:', repo);

        // Update the tags from the updated repository
        tags = repo.tags || '';

        // Fetch versions using the new API endpoint
        try {
          const versionsRes = await fetch(`http://localhost:8000/api/get-versions?repo_id=${encodedRepoId}`);

          if (versionsRes.ok) {
            const versions = await versionsRes.json();
            repo.versions = versions;
            console.log('Versions fetched successfully after update:', versions);
          } else {
            console.error('Failed to fetch versions after update:', await versionsRes.text());
          }
        } catch (versionsErr) {
          console.error('Error fetching versions after update:', versionsErr);
        }

        updateStatus = '✅ Repository updated!';

        // Clear the status after 3 seconds
        setTimeout(() => {
          updateStatus = '';
        }, 3000);
      } catch (detailErr) {
        console.error('Error fetching updated repository details:', detailErr);
        updateStatus = '✅ Repository updated, but failed to refresh details.';
      }
    } catch (err) {
      console.error(err);
      updateStatus = `❌ Failed to update: ${err.message}`;
    }
  }

  async function deleteRepository() {
    try {
      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      const res = await fetch(`http://localhost:8000/repositories/${encodedRepoId}`, {
        method: 'DELETE'
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      // Redirect to home page after successful deletion
      window.location.hash = '';
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

  function toggleComments() {
    commentsCollapsed = !commentsCollapsed;
  }

  function toggleCommits() {
    commitsCollapsed = !commitsCollapsed;
  }

  function toggleVersions() {
    versionsCollapsed = !versionsCollapsed;
  }

  function toggleComparison() {
    showComparison = !showComparison;
    if (!showComparison) {
      // Reset comparison state when closing
      selectedVersion1 = null;
      selectedVersion2 = null;
      comparisonResult = null;
      comparisonError = null;
    }
  }

  async function compareVersions() {
    if (!selectedVersion1 || !selectedVersion2) {
      comparisonError = 'Please select two versions to compare.';
      return;
    }

    if (selectedVersion1 === selectedVersion2) {
      comparisonError = 'Please select two different versions to compare.';
      return;
    }

    loadingComparison = true;
    comparisonError = null;
    comparisonResult = null;

    try {
      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      // Use the new API endpoint that works with query parameters
      console.log(`Using API endpoint: http://localhost:8000/api/compare-versions?repo_id=${encodedRepoId}&version1_id=${selectedVersion1}&version2_id=${selectedVersion2}`);
      const queryRes = await fetch(`http://localhost:8000/api/compare-versions?repo_id=${encodedRepoId}&version1_id=${selectedVersion1}&version2_id=${selectedVersion2}`);

      if (!queryRes.ok) {
        throw new Error(await queryRes.text());
      }

      comparisonResult = await queryRes.json();
      console.log('Version comparison succeeded:', comparisonResult);
    } catch (err) {
      console.error(err);
      comparisonError = `Failed to compare versions: ${err.message}`;
    } finally {
      loadingComparison = false;
    }
  }

  function formatDiff(diff) {
    if (!diff) return '';

    // Split the diff into lines
    const lines = diff.split('\n');

    // Format each line with appropriate styling
    return lines.map(line => {
      if (line.startsWith('+')) {
        return `<span class="diff-line-added">${line}</span>`;
      } else if (line.startsWith('-')) {
        return `<span class="diff-line-removed">${line}</span>`;
      } else {
        return line;
      }
    }).join('\n');
  }

  async function addVersion() {
    if (!newVersion.trim()) {
      versionStatus = 'Please enter a version number.';
      return;
    }

    addingVersion = true;
    versionStatus = 'Adding version...';

    try {
      const versionData = {
        version_number: newVersion.trim(),
        release_date: versionReleaseDate || null,
        description: versionDescription.trim() || null
      };

      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      const res = await fetch(`http://localhost:8000/repositories/${encodedRepoId}/versions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(versionData)
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      // Get the new version
      const newVersionData = await res.json();

      // Fetch all versions to ensure we have the latest list
      try {
        const versionsRes = await fetch(`http://localhost:8000/api/get-versions?repo_id=${encodedRepoId}`);

        if (versionsRes.ok) {
          const versions = await versionsRes.json();
          repo.versions = versions;
          console.log('Versions fetched successfully after adding new version:', versions);
        } else {
          // If fetching all versions fails, just add the new one to the list
          console.error('Failed to fetch versions after adding new version:', await versionsRes.text());
          repo.versions = [newVersionData, ...repo.versions];
        }
      } catch (versionsErr) {
        console.error('Error fetching versions after adding new version:', versionsErr);
        // If fetching all versions fails, just add the new one to the list
        repo.versions = [newVersionData, ...repo.versions];
      }

      // Clear the form
      newVersion = '';
      versionReleaseDate = '';
      versionDescription = '';
      versionStatus = '✅ Version added!';

      // Clear the status after 3 seconds
      setTimeout(() => {
        versionStatus = '';
      }, 3000);
    } catch (err) {
      console.error(err);
      versionStatus = `❌ Failed to add version: ${err.message}`;
    } finally {
      addingVersion = false;
    }
  }

  async function addComment() {
    if (!newComment.trim()) {
      commentStatus = 'Please enter a comment.';
      return;
    }

    addingComment = true;
    commentStatus = 'Adding comment...';

    try {
      // Encode the repository ID for the URL
      const encodedRepoId = encodeURIComponent(repoId);

      const res = await fetch(`http://localhost:8000/repositories/${encodedRepoId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          comment: newComment.trim(),
          author: commentAuthor.trim() || 'Anonymous'
        })
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      // Get the new comment
      const newCommentData = await res.json();

      // Add the new comment to the list
      repo.comments = [newCommentData, ...repo.comments];

      // Clear the form
      newComment = '';
      commentStatus = '✅ Comment added!';

      // Clear the status after 3 seconds
      setTimeout(() => {
        commentStatus = '';
      }, 3000);
    } catch (err) {
      console.error(err);
      commentStatus = `❌ Failed to add comment: ${err.message}`;
    } finally {
      addingComment = false;
    }
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

  /* Comments styles */
  .comments-section {
    margin-top: 2rem;
  }

  .comments-list {
    margin-top: 1rem;
  }

  .comment {
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .comment-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: #6b7280;
  }

  .comment-author {
    font-weight: bold;
  }

  .comment-content {
    white-space: pre-wrap;
    word-break: break-word;
  }

  .comment-form {
    margin-top: 1rem;
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
  }

  .comment-form textarea {
    width: 100%;
    min-height: 100px;
    margin-bottom: 0.5rem;
  }

  .comment-form-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .comment-form-header input {
    width: 200px;
  }

  .comment-status, .version-status {
    margin-top: 0.5rem;
    text-align: center;
    font-style: italic;
  }

  /* Version tracker styles */
  .versions-section {
    margin-top: 2rem;
  }

  .versions-list {
    margin-top: 1rem;
  }

  .version {
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .version-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: #6b7280;
  }

  .version-number {
    font-weight: bold;
    font-size: 1.1rem;
    color: #1f2937;
  }

  .version-date {
    font-style: italic;
  }

  .version-description {
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 0.5rem;
  }

  .version-form {
    margin-top: 1rem;
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
  }

  .version-form-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .version-form-row .field {
    flex: 1;
  }

  .version-form-row label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
    font-size: 0.9rem;
  }

  .version-form textarea {
    width: 100%;
    min-height: 100px;
    margin-bottom: 0.5rem;
  }

  /* Version comparison styles */
  .comparison-container {
    margin-top: 1.5rem;
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .comparison-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .comparison-header h3 {
    margin: 0;
    font-size: 1.2rem;
  }

  .comparison-header button {
    padding: 0.4rem 0.8rem;
    font-size: 0.9rem;
  }

  .comparison-selectors {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .comparison-selector {
    flex: 1;
  }

  .comparison-selector label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
    font-size: 0.9rem;
  }

  .comparison-selector select {
    width: 100%;
    padding: 0.5rem;
    border-radius: 6px;
    border: 1px solid #ccc;
  }

  .comparison-results {
    margin-top: 1.5rem;
  }

  .comparison-field {
    margin-bottom: 1.5rem;
  }

  .comparison-field h4 {
    margin-top: 0;
    margin-bottom: 0.5rem;
    font-size: 1rem;
  }

  .diff-display {
    font-family: monospace;
    white-space: pre-wrap;
    background-color: #f1f5f9;
    padding: 1rem;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    overflow-x: auto;
  }

  .diff-line-added {
    color: #16a34a;
    background-color: #dcfce7;
  }

  .diff-line-removed {
    color: #dc2626;
    background-color: #fee2e2;
  }

  .comparison-error {
    color: #dc2626;
    text-align: center;
    margin: 1rem 0;
  }

  .comparison-loading {
    text-align: center;
    margin: 1rem 0;
    font-style: italic;
    color: #6b7280;
  }

  .compare-button {
    background-color: #4f46e5;
    margin-top: 1rem;
  }

  .compare-button:hover {
    background-color: #4338ca;
  }

  .close-comparison-button {
    background-color: #6b7280;
  }

  .close-comparison-button:hover {
    background-color: #4b5563;
  }

  /* Collapsible section styles */
  .section-header {
    display: flex;
    align-items: center;
    cursor: pointer;
    user-select: none;
    margin-top: 2rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .section-header h2 {
    margin: 0;
    flex-grow: 1;
  }

  .section-header .toggle-icon {
    font-size: 1.2rem;
    transition: transform 0.2s ease;
  }

  .section-header .toggle-icon.collapsed {
    transform: rotate(-90deg);
  }

  .section-content {
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.3s ease;
    max-height: 2000px;
    opacity: 1;
  }

  .section-content.collapsed {
    max-height: 0;
    opacity: 0;
    margin: 0;
    padding: 0;
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
    <button on:click={() => (window.location.hash = '')}>&larr; Back to Home</button>
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

        <tr><th>GitHub</th><td><a href={repo.url} target="_blank">{repo.url}</a></td></tr>
      </tbody>
    </table>

    <div style="text-align: center; margin-top: 1rem;">
      <button on:click={saveMetadata}>💾 Save Tags</button>
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

    <!-- Comments Section (Collapsible) -->
    <div class="section-header" on:click={toggleComments}>
      <h2>💬 Comments</h2>
      <span class="toggle-icon {commentsCollapsed ? 'collapsed' : ''}">▾</span>
    </div>

    <div class="section-content {commentsCollapsed ? 'collapsed' : ''}">
      <!-- Comment form -->
      <div class="comment-form">
        <div class="comment-form-header">
          <label for="comment-author">Your name:</label>
          <input
            type="text"
            id="comment-author"
            bind:value={commentAuthor}
            placeholder="Anonymous"
          />
        </div>

        <textarea
          bind:value={newComment}
          placeholder="Add a comment..."
        ></textarea>

        <div style="text-align: right;">
          <button on:click={addComment} disabled={addingComment}>
            {addingComment ? 'Adding...' : '💬 Add Comment'}
          </button>
        </div>

        {#if commentStatus}
          <p class="comment-status">{commentStatus}</p>
        {/if}
      </div>

      <!-- Comments list -->
      <div class="comments-list">
        {#if repo.comments && repo.comments.length > 0}
          {#each repo.comments as comment}
            <div class="comment">
              <div class="comment-header">
                <span class="comment-author">{comment.author}</span>
                <span class="comment-date">{new Date(comment.created_at).toLocaleString()}</span>
              </div>
              <div class="comment-content">{comment.comment}</div>
            </div>
          {/each}
        {:else}
          <p style="text-align: center;">No comments yet. Be the first to comment!</p>
        {/if}
      </div>
    </div>

    <!-- Version Tracker Section (Collapsible) -->
    <div class="section-header" on:click={toggleVersions}>
      <h2>📈 Version Tracker</h2>
      <span class="toggle-icon {versionsCollapsed ? 'collapsed' : ''}">▾</span>
    </div>

    <div class="section-content {versionsCollapsed ? 'collapsed' : ''}">
      <!-- Version form -->
      <div class="version-form">
        <div class="version-form-row">
          <div class="field">
            <label for="version-number">Version Number:</label>
            <input
              type="text"
              id="version-number"
              bind:value={newVersion}
              placeholder="e.g., 1.0.0"
            />
          </div>
          <div class="field">
            <label for="release-date">Release Date (optional):</label>
            <input
              type="date"
              id="release-date"
              bind:value={versionReleaseDate}
            />
          </div>
        </div>

        <label for="version-description">Description (optional):</label>
        <textarea
          id="version-description"
          bind:value={versionDescription}
          placeholder="What's new in this version?"
        ></textarea>

        <div style="text-align: right;">
          <button on:click={addVersion} disabled={addingVersion}>
            {addingVersion ? 'Adding...' : '📈 Add Version'}
          </button>
        </div>

        {#if versionStatus}
          <p class="version-status">{versionStatus}</p>
        {/if}
      </div>

      <!-- Compare versions button -->
      {#if repo.versions && repo.versions.length > 1}
        <div style="text-align: center; margin-top: 1rem;">
          <button on:click={toggleComparison}>
            {showComparison ? 'Hide Comparison' : 'Compare Versions'}
          </button>
        </div>
      {/if}

      <!-- Version comparison UI -->
      {#if showComparison}
        <div class="comparison-container">
          <div class="comparison-header">
            <h3>Version Comparison</h3>
            <button class="close-comparison-button" on:click={toggleComparison}>Close</button>
          </div>

          <div class="comparison-selectors">
            <div class="comparison-selector">
              <label for="version1-select">First Version:</label>
              <select id="version1-select" bind:value={selectedVersion1}>
                <option value={null}>Select a version</option>
                {#each repo.versions as version}
                  <option value={version.id}>{version.version_number}</option>
                {/each}
              </select>
            </div>

            <div class="comparison-selector">
              <label for="version2-select">Second Version:</label>
              <select id="version2-select" bind:value={selectedVersion2}>
                <option value={null}>Select a version</option>
                {#each repo.versions as version}
                  <option value={version.id}>{version.version_number}</option>
                {/each}
              </select>
            </div>
          </div>

          <div style="text-align: center;">
            <button class="compare-button" on:click={compareVersions} disabled={loadingComparison}>
              {loadingComparison ? 'Comparing...' : 'Compare'}
            </button>
          </div>

          {#if comparisonError}
            <p class="comparison-error">{comparisonError}</p>
          {/if}

          {#if loadingComparison}
            <p class="comparison-loading">Loading comparison...</p>
          {/if}

          {#if comparisonResult}
            <div class="comparison-results">
              <div class="comparison-field">
                <h4>Version Number</h4>
                {#if comparisonResult.differences.version_number.changed}
                  <div class="diff-display" >
                    {@html formatDiff(comparisonResult.differences.version_number.diff)}
                  </div>
                {:else}
                  <p>No changes</p>
                {/if}
              </div>

              <div class="comparison-field">
                <h4>Release Date</h4>
                {#if comparisonResult.differences.release_date.changed}
                  <div class="diff-display">
                    {@html formatDiff(comparisonResult.differences.release_date.diff)}
                  </div>
                {:else}
                  <p>No changes</p>
                {/if}
              </div>

              <div class="comparison-field">
                <h4>Description</h4>
                {#if comparisonResult.differences.description.changed}
                  <div class="diff-display">
                    {@html formatDiff(comparisonResult.differences.description.diff)}
                  </div>
                {:else}
                  <p>No changes</p>
                {/if}
              </div>
            </div>
          {/if}
        </div>
      {/if}

      <!-- Versions list -->
      <div class="versions-list">
        {#if repo.versions && repo.versions.length > 0}
          {#each repo.versions as version}
            <div class="version">
              <div class="version-header">
                <span class="version-number">{version.version_number}</span>
                {#if version.release_date}
                  <span class="version-date">Released: {new Date(version.release_date).toLocaleDateString()}</span>
                {:else}
                  <span class="version-date">Added: {new Date(version.created_at).toLocaleString()}</span>
                {/if}
              </div>
              {#if version.description}
                <div class="version-description">{version.description}</div>
              {/if}
            </div>
          {/each}
        {:else}
          <p style="text-align: center;">No versions tracked yet. Add the first version above!</p>
        {/if}
      </div>
    </div>

    <!-- Recent Commits Section (Collapsible) -->
    <div class="section-header" on:click={toggleCommits}>
      <h2>🕘 Recent Commits</h2>
      <span class="toggle-icon {commitsCollapsed ? 'collapsed' : ''}">▾</span>
    </div>

    <div class="section-content {commitsCollapsed ? 'collapsed' : ''}">
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
    </div>
  {/if}
</div>
