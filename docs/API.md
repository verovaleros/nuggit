# Nuggit API Documentation

The Nuggit API is built with FastAPI and provides endpoints for managing repositories, comments, and versions.

## Base URL

The API runs on port 8001 by default:

```
http://localhost:8001
```

## Authentication

The API does not require authentication, but some endpoints accept a GitHub token for accessing private repositories.

## Endpoints

### Repositories

#### List All Repositories

```
GET /repositories/
```

Returns a list of all repositories in the database.

**Response**

```json
{
  "repositories": [
    {
      "id": "owner/repo",
      "name": "Repository Name",
      "description": "Repository description",
      "url": "https://github.com/owner/repo",
      "topics": "topic1, topic2",
      "license": "MIT",
      "created_at": "2023-01-01T00:00:00",
      "updated_at": "2023-01-02T00:00:00",
      "stars": 10,
      "forks": 5,
      "issues": 2,
      "contributors": "3",
      "commits": 100,
      "last_commit": "2023-01-03T00:00:00",
      "tags": "tag1, tag2",
      "notes": "Notes about the repository",
      "last_synced": "2023-01-04T00:00:00"
    }
  ]
}
```

#### Check Repository Existence

```
GET /repositories/check/{repo_id}
```

Checks if a repository exists in the database.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Response**

```json
{
  "exists": true,
  "repository": {
    "id": "owner/repo",
    "name": "Repository Name",
    ...
  }
}
```

#### Add Repository

```
POST /repositories/
```

Fetches and stores repository metadata from GitHub.

**Request Body**

```json
{
  "id": "owner/repo",
  "url": "https://github.com/owner/repo",
  "token": "github_token"
}
```

Either `id` or `url` is required. `token` is optional.

**Response**

```json
{
  "message": "Repository 'owner/repo' added successfully.",
  "repository": {
    "id": "owner/repo",
    "name": "Repository Name",
    ...
  }
}
```

#### Update Repository

```
PUT /repositories/{repo_id}
```

Updates repository information from GitHub and creates a new version snapshot.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Query Parameters**

- `token`: GitHub token (optional)
- `max_retries`: Maximum number of retry attempts on rate limit (default: 3)

**Response**

```json
{
  "message": "Repository 'owner/repo' updated and versioned successfully.",
  "repository": {
    "id": "owner/repo",
    "name": "Repository Name",
    ...
  }
}
```

#### Delete Repository

```
DELETE /repositories/{repo_id}
```

Deletes a repository and its related data.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Response**

```json
{
  "message": "Repository 'owner/repo' deleted."
}
```

#### Update Repository Metadata

```
PATCH /repositories/{repo_id}/metadata
```

Updates metadata (tags and notes) for a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Request Body**

```json
{
  "tags": "tag1, tag2",
  "notes": "Updated notes"
}
```

**Response**

```json
{
  "message": "Metadata for 'owner/repo' updated.",
  "repository": {
    "id": "owner/repo",
    "name": "Repository Name",
    ...
  }
}
```

### Repository Detail

#### Get Repository Detail

```
GET /repositories/{repo_id}
```

Retrieves full repository info, including recent commits, comments, and versions.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Response**

```json
{
  "id": "owner/repo",
  "name": "Repository Name",
  "description": "Repository description",
  "url": "https://github.com/owner/repo",
  "topics": "topic1, topic2",
  "license": "MIT",
  "created_at": "2023-01-01T00:00:00",
  "updated_at": "2023-01-02T00:00:00",
  "stars": 10,
  "forks": 5,
  "issues": 2,
  "contributors": "3",
  "commits": 100,
  "last_commit": "2023-01-03T00:00:00",
  "tags": ["tag1", "tag2"],
  "notes": "Notes about the repository",
  "last_synced": "2023-01-04T00:00:00",
  "recent_commits": [
    {
      "sha": "commit_sha",
      "message": "Commit message",
      "author": "Author Name",
      "date": "2023-01-03T00:00:00"
    }
  ],
  "comments": [
    {
      "id": 1,
      "comment": "Comment text",
      "author": "Comment Author",
      "created_at": "2023-01-04T00:00:00"
    }
  ],
  "versions": [
    {
      "id": 1,
      "version": "1.0.0",
      "release_date": "2023-01-01T00:00:00",
      "description": "Version description",
      "created_at": "2023-01-01T00:00:00"
    }
  ]
}
```

#### Add Comment

```
POST /repositories/{repo_id}/comments
```

