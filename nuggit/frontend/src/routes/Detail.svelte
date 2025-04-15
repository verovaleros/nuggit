<script>
  import { onMount } from 'svelte';

  let repoId = null;
  let repo = null;
  let loading = true;
  let error = null;

  let tags = '';
  let notes = '';
  let saveStatus = '';

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
      repo = await res.json();
      tags = repo.tags;
      notes = repo.notes;
    } catch (err) {
      error = 'Failed to fetch repository details.';
      console.error(err);
    } finally {
      loading = false;
    }
  });

  async function saveMetadata() {
    saveStatus = 'Saving...';
    try {
      const res = await fetch(`http://localhost:8000/repositories/${repoId}`, {
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
    } catch (err) {
      console.error(err);
      saveStatus = '❌ Failed to save.';
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

  .save-status {
    margin-top: 0.5rem;
    text-align: center;
    font-style: italic;
  }

  .nav-back {
    max-width: 960px;
    margin: 1rem auto -1rem auto;
    text-align: left;
  }

  .nav-back button {
    background-color: #e5e7eb;
    color: #111827;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    cursor: pointer;
    font-size: 1rem;
  }

  .nav-back button:hover {
    background-color: #d1d5db;
  }
</style>

<div class="nav-back">
  <button on:click={() => window.location.hash = '#/'}>← Back to Home</button>
</div>

<div class="container">
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
