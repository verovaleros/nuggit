<script>
  import { onMount, onDestroy } from 'svelte';
  import TagInput from '../components/TagInput.svelte';
  import ErrorBoundary from '../components/ErrorBoundary.svelte';
  import {
    formatDateTime,
    formatRelativeTime,
    formatDateTimeWithRelative,
    formatCompactDate,
    isValidDate
  } from '../lib/timezone.js';

  let currentTab = 'repos';

  function parseHashTab() {
    const params = new URLSearchParams(window.location.hash.split('?')[1]);
    currentTab = params.get('tab') || 'repos';
  }

  onMount(() => {
    parseHashTab();
    window.addEventListener('hashchange', parseHashTab);
  });

  onDestroy(() => {
    window.removeEventListener('hashchange', parseHashTab);
  });

  function switchTab(tab) {
    currentTab = tab;
  }

  let allRepos = [];
  let filteredRepos = [];
  let pageSize = 5; // Smaller page size to make pagination more visible
  let currentDisplayCount = pageSize;
  let searchTerm = '';

  // Sorting options
  let sortField = 'last_commit'; // Default sort by last_commit (most recent first)
  let sortOrder = 'desc'; // Default sort order is descending

  // Repository adding
  let repoIds = '';
  let addStatus = '';
  let isAdding = false;
  let addResults = null;
  let processingRepos = [];
  let sharedTags = ''; // Tags to apply to all repositories in batch

  // Version information for troubleshooting
  let versionInfo = null;

  // Tags and stats
  $: allTags = Array.from(
    new Set(
      allRepos.flatMap(repo =>
        (repo.tags || '').split(',').map(tag => tag.trim()).filter(Boolean)
      )
    )
  ).sort();

  $: stats = {
    totalRepos: allRepos.length,
    totalStars: allRepos.reduce((sum, r) => sum + (r.stars || 0), 0),
    totalContributors: allRepos.reduce((sum, r) => sum + parseInt(r.contributors || 0), 0),
    mostCommonLicense: (() => {
      const counts = {};
      for (const repo of allRepos) {
        const lic = repo.license || 'Unknown';
        counts[lic] = (counts[lic] || 0) + 1;
      }
      return Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A';
    })()
  };

  onMount(async () => {
    try {
      console.log('Fetching repositories...');
      const res = await fetch('http://localhost:8001/repositories/');
      const data = await res.json();
      allRepos = data.repositories;
      console.log('Total repositories loaded:', allRepos.length);

      // Initialize filteredRepos with all repositories, properly sorted
      filteredRepos = sortRepositories([...allRepos]);
      console.log('Initial filteredRepos length:', filteredRepos.length, 'sorted by', sortField, sortOrder);

      // Initialize to show the first page
      currentDisplayCount = pageSize;
    } catch (error) {
      console.error('Error loading repositories:', error);
    }

    // Fetch version information for troubleshooting
    try {
      const versionRes = await fetch('http://localhost:8001/version');
      versionInfo = await versionRes.json();
    } catch (error) {
      console.error('Error loading version info:', error);
      versionInfo = { api_version: 'unknown', git_commit: 'unknown', app_name: 'Nuggit' };
    }
  });

  function goToDetail(id) {
    const encodedId = btoa(id);
    window.location.hash = `#/repo/${encodedId}`;
  }

  function matchesSearch(repo) {
    // If search term is empty, return all repositories
    if (!searchTerm || searchTerm.trim() === '') {
      return true;
    }

    const lower = searchTerm.toLowerCase().trim();

    // Check each field with proper null handling
    const nameMatch = repo.name ? repo.name.toLowerCase().includes(lower) : false;
    const descMatch = repo.description ? repo.description.toLowerCase().includes(lower) : false;
    const idMatch = repo.id ? repo.id.toLowerCase().includes(lower) : false;
    const tagsMatch = repo.tags ? repo.tags.toLowerCase().includes(lower) : false;
    const licenseMatch = repo.license ? repo.license.toLowerCase().includes(lower) : false;

    return nameMatch || descMatch || idMatch || tagsMatch || licenseMatch;
  }

  function sortRepositories(repos) {
    // Create a copy of the array to avoid modifying the original
    const sortedRepos = [...repos];

    // Sort the repositories based on the selected field and order
    sortedRepos.sort((a, b) => {
      let valueA = a[sortField];
      let valueB = b[sortField];

      // Handle null or undefined values
      if (valueA === null || valueA === undefined) valueA = '';
      if (valueB === null || valueB === undefined) valueB = '';

      // Convert to lowercase strings for string comparison
      if (typeof valueA === 'string') valueA = valueA.toLowerCase();
      if (typeof valueB === 'string') valueB = valueB.toLowerCase();

      // For numeric fields, convert to numbers
      if (sortField === 'stars' || sortField === 'forks' || sortField === 'issues' || sortField === 'commits') {
        valueA = Number(valueA) || 0;
        valueB = Number(valueB) || 0;
      }

      // Compare based on sort order
      if (sortOrder === 'asc') {
        return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
      } else {
        return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
      }
    });

    return sortedRepos;
  }

  function loadNextPage() {
    // Simply increase the number of repositories to display
    currentDisplayCount += pageSize;
    console.log(`Now showing up to ${currentDisplayCount} repositories`);
  }

  // Combined reactive statement to handle search and sort changes
  // This prevents race conditions between multiple reactive statements
  $: if (allRepos && searchTerm !== undefined && sortField && sortOrder) {
    console.log('Updating filtered repositories - search:', searchTerm, 'sort:', sortField, sortOrder);

    // Reset to show only the first page when search or sort changes
    currentDisplayCount = pageSize;

    // Filter and sort repositories
    const filtered = allRepos.filter(matchesSearch);
    filteredRepos = sortRepositories(filtered);

    console.log(`Showing ${filteredRepos.length} repositories, sorted by ${sortField} (${sortOrder})`);
  }

  // This reactive statement has been moved above

  function filterByTag(tag) {
    searchTerm = tag;
    currentTab = 'repos';
  }

  function changeSort(field) {
    console.log(`Changing sort to field: ${field} (current: ${sortField}, ${sortOrder})`);

    // If clicking on the same field, toggle the sort order
    if (field === sortField) {
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
      console.log(`Toggled sort order to: ${sortOrder}`);
    } else {
      // If clicking on a different field, set it as the new sort field
      // and reset the sort order based on the field type
      sortField = field;

      // For date fields and numeric fields, default to descending (newest/highest first)
      if (field === 'last_synced' || field === 'created_at' || field === 'updated_at' ||
          field === 'stars' || field === 'forks' || field === 'issues' || field === 'commits') {
        sortOrder = 'desc';
      } else {
        // For text fields, default to ascending (A-Z)
        sortOrder = 'asc';
      }
      console.log(`Set sort order to: ${sortOrder} for field: ${field}`);
    }

    // Force update of filteredRepos
    filteredRepos = sortRepositories(allRepos.filter(matchesSearch));
  }

  function formatDate(dateString) {
    return formatDateTime(dateString, { includeTime: true, includeTimezone: false });
  }

  // Format date with relative time
  function formatDateWithDaysAgo(dateString) {
    return formatDateTimeWithRelative(dateString, { includeTime: true, includeTimezone: false });
  }

  // Helper function to determine if a string is a GitHub URL
  function isGitHubUrl(str) {
    return str.startsWith('http') && str.includes('github.com/');
  }

  // Helper function to process repositories one by one with progressive feedback
  async function processRepositories(repos) {
    const results = { successful: [], failed: [] };

    for (let i = 0; i < repos.length; i++) {
      const repoInput = repos[i];

      // Update the status to show we're processing this repository
      processingRepos = processingRepos.map((repo, index) =>
        index === i
          ? { ...repo, status: 'processing', message: '🔄' }
          : repo
      );

      try {
        // Determine if this is a URL or username/repo format
        const isUrl = isGitHubUrl(repoInput);

        // Prepare the request payload
        let payload;
        if (isUrl) {
          payload = { url: repoInput };
        } else {
          payload = { id: repoInput };
        }

        console.log(`Processing repository: ${repoInput} (${isUrl ? 'URL' : 'ID'})`);

        // First try the single repository endpoint
        try {
          const singleRes = await fetch('http://localhost:8001/repositories/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

          if (singleRes.ok) {
            const data = await singleRes.json();

            // Update the processing status for this repository
            processingRepos = processingRepos.map((repo, index) =>
              index === i
                ? {
                    ...repo,
                    status: 'success',
                    message: '✅',
                    name: data.repository.name,
                    id: data.repository.id
                  }
                : repo
            );

            // Add to successful results
            results.successful.push({
              id: data.repository.id,
              name: data.repository.name
            });

            continue; // Skip to the next repository
          }

          // If single endpoint fails, fall back to batch endpoint
          console.log(`Single endpoint failed for ${repoInput}, trying batch endpoint`);
        } catch (singleErr) {
          console.error(`Error with single endpoint for ${repoInput}:`, singleErr);
          // Continue to batch endpoint
        }

        // Fall back to the batch endpoint
        const batchRes = await fetch('http://localhost:8001/repositories/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repositories: [repoInput] })
        });

        if (!batchRes.ok) {
          const errText = await batchRes.text();
          throw new Error(errText);
        }

        const batchData = await batchRes.json();

        // Check if the repository was added successfully
        if (batchData.results.successful.length > 0) {
          const successfulRepo = batchData.results.successful[0];

          // Update the processing status for this repository
          processingRepos = processingRepos.map((repo, index) =>
            index === i
              ? {
                  ...repo,
                  status: 'success',
                  message: '✅',
                  name: successfulRepo.name,
                  id: successfulRepo.id // Update with the canonical ID
                }
              : repo
          );

          // Add to successful results
          results.successful.push({
            id: successfulRepo.id,
            name: successfulRepo.name
          });
        } else if (batchData.results.failed.length > 0) {
          const failedRepo = batchData.results.failed[0];
          throw new Error(failedRepo.error);
        } else {
          throw new Error("Unknown error occurred");
        }

      } catch (err) {
        console.error(`Error processing repository ${repoInput}:`, err);

        // Update the processing status for this repository
        processingRepos = processingRepos.map((repo, index) =>
          index === i
            ? { ...repo, status: 'error', message: '❌', errorDetails: err.message }
            : repo
        );

        // Add to failed results
        results.failed.push({
          id: repoInput,
          error: err.message
        });
      }
    }

    return results;
  }

  // Helper function to process repositories using batch endpoint with shared tags
  async function processBatchWithTags(repos, tags) {
    const results = { successful: [], failed: [] };

    // Update all repos to processing status
    processingRepos = processingRepos.map(repo => ({
      ...repo,
      status: 'processing',
      message: '🔄'
    }));

    try {
      // Try batch endpoint first
      const batchRes = await fetch('http://localhost:8001/repositories/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repositories: repos,
          tags: tags
        })
      });

      if (batchRes.ok) {
        const batchData = await batchRes.json();

        // Update processing status based on results
        processingRepos = processingRepos.map((repo, index) => {
          const successful = batchData.results.successful.find(s => s.id === repo.id || repos[index] === repo.id);
          const failed = batchData.results.failed.find(f => f.id === repo.id || repos[index] === repo.id);

          if (successful) {
            return {
              ...repo,
              status: 'success',
              message: '✅',
              name: successful.name || repo.id
            };
          } else if (failed) {
            return {
              ...repo,
              status: 'error',
              message: '❌',
              errorDetails: failed.error
            };
          } else {
            return repo;
          }
        });

        return batchData.results;
      } else {
        // If batch endpoint fails, fall back to individual processing with tag application
        console.log('Batch endpoint failed, falling back to individual processing with tags');
        return await processRepositoriesWithTags(repos, tags);
      }
    } catch (error) {
      console.log('Batch endpoint error, falling back to individual processing with tags:', error);
      return await processRepositoriesWithTags(repos, tags);
    }
  }

  // Helper function to process repositories individually and then apply tags
  async function processRepositoriesWithTags(repos, tags) {
    const results = { successful: [], failed: [] };

    for (let i = 0; i < repos.length; i++) {
      const repoInput = repos[i];

      // Update the status to show we're processing this repository
      processingRepos = processingRepos.map((repo, index) =>
        index === i
          ? { ...repo, status: 'processing', message: '🔄' }
          : repo
      );

      try {
        // Determine if this is a URL or username/repo format
        const isUrl = isGitHubUrl(repoInput);

        // Prepare the request payload
        let payload;
        if (isUrl) {
          payload = { url: repoInput };
        } else {
          payload = { id: repoInput };
        }

        console.log(`Processing repository: ${repoInput} (${isUrl ? 'URL' : 'ID'})`);

        // Add the repository first
        const singleRes = await fetch('http://localhost:8001/repositories/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (singleRes.ok) {
          const data = await singleRes.json();
          const repoId = data.repository.id;

          // Now apply the tags if provided
          if (tags) {
            try {
              const tagRes = await fetch(`http://localhost:8001/repositories/${encodeURIComponent(repoId)}/metadata/`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  tags: tags,
                  notes: data.repository.notes || ''
                })
              });

              if (!tagRes.ok) {
                console.warn(`Failed to apply tags to ${repoId}`);
              }
            } catch (tagError) {
              console.warn(`Error applying tags to ${repoId}:`, tagError);
            }
          }

          // Update the processing status for this repository
          processingRepos = processingRepos.map((repo, index) =>
            index === i
              ? {
                  ...repo,
                  status: 'success',
                  message: '✅',
                  name: data.repository.name,
                  id: data.repository.id
                }
              : repo
          );

          // Add to successful results
          results.successful.push({
            id: data.repository.id,
            name: data.repository.name
          });
        } else {
          throw new Error(`Failed to add repository: ${await singleRes.text()}`);
        }
      } catch (error) {
        // Update the processing status for this repository
        processingRepos = processingRepos.map((repo, index) =>
          index === i
            ? {
                ...repo,
                status: 'error',
                message: '❌',
                errorDetails: error.message
              }
            : repo
        );

        // Add to failed results
        results.failed.push({
          id: repoInput,
          error: error.message
        });
      }
    }

    return results;
  }

  async function addRepositories() {
    if (!repoIds.trim()) {
      addStatus = 'Please enter at least one repository ID.';
      return;
    }

    // Parse the input into an array of repository IDs or URLs
    const repos = repoIds
      .split('\n')
      .map(id => id.trim())
      .filter(id => id.length > 0);

    if (repos.length === 0) {
      addStatus = 'Please enter at least one valid repository ID or URL.';
      return;
    }

    isAdding = true;
    addStatus = 'Adding repositories...';
    addResults = null;

    // Initialize progress tracking for each repository
    processingRepos = repos.map(id => ({
      id,
      status: 'pending', // pending, processing, success, error
      message: '⏳',
      name: ''
    }));

    // For a single repository, we'll redirect to its detail page after adding
    const isSingleRepo = repos.length === 1;
    let singleRepoId = isSingleRepo ? repos[0] : null;

    try {
      // Update UI to show we're starting
      addStatus = `Processing ${repos.length} repositories...`;

      let results;

      // If shared tags are provided, use the batch endpoint directly
      if (sharedTags.trim()) {
        results = await processBatchWithTags(repos, sharedTags.trim());
      } else {
        // Process repositories one by one with progressive feedback
        results = await processRepositories(repos);
      }

      // Create a results object similar to what the batch API returns
      addResults = {
        message: `Batch import: ${results.successful.length} succeeded, ${results.failed.length} failed.`,
        results: results
      };

      addStatus = addResults.message;

      // If all repositories were added successfully, clear the inputs
      if (results.failed.length === 0) {
        repoIds = '';
        sharedTags = '';
      }

      // Refresh the repository list
      const reposData = await fetch('http://localhost:8001/repositories/').then(r => r.json());
      allRepos = reposData.repositories;
      // Update filteredRepos based on current search term and sort settings
      filteredRepos = sortRepositories(allRepos.filter(matchesSearch));

      // If it was a single repository and it was added successfully, redirect to its detail page
      if (isSingleRepo && results.successful.length > 0) {
        const successfulRepo = results.successful[0];
        const encoded = btoa(successfulRepo.id);
        window.location.hash = `#/repo/${encoded}`;
      }
    } catch (err) {
      console.error(err);
      addStatus = `❌ Error: ${err.message}`;

      // Mark all repositories as failed due to the overall error
      processingRepos = processingRepos.map(repo => ({
        ...repo,
        status: 'error',
        message: '❌',
        errorDetails: err.message
      }));
    } finally {
      isAdding = false;
    }
  }
