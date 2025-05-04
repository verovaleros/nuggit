<script>
  import { onMount } from 'svelte';
  import TagInput from '../components/TagInput.svelte';

  let repoId = null;
  let repo = null;

  // Initialize repo with empty recent_commits array to avoid errors
  $: if (repo && !repo.recent_commits) {
    repo.recent_commits = [];
  }
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
  // Set today's date as default
  let today = new Date();
  let formattedDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  // Use today's date for version name too
  let newVersion = `v${today.getFullYear()}.${today.getMonth() + 1}.${today.getDate()}`;
  let versionReleaseDate = formattedDate;
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

      // Set a timeout for the fetch operation to handle offline mode gracefully
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      try {
        // Fetch repository details
        const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}`, {
          signal: controller.signal
        });

        clearTimeout(timeoutId); // Clear the timeout if fetch completes

        if (!res.ok) {
          throw new Error(await res.text());
        }

        repo = await res.json();
        tags = repo.tags ? repo.tags.join(',') : '';
        notes = repo.notes || '';

        // Fetch versions using the new API endpoint
        try {
          const versionsRes = await fetch(`http://localhost:8001/api/get-versions?repo_id=${encodedRepoId}`);

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
      } catch (fetchErr) {
        if (fetchErr.name === 'AbortError') {
          error = 'Connection timed out. Loading repository from local database.';
          console.warn('Repository fetch timed out - trying to load from local database');

          // Try again with a longer timeout - this will use the offline mode in the backend
          try {
            const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}`, {
              timeout: 10000 // Longer timeout for offline mode
            });

            if (!res.ok) {
              throw new Error(await res.text());
            }

            repo = await res.json();
            tags = repo.tags ? repo.tags.join(',') : '';
            notes = repo.notes || '';
            error = null; // Clear the error if we successfully loaded from DB
          } catch (offlineErr) {
            error = `Failed to load repository: ${offlineErr.message}`;
            console.error('Failed to load repository in offline mode:', offlineErr);
          }
        } else {
          throw fetchErr;
        }
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

      const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}/fields`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tags, notes }) // Pass both tags and notes
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

      // Set a timeout for the fetch operation
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      try {
        const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}`, {
          method: 'PUT',
          signal: controller.signal
        });

        clearTimeout(timeoutId); // Clear the timeout if fetch completes

        if (!res.ok) {
          throw new Error(await res.text());
        }

        // Parse the response from the update endpoint
        const updateData = await res.json();
        console.log('Update response:', updateData);
      } catch (fetchErr) {
        if (fetchErr.name === 'AbortError') {
          console.warn('Update request timed out - continuing with local data');
        } else {
          throw fetchErr;
        }
      }

      // After update attempt (successful or not), fetch the repository details again
      try {
        // Encode the repository ID for the URL
        const encodedRepoId = encodeURIComponent(repoId);

        const detailRes = await fetch(`http://localhost:8001/repositories/${encodedRepoId}`);

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
          const versionsRes = await fetch(`http://localhost:8001/api/get-versions?repo_id=${encodedRepoId}`);

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

        // Clear the status after 1 second
        setTimeout(() => {
          updateStatus = '';
        }, 1000);
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

      const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}`, {
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

  // State for commit loading
  let loadingCommits = false;
  let commitsError = null;

  async function toggleCommits() {
    commitsCollapsed = !commitsCollapsed;

    // If we're expanding the commits section and there are no commits yet, fetch them
    if (!commitsCollapsed && (!repo.recent_commits || repo.recent_commits.length === 0)) {
      await fetchCommits();
    }
  }

  async function checkRepositoryExists(repoId) {
    try {
      const encodedRepoId = encodeURIComponent(repoId);
      const checkUrl = `http://localhost:8001/repositories/check/${encodedRepoId}`;
      console.log('Checking if repository exists:', checkUrl);

      const res = await fetch(checkUrl);
      if (!res.ok) {
        console.error('Error checking repository:', await res.text());
        return false;
      }

      const data = await res.json();
      return data.exists;
    } catch (err) {
      console.error('Error checking if repository exists:', err);
      return false;
    }
  }

  async function fetchCommits() {
    if (loadingCommits) return; // Prevent multiple simultaneous requests

    loadingCommits = true;
    commitsError = null;

    try {
      // Make sure repoId is properly defined
      if (!repoId) {
        throw new Error("Repository ID is missing");
      }

      console.log('Fetching commits for repository:', repoId);

      // First check if the repository exists in the database
      const exists = await checkRepositoryExists(repoId);
      if (!exists) {
        throw new Error("Repository not found in database");
      }

      const encodedRepoId = encodeURIComponent(repoId);

      // Set a timeout for the fetch operation
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      try {
        // Log the URL we're fetching from - make sure to include trailing slash
        const url = `http://localhost:8001/repositories/${encodedRepoId}/commits/`;
        console.log('Fetching commits from URL:', url);

        const res = await fetch(url, {
          signal: controller.signal
        });

        clearTimeout(timeoutId); // Clear the timeout if fetch completes

        if (!res.ok) {
          const errorText = await res.text();
          console.error('Error response from commits API:', errorText);
          throw new Error(errorText);
        }

        const commits = await res.json();
        repo.recent_commits = commits;
        console.log('Commits fetched successfully:', commits);
      } catch (fetchErr) {
        if (fetchErr.name === 'AbortError') {
          commitsError = 'Failed to load commits: Connection timed out';
          console.warn('Commits fetch timed out');
        } else {
          throw fetchErr;
        }
      }
    } catch (err) {
      commitsError = `Failed to load commits: ${err.message}`;
      console.error('Error fetching commits:', err);
    } finally {
      loadingCommits = false;
    }
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
      console.log(`Using API endpoint: http://localhost:8001/api/compare-versions?repo_id=${encodedRepoId}&version1_id=${selectedVersion1}&version2_id=${selectedVersion2}`);
      const queryRes = await fetch(`http://localhost:8001/api/compare-versions?repo_id=${encodedRepoId}&version1_id=${selectedVersion1}&version2_id=${selectedVersion2}`);

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

  // Format date to human-readable format
  function formatDate(dateString) {
    if (!dateString) return 'N/A';

    try {
      const date = new Date(dateString);

      // Check if date is valid
      if (isNaN(date.getTime())) return dateString;

      // Format options
      const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      };

      return date.toLocaleDateString(undefined, options);
    } catch (error) {
      console.error('Error formatting date:', error);
      return dateString;
    }
  }

  // Format date with days ago
  function formatDateWithDaysAgo(dateString) {
    if (!dateString) return 'N/A';

    try {
      const date = new Date(dateString);

      // Check if date is valid
      if (isNaN(date.getTime())) return dateString;

      // Format the date
      const formattedDate = formatDate(dateString);

      // Calculate days ago
      const now = new Date();
      const diffTime = Math.abs(now - date);
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

      // Return formatted string
      return `${formattedDate} (${diffDays} ${diffDays === 1 ? 'day' : 'days'} ago)`;
    } catch (error) {
      console.error('Error formatting date with days ago:', error);
      return dateString;
    }
  }

  // Format relative time (e.g., "2 days ago")
  function formatRelativeTime(dateString) {
    if (!dateString) return 'N/A';

    try {
      const date = new Date(dateString);

      // Check if date is valid
      if (isNaN(date.getTime())) return dateString;

      const now = new Date();
      const diffMs = now - date;
      const diffSec = Math.floor(diffMs / 1000);
      const diffMin = Math.floor(diffSec / 60);
      const diffHour = Math.floor(diffMin / 60);
      const diffDay = Math.floor(diffHour / 24);
      const diffMonth = Math.floor(diffDay / 30);
      const diffYear = Math.floor(diffDay / 365);

      if (diffSec < 60) return 'just now';
      if (diffMin < 60) return `${diffMin} minute${diffMin === 1 ? '' : 's'} ago`;
      if (diffHour < 24) return `${diffHour} hour${diffHour === 1 ? '' : 's'} ago`;
      if (diffDay < 30) return `${diffDay} day${diffDay === 1 ? '' : 's'} ago`;
      if (diffMonth < 12) return `${diffMonth} month${diffMonth === 1 ? '' : 's'} ago`;
      return `${diffYear} year${diffYear === 1 ? '' : 's'} ago`;
    } catch (error) {
      console.error('Error formatting relative time:', error);
      return dateString;
    }
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

      const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}/versions`, {
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
        const versionsRes = await fetch(`http://localhost:8001/api/get-versions?repo_id=${encodedRepoId}`);

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

      const res = await fetch(`http://localhost:8001/repositories/${encodedRepoId}/comments`, {
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
    max-width: 1200px;
    margin: 2rem auto;
    font-family: sans-serif;
  }

  h1, h2 {
    margin-bottom: 1rem;
  }

  /* Two-column layout */
  .repo-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  @media (max-width: 768px) {
    .repo-grid {
      grid-template-columns: 1fr;
    }
  }

  .info-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
  }

  .info-card h3 {
    margin-top: 0;
    margin-bottom: 1rem;
    color: #1f2937;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.5rem;
  }

  .info-item {
    display: flex;
    padding: 0.75rem;
    border-radius: 4px;
  }

  .info-item:nth-child(odd) {
    background-color: #f9fafb;
  }

  .info-item:nth-child(even) {
    background-color: #ffffff;
  }

  .info-item:hover {
    background-color: #f3f4f6;
  }

  .info-label {
    font-weight: bold;
    width: 40%;
    color: #4b5563;
  }

  .info-value {
    width: 60%;
  }

  .topic-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .topic-pill {
    background-color: #e0f2fe;
    color: #0369a1;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    transition: all 0.2s ease;
  }

  .topic-pill:hover {
    background-color: #bae6fd;
    transform: translateY(-1px);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  .no-topics {
    color: #9ca3af;
    font-style: italic;
  }

  /* Table styles for commits */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
    box-shadow: 0 0 8px rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    overflow: hidden;
  }

  th, td {
    padding: 0.75rem 1rem;
    text-align: left;
    border-bottom: 1px solid #eee;
  }

  th {
    background-color: #1f2937;
    color: white;
  }

  td {
    background-color: #fff;
  }

  tr:nth-child(even) td {
    background-color: #f9fafb;
  }

  tr:hover td {
    background-color: #f3f4f6;
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
    font-weight: 600;
    background-color: #1f2937;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  button:hover {
    background-color: #374151;
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  button:active {
    transform: translateY(0);
  }

  .error {
    color: #dc2626;
    text-align: center;
    padding: 0.75rem;
    background-color: #fee2e2;
    border-radius: 6px;
    margin: 1rem 0;
  }

  .status-message {
    margin-top: 0.5rem;
    text-align: center;
    font-style: italic;
    padding: 0.5rem;
    border-radius: 6px;
    background-color: #f3f4f6;
    transition: opacity 0.3s ease;
  }

  .status-success {
    background-color: #d1fae5;
    color: #065f46;
  }

  .status-error {
    background-color: #fee2e2;
    color: #b91c1c;
  }

  .status-loading {
    background-color: #e0f2fe;
    color: #0369a1;
  }

  .tags-actions-container {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    padding: 1.5rem;
    margin-bottom: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .tags-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .tags-container label {
    font-weight: 600;
    color: #374151;
  }

  /* Tag styles moved to TagInput.svelte component */

  .action-buttons {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-start;
    gap: 0.75rem;
    margin-top: 0.5rem;
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

  .save-button {
    background-color: #059669;
  }

  .save-button:hover {
    background-color: #047857;
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
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }

  .comment {
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #4f46e5;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .comment-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
    color: #6b7280;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.5rem;
  }

  .comment-author {
    font-weight: bold;
    color: #4f46e5;
  }

  .comment-content {
    white-space: pre-wrap;
    word-break: break-word;
    flex-grow: 1;
    font-size: 0.95rem;
    line-height: 1.5;
  }

  .comment-form {
    margin-bottom: 1.5rem;
    background-color: white;
    border-radius: 8px;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    border: 1px solid #e5e7eb;
  }

  .comment-form textarea {
    width: 100%;
    min-height: 100px;
    margin-bottom: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0.75rem;
    font-size: 0.95rem;
    resize: vertical;
  }

  .comment-form-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .comment-form-header input {
    width: 200px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
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
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }

  .version {
    background-color: white;
    border-radius: 8px;
    padding: 1.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #059669;
    height: 100%;
    display: flex;
    flex-direction: column;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .version:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  }

  .version-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
    color: #6b7280;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.75rem;
  }

  .version-number {
    font-weight: bold;
    font-size: 1.1rem;
    color: #059669;
  }

  .version-date {
    font-style: italic;
  }

  .version-description {
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 0.5rem;
    flex-grow: 1;
    font-size: 0.95rem;
    line-height: 1.5;
  }

  .version-form {
    margin-bottom: 1rem;
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .version-form-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .version-form-row input {
    padding: 0.6rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 0.95rem;
    height: 40px;
  }

  .version-form-row input[type="text"]:first-child {
    width: 180px;
  }

  .version-form-row input[type="date"] {
    width: 150px;
  }

  .version-form-row input[type="text"]:nth-child(3) {
    flex: 1;
  }

  @media (max-width: 768px) {
    .version-form-row {
      flex-wrap: wrap;
    }

    .version-form-row input[type="text"]:first-child,
    .version-form-row input[type="date"],
    .version-form-row input[type="text"]:nth-child(3) {
      width: 100%;
    }
  }

  .add-version-button {
    background-color: #059669;
    white-space: nowrap;
    height: 40px;
    padding: 0 1rem;
  }

  .add-version-button:hover {
    background-color: #047857;
  }

  @media (max-width: 768px) {
    .add-version-button {
      width: 100%;
      margin-top: 0.5rem;
    }
  }

  /* Version comparison styles */
  .comparison-container {
    margin-top: 1.5rem;
    background-color: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    border: 1px solid #e5e7eb;
  }

  .comparison-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .comparison-header h3 {
    margin: 0;
    font-size: 1.2rem;
    color: #1f2937;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .comparison-header button {
    padding: 0.4rem 0.8rem;
    font-size: 0.9rem;
  }

  .comparison-selectors {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  @media (max-width: 640px) {
    .comparison-selectors {
      grid-template-columns: 1fr;
    }
  }

  .comparison-selector {
    background-color: #f9fafb;
    padding: 1rem;
    border-radius: 6px;
    border: 1px solid #e5e7eb;
  }

  .comparison-selector label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    font-size: 0.9rem;
    color: #374151;
  }

  .comparison-selector select {
    width: 100%;
    padding: 0.6rem;
    border-radius: 6px;
    border: 1px solid #d1d5db;
    background-color: white;
    font-size: 0.95rem;
  }

  .comparison-results {
    margin-top: 1.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
  }

  .comparison-field {
    background-color: #f9fafb;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .comparison-field h4 {
    margin-top: 0;
    margin-bottom: 0.75rem;
    font-size: 1rem;
    color: #1f2937;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .diff-display {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    white-space: pre-wrap;
    background-color: #f8fafc;
    padding: 1rem;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    overflow-x: auto;
    font-size: 0.9rem;
    line-height: 1.5;
  }

  .diff-line-added {
    color: #16a34a;
    background-color: #dcfce7;
    display: block;
    padding: 0.1rem 0.3rem;
    margin: 0.1rem 0;
    border-radius: 3px;
  }

  .diff-line-removed {
    color: #dc2626;
    background-color: #fee2e2;
    display: block;
    padding: 0.1rem 0.3rem;
    margin: 0.1rem 0;
    border-radius: 3px;
  }

  .comparison-error {
    color: #dc2626;
    text-align: center;
    margin: 1rem 0;
    padding: 0.75rem;
    background-color: #fee2e2;
    border-radius: 6px;
  }

  .comparison-loading {
    text-align: center;
    margin: 1rem 0;
    font-style: italic;
    color: #6b7280;
    padding: 1rem;
    background-color: #f3f4f6;
    border-radius: 6px;
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
    padding: 0.75rem 1rem;
    border-radius: 8px;
    background-color: #f3f4f6;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    transition: background-color 0.2s ease;
  }

  .section-header:hover {
    background-color: #e5e7eb;
  }

  .section-header h2 {
    margin: 0;
    flex-grow: 1;
    font-size: 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .section-header .toggle-icon {
    font-size: 1.2rem;
    transition: transform 0.3s ease;
    color: #4b5563;
  }

  .section-header .toggle-icon.collapsed {
    transform: rotate(-90deg);
  }

  .section-content {
    overflow: hidden;
    transition: max-height 0.4s ease, opacity 0.3s ease, margin 0.3s ease;
    max-height: 2000px;
    opacity: 1;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem;
    padding: 1.5rem;
  }

  .section-content.collapsed {
    max-height: 0;
    opacity: 0;
    margin: 0;
    padding: 0;
    box-shadow: none;
  }

  .nav-back {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    background-color: #f9fafb;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .nav-back button {
    padding: 0.5rem 1rem;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .nav-back button:hover {
    background-color: #e5e7eb;
    transform: translateY(-1px);
  }

  .nav-back .add-repo {
    background-color: #1f2937;
    color: white;
  }

  .nav-back .add-repo:hover {
    background-color: #374151;
  }

  .repo-header {
    display: flex;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .repo-header h1 {
    margin: 0;
    flex-grow: 1;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .repo-stats {
    display: flex;
    gap: 1.5rem;
  }

  .stat-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
    cursor: help;
    padding: 0.5rem 0.75rem;
    background-color: #f9fafb;
    border-radius: 6px;
    transition: all 0.2s ease;
  }

  .stat-item:hover {
    background-color: #f3f4f6;
    transform: translateY(-2px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .stat-value {
    font-weight: bold;
    font-size: 1.1rem;
  }

  .no-license {
    color: #e65100;
    font-weight: bold;
    background-color: #fff3e0;
    padding: 2px 6px;
    border-radius: 4px;
  }

  .loading-commits {
    padding: 1rem;
    text-align: center;
    color: #4b5563;
  }

  .commits-error {
    padding: 1rem;
    text-align: center;
    color: #ef4444;
  }

  .retry-button {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .retry-button:hover {
    background-color: #e5e7eb;
  }
</style>

<div class="container">
  <div class="nav-back">
    <button on:click={() => (window.location.hash = '')}>
      <span>&larr;</span> Back to Home
    </button>
    <button class="add-repo" on:click={() => (window.location.hash = '#/?tab=add')}>
      <span>+</span> Add Repositories
    </button>
  </div>
  {#if loading}
    <div style="text-align: center; padding: 3rem 0;">
      <h1>Loading repository data…</h1>
    </div>
  {:else if error}
    <p class="error">{error}</p>
  {:else if repo}
    <div class="repo-header">
      <h1>📦 {repo.name}</h1>
      <div class="repo-stats">
        <div class="stat-item" title="Total Commits">
          <span>✍️</span>
          <span class="stat-value">{repo.commits}</span>
        </div>
        <div class="stat-item" title="Open Issues">
          <span>🐞</span>
          <span class="stat-value">{repo.issues}</span>
        </div>
        <div class="stat-item" title="Contributors">
          <span>🧑‍🤝‍🧑</span>
          <span class="stat-value">{repo.contributors}</span>
        </div>
        <div class="stat-item" title="GitHub Forks">
          <span>🍴</span>
          <span class="stat-value">{repo.forks}</span>
        </div>
        <div class="stat-item" title="GitHub Stars">
          <span>⭐</span>
          <span class="stat-value">{repo.stars}</span>
        </div>
      </div>
    </div>

    <div class="repo-grid">
      <div class="info-card">
        <h3>Repository Information</h3>
        <div class="info-item">
          <div class="info-label">Description</div>
          <div class="info-value">{repo.description}</div>
        </div>
        <div class="info-item">
          <div class="info-label">GitHub</div>
          <div class="info-value" style="word-break: break-all;">
            <a href={repo.url} target="_blank">{repo.url}</a>
          </div>
        </div>
        <div class="info-item">
          <div class="info-label">License</div>
          <div class="info-value">
            {#if repo.license === 'No license'}
              <span class="no-license">⚠️ {repo.license}</span>
            {:else}
              {repo.license}
            {/if}
          </div>
        </div>
        <div class="info-item">
          <div class="info-label">Topics</div>
          <div class="info-value">
            {#if repo.topics}
              <div class="topic-pills">
                {#each repo.topics.split(',').filter(topic => topic.trim()) as topic}
                  <span class="topic-pill">{topic.trim()}</span>
                {/each}
              </div>
            {:else}
              <span class="no-topics">No topics</span>
            {/if}
          </div>
        </div>
        <div class="info-item">
          <div class="info-label">Last Commit</div>
          <div class="info-value">{formatDateWithDaysAgo(repo.last_commit)}</div>
        </div>
      </div>

      <div class="info-card">
        <h3>Metadata & Actions</h3>
        <div class="info-item">
          <div class="info-label">Full ID</div>
          <div class="info-value" style="word-break: break-all; font-size: 0.9rem;">{repo.id}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Created At</div>
          <div class="info-value">{formatDate(repo.created_at)}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Updated At</div>
          <div class="info-value">{formatDateWithDaysAgo(repo.updated_at)}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Last Synced</div>
          <div class="info-value">{formatDateWithDaysAgo(repo.last_synced)}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Total Comments</div>
          <div class="info-value">{repo.comments ? repo.comments.length : 0}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Total Versions</div>
          <div class="info-value">{repo.versions ? repo.versions.length : 0}</div>
        </div>

      </div>
    </div>

    <div class="tags-actions-container">
      <div class="tags-container">
        <label for="tags-input">Repository Tags:</label>
        <TagInput bind:tags on:change={event => tags = event.detail.tags} />
      </div>

      <div class="action-buttons">
        <button class="save-button" on:click={saveMetadata}>
          <span>💾</span> Save Tags
        </button>
        <button class="update-button" on:click={updateRepository}>
          <span>🔄</span> Update from GitHub
        </button>
        <button class="delete-button" on:click={confirmDelete}>
          <span>🗑️</span> Delete Repository
        </button>
      </div>

      {#if saveStatus}
        <div class="status-message {saveStatus.includes('✅') ? 'status-success' : saveStatus.includes('❌') ? 'status-error' : 'status-loading'}">
          {saveStatus}
        </div>
      {/if}

      {#if updateStatus}
        <div class="status-message {updateStatus.includes('✅') ? 'status-success' : updateStatus.includes('❌') ? 'status-error' : 'status-loading'}">
          {updateStatus}
        </div>
      {/if}
    </div>

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
                <span class="comment-date">{formatRelativeTime(comment.created_at)}</span>
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
          <input
            type="text"
            id="version-number"
            bind:value={newVersion}
            placeholder="Version number"
            title="Version number (e.g., v2023.5.15)"
          />
          <input
            type="date"
            id="release-date"
            bind:value={versionReleaseDate}
            title="Release date"
          />
          <input
            type="text"
            id="version-description"
            bind:value={versionDescription}
            placeholder="Description (optional)"
            title="Brief description of this version"
          />
          <button class="add-version-button" on:click={addVersion} disabled={addingVersion}>
            {addingVersion ? 'Adding...' : '📈 Add'}
          </button>
        </div>

        {#if versionStatus}
          <div class="status-message {versionStatus.includes('✅') ? 'status-success' : versionStatus.includes('❌') ? 'status-error' : 'status-loading'}">
            {versionStatus}
          </div>
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

              <!-- New repository fields -->
              <div class="comparison-field">
                <h4>License</h4>
                {#if comparisonResult.differences.license && comparisonResult.differences.license.changed}
                  <div class="diff-display">
                    {@html formatDiff(comparisonResult.differences.license.diff)}
                  </div>
                {:else}
                  <p>No changes</p>
                {/if}
              </div>

              <div class="comparison-field">
                <h4>Stars</h4>
                {#if comparisonResult.differences.stars && comparisonResult.differences.stars.changed}
                  <div class="diff-display">
                    {@html formatDiff(comparisonResult.differences.stars.diff)}
                  </div>
                {:else}
                  <p>No changes</p>
                {/if}
              </div>

              <div class="comparison-field">
                <h4>Topics</h4>
                {#if comparisonResult.differences.topics && comparisonResult.differences.topics.changed}
                  <div class="diff-display">
                    {@html formatDiff(comparisonResult.differences.topics.diff)}
                  </div>
                {:else}
                  <p>No changes</p>
                {/if}
              </div>

              <div class="comparison-field">
                <h4>Total Commits</h4>
                {#if comparisonResult.differences.commits && comparisonResult.differences.commits.changed}
                  <div class="diff-display">
                    {@html formatDiff(comparisonResult.differences.commits.diff)}
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
                  <span class="version-date">Released: {formatDate(version.release_date)}</span>
                {:else}
                  <span class="version-date">Added: {formatRelativeTime(version.created_at)}</span>
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
      {#if loadingCommits}
        <div class="loading-commits">
          <p style="text-align: center;">Loading commits from GitHub...</p>
        </div>
      {:else if commitsError}
        <div class="commits-error">
          <p style="text-align: center;">{commitsError}</p>
          <div style="text-align: center; margin-top: 1rem;">
            <button on:click={fetchCommits} class="retry-button">Retry</button>
          </div>
        </div>
      {:else if repo.recent_commits && repo.recent_commits.length > 0}
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>SHA</th>
              <th>Author</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {#each repo.recent_commits as commit}
              <tr>
                <td>{formatDateWithDaysAgo(commit.date)}</td>
                <td>{commit.sha}</td>
                <td>{commit.author}</td>
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
