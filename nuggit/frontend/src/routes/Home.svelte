<script>
  import { onMount } from 'svelte';

  let currentTab = 'repos';

  function parseHashTab() {
    const params = new URLSearchParams(window.location.hash.split('?')[1]);
    currentTab = params.get('tab') || 'repos';
  }

  onMount(() => {
    parseHashTab();
    window.addEventListener('hashchange', parseHashTab);
  });

  function switchTab(tab) {
    currentTab = tab;
  }

  let allRepos = [];
  let filteredRepos = [];
  let pageSize = 10; // Smaller page size to make pagination more visible
  let currentDisplayCount = pageSize;
  let searchTerm = '';

  // Sorting options
  let sortField = 'last_synced'; // Default sort by last_synced (most recent first)
  let sortOrder = 'desc'; // Default sort order is descending

  // New repo
  let newRepoId = '';
  let addStatus = '';
  let isAdding = false;

  // Batch add repos
  let batchRepoIds = '';
  let batchAddStatus = '';
  let isBatchAdding = false;
  let batchResults = null;

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
      const res = await fetch('http://localhost:8000/repositories/');
      const data = await res.json();
      allRepos = data.repositories;
      console.log('Total repositories loaded:', allRepos.length);

      // Initialize filteredRepos with all repositories
      filteredRepos = [...allRepos];
      console.log('Initial filteredRepos length:', filteredRepos.length);

      // Initialize to show the first page
      currentDisplayCount = pageSize;
    } catch (error) {
      console.error('Error loading repositories:', error);
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

    return nameMatch || descMatch || idMatch || tagsMatch;
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

  // Calculate filtered and sorted repositories
  $: filteredRepos = sortRepositories(allRepos.filter(matchesSearch));

  // Log when filtered repos change
  $: console.log(`Showing ${filteredRepos.length} repositories, sorted by ${sortField} (${sortOrder})`);

  // Make sure the reactive statement is triggered when searchTerm changes
  $: searchTerm, recalculateFiltered();

  function recalculateFiltered() {
    console.log('Search term changed to:', searchTerm);
    filteredRepos = sortRepositories(allRepos.filter(matchesSearch));
  }

  // Reset display count when search term changes
  $: if (searchTerm !== undefined) {
    console.log('Search term changed to:', searchTerm);
    // Reset to show only the first page when search changes
    currentDisplayCount = pageSize;
  }

  // Re-sort when sort options change
  $: if (sortField || sortOrder) {
    // The reactive statement above will handle the actual sorting
    // This is just to ensure the statement runs when sort options change
    console.log(`Sort options changed: ${sortField} (${sortOrder})`);
  }

  function filterByTag(tag) {
    searchTerm = tag;
    currentTab = 'repos';
  }

  function changeSort(field) {
    // If clicking on the same field, toggle the sort order
    if (field === sortField) {
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
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
    }
  }

  function formatDate(dateString) {
    if (!dateString) return 'N/A';

    try {
      const date = new Date(dateString);

      // Check if the date is valid
      if (isNaN(date.getTime())) return 'Invalid date';

      // Format the date as a readable string
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      console.error('Error formatting date:', error);
      return dateString; // Return the original string if there's an error
    }
  }

  async function addRepo() {
    if (!newRepoId.trim()) {
      addStatus = 'Please enter a valid repository ID.';
      return;
    }

    isAdding = true;
    addStatus = '';
    const repo_id = newRepoId.trim();

    try {
      const res = await fetch('http://localhost:8000/repositories/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: repo_id })
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }

      addStatus = '✅ Repository added!';
      newRepoId = '';

      const data = await fetch('http://localhost:8000/repositories/').then(r => r.json());
      allRepos = data.repositories;
      // Update filteredRepos based on current search term
      filteredRepos = allRepos.filter(matchesSearch);

      const encoded = btoa(repo_id);
      window.location.hash = `#/repo/${encoded}`;
    } catch (err) {
      console.error(err);
      addStatus = `❌ Error: ${err.message}`;
    } finally {
      isAdding = false;
    }
  }

  async function addBatchRepos() {
    if (!batchRepoIds.trim()) {
      batchAddStatus = 'Please enter at least one repository ID.';
      return;
    }

    // Parse the input into an array of repository IDs
    const repoIds = batchRepoIds
      .split('\n')
      .map(id => id.trim())
      .filter(id => id.length > 0);

    if (repoIds.length === 0) {
      batchAddStatus = 'Please enter at least one valid repository ID.';
      return;
    }

    isBatchAdding = true;
    batchAddStatus = 'Adding repositories...';
    batchResults = null;

    try {
      const res = await fetch('http://localhost:8000/repositories/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repositories: repoIds })
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText);
      }

      const data = await res.json();
      batchResults = data;
      batchAddStatus = data.message;

      // If all repositories were added successfully, clear the input
      if (data.results.failed.length === 0) {
        batchRepoIds = '';
      }

      // Refresh the repository list
      const reposData = await fetch('http://localhost:8000/repositories/').then(r => r.json());
      allRepos = reposData.repositories;
      // Update filteredRepos based on current search term
      filteredRepos = allRepos.filter(matchesSearch);

    } catch (err) {
      console.error(err);
      batchAddStatus = `❌ Error: ${err.message}`;
    } finally {
      isBatchAdding = false;
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
    background-color: #f3f4f6;
    border: none;
    border-radius: 6px;
    padding: 0.4rem 0.8rem;
    font-size: 0.9rem;
    font-family: monospace;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .tag-btn:hover {
    background-color: #d1d5db;
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

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>

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
      {#key currentDisplayCount + searchTerm}
        <table>
          <thead>
            <tr>
              <th class={sortField === 'name' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('name')}>Name</th>
              <th class={sortField === 'description' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('description')}>Description</th>
              <th class={sortField === 'license' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('license')}>License</th>
              <th class={sortField === 'stars' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('stars')}>Stars</th>
              <th class={sortField === 'last_synced' ? `sorted ${sortOrder}` : ''} on:click={() => changeSort('last_synced')}>Updated</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredRepos.slice(0, currentDisplayCount) as repo (repo.id)}
              <tr on:click={() => goToDetail(repo.id)}>
                <td>{repo.name}</td>
                <td>{repo.description}</td>
                <td>{repo.license}</td>
                <td>{repo.stars}</td>
                <td>{formatDate(repo.last_synced)}</td>
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
      <h2>➕ Add Repository</h2>

      <!-- Single Repository Add Section -->
      <div style="margin-bottom: 3rem;">
        <h3>Add Single Repository</h3>
        <input
          type="text"
          placeholder="username/repo"
          bind:value={newRepoId}
          style="width: 300px; margin-top: 1rem; font-size: 1rem;"
        />
        <div style="margin-top: 1rem;">
          <button class="add-repo-button" on:click={addRepo} disabled={isAdding}>
            {isAdding ? 'Adding...' : 'Add Repository'}
          </button>
        </div>
        {#if addStatus}
          <p style="margin-top: 1rem;">{addStatus}</p>
        {/if}
      </div>

      <!-- Batch Add Section -->
      <div>
        <h3>Batch Add Repositories</h3>
        <p>Enter one repository ID per line (format: username/repo)</p>
        <textarea
          class="batch-textarea"
          placeholder="username1/repo1
username2/repo2
username3/repo3"
          bind:value={batchRepoIds}
        ></textarea>
        <div style="margin-top: 1rem;">
          <button class="add-repo-button" on:click={addBatchRepos} disabled={isBatchAdding}>
            {isBatchAdding ? 'Adding...' : 'Add Repositories'}
          </button>
        </div>
        {#if batchAddStatus}
          <p style="margin-top: 1rem;">{batchAddStatus}</p>
        {/if}

        <!-- Batch Results -->
        {#if batchResults}
          <div class="batch-results">
            <!-- Successful Repositories -->
            {#if batchResults.results.successful.length > 0}
              <h3>✅ Successfully Added ({batchResults.results.successful.length})</h3>
              <div class="success-list">
                {#each batchResults.results.successful as repo}
                  <div class="repo-item">
                    <strong>{repo.id}</strong> - {repo.name}
                  </div>
                {/each}
              </div>
            {/if}

            <!-- Failed Repositories -->
            {#if batchResults.results.failed.length > 0}
              <h3>❌ Failed to Add ({batchResults.results.failed.length})</h3>
              <div class="failed-list">
                {#each batchResults.results.failed as repo}
                  <div class="repo-item">
                    <strong>{repo.id}</strong>
                    <div class="error-message">{repo.error}</div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>
