# Nuggit Frontend Documentation

The Nuggit frontend is built with Svelte and provides a user interface for interacting with the Nuggit API.

## Architecture

The frontend is a single-page application (SPA) that uses the Svelte framework. It uses the following libraries:

- **Svelte**: UI framework
- **svelte-spa-router**: Client-side routing

## Project Structure

```
nuggit/frontend/
├── public/             # Static assets
├── src/
│   ├── assets/         # Images, fonts, etc.
│   ├── components/     # Reusable components
│   │   └── TagInput.svelte  # Tag input component
│   ├── lib/            # Utility libraries
│   ├── routes/         # Page components
│   │   ├── Home.svelte # Home page
│   │   ├── Detail.svelte # Repository detail page
│   │   └── routes.js   # Route definitions
│   ├── App.svelte      # Root component
│   └── main.js         # Entry point
├── scripts/            # Build scripts
├── vite.config.js      # Vite configuration
└── package.json        # Dependencies and scripts
```

## Pages

### Home Page (`Home.svelte`)

The home page displays a list of all repositories and provides functionality for:

- Searching repositories
- Filtering repositories by tag
- Sorting repositories
- Adding new repositories
- Viewing repository statistics

The home page has four tabs:

1. **Repos**: Displays a table of repositories
2. **Tags**: Displays all tags used across repositories
3. **Stats**: Displays repository statistics
4. **Add Repo**: Form for adding new repositories

### Detail Page (`Detail.svelte`)

The detail page displays detailed information about a single repository and provides functionality for:

- Viewing repository metadata
- Adding and viewing comments
- Viewing recent commits
- Managing repository tags
- Updating repository data from GitHub
- Viewing and comparing versions
- Deleting the repository

The detail page has several sections:

1. **Repository Info**: Basic repository information
2. **Tags**: Repository tags
3. **Comments**: Repository comments
4. **Recent Commits**: Recent commits to the repository
5. **Version Tracker**: Repository versions
6. **Compare Versions**: Tool for comparing versions

## Components

### TagInput (`TagInput.svelte`)

A reusable component for inputting tags. It provides:

- Adding tags by typing and pressing Enter or comma
- Removing tags by clicking the "×" button
- Displaying tags as pills/chips

## Routing

Routing is handled by `svelte-spa-router`. The routes are defined in `src/routes/routes.js`:

```javascript
import Home from './Home.svelte';
import Detail from './Detail.svelte';

export default {
  '/': Home,
  '/repo/:id': Detail
};
```

The router is initialized in `App.svelte`:

```javascript
import Router from 'svelte-spa-router';
import routes from './routes/routes.js';

<Router {routes} />
```

## API Integration

The frontend communicates with the backend API using the Fetch API. The API base URL is hardcoded as `http://localhost:8001`.

### Example API Calls

#### Fetching Repositories

```javascript
const res = await fetch('http://localhost:8001/repositories/');
const data = await res.json();
allRepos = data.repositories;
```

#### Adding a Repository

```javascript
const res = await fetch('http://localhost:8001/repositories/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ id: repoInput })
});
```

#### Updating Repository Metadata

```javascript
const res = await fetch(`http://localhost:8001/repositories/${repoId}/metadata`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ tags, notes })
});
```

## Styling

The frontend uses custom CSS for styling. Styles are defined within each component using Svelte's `<style>` block.

### Key UI Elements

- **Cards**: Used for displaying repository information
- **Tables**: Used for displaying lists of repositories, commits, etc.
- **Tabs**: Used for organizing content on the home page
- **Pills/Chips**: Used for displaying tags
- **Buttons**: Used for actions like saving, updating, deleting, etc.

## Data Flow

1. User navigates to the home page
2. Frontend fetches repositories from the API
3. User clicks on a repository
4. Frontend navigates to the detail page
5. Frontend fetches repository details from the API
6. User interacts with the repository (adds comments, updates tags, etc.)
7. Frontend sends updates to the API
8. API processes the updates and returns the updated data
9. Frontend displays the updated data

## Error Handling

The frontend handles errors by displaying error messages to the user. It also provides loading indicators during API calls.

## Responsive Design

The frontend is designed to be responsive and work on both desktop and mobile devices.