</script>

<style>
  .container {
    max-width: 960px;
    margin: 2rem auto;
    font-family: sans-serif;
  }

  h1 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 1.5rem;
  }

  nav.tabs {
    display: flex;
    justify-content: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  nav.tabs button {
    padding: 0.6rem 1.2rem;
    font-size: 1rem;
    font-weight: bold;
    background-color: #e5e7eb;
    border: none;
    border-radius: 8px;
    cursor: pointer;
  }

  nav.tabs button.active {
    background-color: #1f2937;
    color: white;
  }

  .search-bar {
    position: relative;
    width: 100%;
    margin-bottom: 1rem;
  }

  .search-bar input {
    width: 97%;
    padding: 0.8rem;
    font-size: 1rem;
    border-radius: 6px;
    border: 1px solid #ccc;
  }

  .clear-btn {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    background-color: #e5e7eb;
    border: none;
    border-radius: 4px;
    padding: 0.3rem 0.8rem;
    font-size: 0.9rem;
    font-weight: bold;
    color: #1f2937;
    cursor: pointer;
  }

  .clear-btn:hover {
    background-color: #d1d5db;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    box-shadow: 0 0 8px rgba(0, 0, 0, 0.1);
  }

  th {
    background-color: #1f2937;
    color: white;
    padding: 1rem;
    text-align: left;
    cursor: pointer;
    user-select: none;
    position: relative;
  }

  th:hover {
    background-color: #374151;
  }

  th.sorted:after {
    content: '';
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
  }

  th.sorted.asc:after {
    border-bottom: 5px solid white;
  }

  th.sorted.desc:after {
    border-top: 5px solid white;
  }

  td {
    padding: 1rem;
    border-bottom: 1px solid #eee;
  }

  tr:hover {
    background-color: #f3f4f6;
    cursor: pointer;
  }

  button.load-more {
    margin-top: 1rem;
    padding: 0.6rem 1.2rem;
    font-weight: bold;
    background-color: #1f2937;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
  }

  button.load-more:hover {
    background-color: #374151;
  }

  .center {
    text-align: center;
  }

  .tag-grid {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 1rem;
  }

  .tag-btn {
    background-color: #dbeafe; /* Light blue background */
    color: #1e40af; /* Dark blue text for contrast */
    border: none;
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    font-size: 0.9rem;
    font-family: monospace;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .tag-btn:hover {
    background-color: #bfdbfe; /* Slightly darker blue on hover */
  }

  .stat-block {
    background: #f9fafb;
    padding: 1rem 1.5rem;
    border-radius: 10px;
    box-shadow: 0 0 4px rgba(0,0,0,0.05);
    text-align: center;
    font-size: 1.1rem;
    margin: 1rem;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem;
    margin-top: 2rem;
  }

  .add-repo-button {
    margin-top: 1rem;
    padding: 0.6rem 1.2rem;
    font-weight: bold;
    background-color: #1f2937;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 1rem;
  }

  .add-repo-button:hover {
    background-color: #374151;
  }

  .batch-textarea {
    width: 100%;
    max-width: 500px;
    height: 150px;
    margin-top: 1rem;
    padding: 0.8rem;
    font-size: 1rem;
    font-family: monospace;
    border-radius: 6px;
    border: 1px solid #ccc;
    resize: vertical;
  }

  .shared-tags-section {
    margin-top: 1rem;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
  }

  .shared-tags-section label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #374151;
  }

  .batch-results {
    margin-top: 1.5rem;
    text-align: left;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
  }

  .batch-results h3 {
    margin-bottom: 0.5rem;
  }

  .success-list, .failed-list {
    margin-top: 0.5rem;
    padding: 1rem;
    border-radius: 6px;
    font-family: monospace;
    font-size: 0.9rem;
  }

  .success-list {
    background-color: #ecfdf5;
    border: 1px solid #10b981;
  }

  .failed-list {
    background-color: #fef2f2;
    border: 1px solid #ef4444;
  }

  .repo-item {
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(0,0,0,0.1);
  }

  .repo-item:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: none;
  }

  .error-message {
    color: #ef4444;
    font-style: italic;
  }

  .tabs-content {
    animation: fadeIn 0.3s ease-in-out;
  }

  .repo-progress {
    margin-top: 1.5rem;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
    text-align: left;
  }

  .repo-progress-item {
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    border-radius: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.3s ease;
  }

  .repo-progress-item.status-pending {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
  }

  .repo-progress-item.status-processing {
    background-color: #eff6ff;
    border: 1px solid #93c5fd;
  }

  .repo-progress-item.status-success {
    background-color: #ecfdf5;
    border: 1px solid #10b981;
  }

  .repo-progress-item.status-error {
    background-color: #fef2f2;
    border: 1px solid #ef4444;
  }

  .repo-id {
    font-weight: bold;
    font-family: monospace;
  }

  .repo-status {
    font-size: 0.9rem;
  }

  .results-summary {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 1.5rem;
  }

  .summary-item {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .summary-count {
    font-size: 2rem;
    font-weight: bold;
    margin-bottom: 0.25rem;
  }

  .summary-count.success {
    color: #10b981;
  }

  .summary-count.failed {
    color: #ef4444;
  }

  .summary-label {
    font-size: 0.9rem;
    color: #6b7280;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  /* Version Footer Styles */
  .version-footer {
    margin-top: 3rem;
    padding: 1rem 0;
    border-top: 1px solid #e5e7eb;
    text-align: center;
  }

  .version-info {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #6b7280;
  }

  .app-name {
    font-weight: 600;
    color: #374151;
  }

  .version-details {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    background-color: #f3f4f6;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  @media (max-width: 768px) {
    .version-info {
      flex-direction: column;
      gap: 0.25rem;
    }
  }
</style>

<ErrorBoundary>
  <div class="container">
    <h1>🧠 Nuggit Dashboard</h1>

  <nav class="tabs">
    <button class:active={currentTab === 'repos'} on:click={() => switchTab('repos')}>🧠 Repos</button>
    <button class:active={currentTab === 'tags'} on:click={() => switchTab('tags')}>🏷️ Tags</button>
    <button class:active={currentTab === 'stats'} on:click={() => switchTab('stats')}>📊 Stats</button>
    <button class:active={currentTab === 'add'} on:click={() => switchTab('add')}>➕ Add Repo</button>
  </nav>

  {#if currentTab === 'repos'}
    <div class="search-bar">
      <input
        type="text"
        placeholder="🔍 Search repositories..."
        bind:value={searchTerm}
      />
      {#if searchTerm}
        <button class="clear-btn" on:click={() => (searchTerm = '')}>Clear</button>
      {/if}
    </div>

    <!-- Get filtered repositories based on search term -->
    {#if allRepos.length === 0}
      <p class="center">Loading repositories...</p>
    {:else}
      {#key currentDisplayCount + searchTerm + sortField + sortOrder}
        <table>
          <thead>
            <tr>
              <th class={sortField === 'name' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('name')}>Name</th>
              <th class={sortField === 'description' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('description')}>Description</th>
              <th class={sortField === 'license' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('license')}>License</th>
              <th class={sortField === 'stars' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('stars')}>Stars</th>
              <th class={sortField === 'last_commit' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('last_commit')}>Last Commit</th>
              <th class={sortField === 'last_synced' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('last_synced')}>Last Updated</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredRepos.slice(0, currentDisplayCount) as repo (repo.id)}
              <tr on:click={() => goToDetail(repo.id)}>
                <td>{repo.name}</td>
                <td>{repo.description}</td>
                <td>{repo.license}</td>
                <td>{repo.stars}</td>
                <td>{formatDateWithDaysAgo(repo.last_commit)}</td>
                <td>{formatDateWithDaysAgo(repo.last_synced)}</td>
              </tr>
            {/each}
          </tbody>
        </table>

        <div class="center">
          {#if currentDisplayCount < filteredRepos.length}
            <button class="load-more" on:click={loadNextPage}>Load more</button>
          {/if}

          <div style="margin-top: 1rem; font-size: 0.8rem; color: #666;">
            Showing {Math.min(currentDisplayCount, filteredRepos.length)} of {filteredRepos.length} repositories
          </div>
        </div>
      {/key}
    {/if}

  {:else if currentTab === 'tags'}
    <div class="center">
      <h2>🏷️ All Tags</h2>
      {#if allTags.length === 0}
        <p>No tags available.</p>
      {:else}
        <div class="tag-grid">
          {#each allTags as tag}
            <button class="tag-btn" on:click={() => filterByTag(tag)}>{tag}</button>
          {/each}
        </div>
      {/if}
    </div>

  {:else if currentTab === 'stats'}
    <div class="center">
      <h2>📊 Repository Stats</h2>
      <div class="stats-grid">
        <div class="stat-block"><strong>{stats.totalRepos}</strong><br />Total Repositories</div>
        <div class="stat-block"><strong>{stats.totalStars}</strong><br />Total Stars</div>
        <div class="stat-block"><strong>{stats.totalContributors}</strong><br />Contributors</div>
        <div class="stat-block"><strong>{stats.mostCommonLicense}</strong><br />Most Common License</div>
      </div>
    </div>

  {:else if currentTab === 'add'}
    <div class="center tabs-content">
      <h2>➕ Add Repositories</h2>

      <!-- Repository Add Section -->
      <div>
        <p>Enter one or more repositories (one per line):</p>
        <p><small>Accepted formats: <code>username/repo</code> or <code>https://github.com/username/repo</code></small></p>
        <textarea
          class="batch-textarea"
          placeholder="username1/repo1
https://github.com/username2/repo2
username3/repo3"
          bind:value={repoIds}
        ></textarea>

        <!-- Shared Tags Section -->
        <div class="shared-tags-section">
          <label for="shared-tags">Tags to apply to all repositories (optional):</label>
          <TagInput bind:tags={sharedTags} />
        </div>

        <div style="margin-top: 1rem;">
          <button class="add-repo-button" on:click={addRepositories} disabled={isAdding}>
            {isAdding ? 'Adding...' : 'Add Repositories'}
          </button>
        </div>
        {#if addStatus}
          <p style="margin-top: 1rem;">{addStatus}</p>
        {/if}

        <!-- Processing Status -->
        {#if processingRepos.length > 0}
          <div class="repo-progress">
            {#each processingRepos as repo}
              <div class="repo-progress-item status-{repo.status}">
                <div class="repo-id">{repo.id}</div>
                <div class="repo-status">
                  {#if repo.status === 'pending'}
                    ⏳
                  {:else if repo.status === 'processing'}
                    🔄
                  {:else if repo.status === 'success'}
                    {repo.message}
                  {:else if repo.status === 'error'}
                    <span title="{repo.errorDetails}">{repo.message}</span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}

        <!-- Final Results Summary -->
        {#if addResults}
          <div class="batch-results">
            <div class="results-summary">
              <div class="summary-item">
                <span class="summary-count success">{addResults.results.successful.length}</span>
                <span class="summary-label">Successful</span>
              </div>
              <div class="summary-item">
                <span class="summary-count failed">{addResults.results.failed.length}</span>
                <span class="summary-label">Failed</span>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Version Footer for Troubleshooting -->
  {#if versionInfo}
    <footer class="version-footer">
      <div class="version-info">
        <span class="app-name">{versionInfo.app_name}</span>
        <span class="version-details">
          v{versionInfo.api_version}
          {#if versionInfo.git_commit !== 'unknown'}
            • {versionInfo.git_commit}
          {/if}
        </span>
      </div>
    </footer>
  {/if}
  </div>
</ErrorBoundary>