Adds a comment to a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Request Body**

```json
{
  "comment": "Comment text",
  "author": "Comment Author"
}
```

`author` is optional and defaults to "Anonymous".

**Response**

```json
{
  "id": 1,
  "comment": "Comment text",
  "author": "Comment Author",
  "created_at": "2023-01-04T00:00:00"
}
```

#### Get Comments

```
GET /repositories/{repo_id}/comments
```

Gets comments for a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Query Parameters**

- `limit`: Maximum number of comments to return (default: 20)

**Response**

```json
[
  {
    "id": 1,
    "comment": "Comment text",
    "author": "Comment Author",
    "created_at": "2023-01-04T00:00:00"
  }
]
```

#### Get Commits

```
GET /repositories/{repo_id}/commits
```

Gets recent commits for a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Query Parameters**

- `limit`: Maximum number of commits to return (default: 10)

**Response**

```json
[
  {
    "sha": "commit_sha",
    "message": "Commit message",
    "author": "Author Name",
    "date": "2023-01-03T00:00:00"
  }
]
```

### Versions

#### Add Version

```
POST /repositories/{repo_id}/versions
```

Adds a version to a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Request Body**

```json
{
  "version_number": "1.0.0",
  "release_date": "2023-01-01T00:00:00",
  "description": "Version description"
}
```

`release_date` and `description` are optional.

**Response**

```json
{
  "id": 1,
  "version_number": "1.0.0",
  "release_date": "2023-01-01T00:00:00",
  "description": "Version description",
  "created_at": "2023-01-01T00:00:00"
}
```

#### List Versions

```
GET /repositories/{repo_id}/versions
```

Gets versions for a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Query Parameters**

- `limit`: Maximum number of versions to return (default: 20)

**Response**

```json
[
  {
    "id": 1,
    "version_number": "1.0.0",
    "release_date": "2023-01-01T00:00:00",
    "description": "Version description",
    "created_at": "2023-01-01T00:00:00"
  }
]
```

#### Compare Versions

```
GET /repositories/{repo_id}/versions/compare
```

Compares two versions of a repository.

**Parameters**

- `repo_id`: Repository ID in the format "owner/repo"

**Query Parameters**

- `version1_id`: ID of the first version
- `version2_id`: ID of the second version

**Response**

```json
{
  "version1": {
    "id": 1,
    "version_number": "1.0.0",
    "release_date": "2023-01-01T00:00:00",
    "description": "Version description",
    "created_at": "2023-01-01T00:00:00"
  },
  "version2": {
    "id": 2,
    "version_number": "2.0.0",
    "release_date": "2023-01-02T00:00:00",
    "description": "Version description",
    "created_at": "2023-01-02T00:00:00"
  },
  "differences": {
    "version_number": {
      "old": "1.0.0",
      "new": "2.0.0",
      "changed": true
    },
    "release_date": {
      "old": "2023-01-01T00:00:00",
      "new": "2023-01-02T00:00:00",
      "changed": true
    },
    "description": {
      "old": "Version description",
      "new": "Version description",
      "changed": false
    },
    "license": {
      "old": "MIT",
      "new": "MIT",
      "changed": false
    },
    "stars": {
      "old": 10,
      "new": 15,
      "changed": true,
      "difference": 5
    },
    "forks": {
      "old": 5,
      "new": 7,
      "changed": true,
      "difference": 2
    },
    "issues": {
      "old": 2,
      "new": 3,
      "changed": true,
      "difference": 1
    },
    "contributors": {
      "old": "3",
      "new": "4",
      "changed": true,
      "difference": 1
    },
    "commits": {
      "old": 100,
      "new": 120,
      "changed": true,
      "difference": 20
    },
    "topics": {
      "old": "topic1, topic2",
      "new": "topic1, topic2, topic3",
      "changed": true
    },
    "description": {
      "old": "Repository description",
      "new": "Updated repository description",
      "changed": true
    },
    "last_commit": {
      "old": "2023-01-03T00:00:00",
      "new": "2023-01-04T00:00:00",
      "changed": true
    }
  }
}
```

## Error Handling

The API returns standard HTTP status codes:

- 200: Success
- 400: Bad request (e.g., invalid input)
- 404: Not found
- 500: Server error

Error responses include a detail message:

```json
{
  "detail": "Error message"
}
```

## Rate Limiting

The API respects GitHub's rate limits and will retry requests when rate limited. The `max_retries` parameter controls the number of retry attempts.
