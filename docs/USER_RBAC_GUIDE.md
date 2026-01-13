# User Management & RBAC Guide

This guide covers user management, role-based access control (RBAC), and authentication in DBNotebook.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Default Admin User](#default-admin-user)
- [Roles and Permissions](#roles-and-permissions)
- [User Management](#user-management)
- [API Keys](#api-keys)
- [Access Control](#access-control)
- [Database Schema](#database-schema)

---

## Overview

DBNotebook implements a role-based access control system with three levels:

| Role | Description | Permissions |
|------|-------------|-------------|
| **admin** | Full system access | Manage users, roles, notebooks, connections; view/edit/delete all |
| **user** | Standard access | Create notebooks/connections; view/edit assigned resources |
| **viewer** | Read-only access | View assigned notebooks only |

## Authentication

### Login Flow

DBNotebook uses session-based authentication with Flask sessions.

**Endpoint**: `POST /api/auth/login`

```json
{
    "username": "admin",
    "password": "admin123"
}
```

**Response**:
```json
{
    "success": true,
    "user": {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "username": "admin",
        "email": "admin@dbnotebook.local",
        "roles": ["admin"],
        "api_key": "dbn_00000000000000000000000000000001"
    }
}
```

### Logout

**Endpoint**: `POST /api/auth/logout`

Clears the session cookie.

### Get Current User

**Endpoint**: `GET /api/auth/me`

Returns the currently authenticated user's information.

---

## Default Admin User

On fresh installation, Alembic migrations create a default admin user:

| Field | Value |
|-------|-------|
| User ID | `00000000-0000-0000-0000-000000000001` |
| Username | `admin` |
| Email | `admin@dbnotebook.local` |
| Password | `admin123` |
| API Key | `dbn_00000000000000000000000000000001` |
| Role | `admin` |

**Security Note**: Change the default password in production environments.

---

## Roles and Permissions

### Role Definitions

#### Admin Role
```json
{
    "name": "admin",
    "description": "Full access to all features and user management",
    "permissions": [
        "manage_users",
        "manage_roles",
        "manage_notebooks",
        "manage_connections",
        "view_all",
        "edit_all",
        "delete_all"
    ]
}
```

#### User Role
```json
{
    "name": "user",
    "description": "Standard access to own notebooks and assigned resources",
    "permissions": [
        "create_notebook",
        "create_connection",
        "view_assigned",
        "edit_assigned"
    ]
}
```

#### Viewer Role
```json
{
    "name": "viewer",
    "description": "Read-only access to assigned notebooks",
    "permissions": [
        "view_assigned"
    ]
}
```

### Permission Descriptions

| Permission | Description |
|------------|-------------|
| `manage_users` | Create, update, delete users |
| `manage_roles` | Assign and revoke roles |
| `manage_notebooks` | Full control over all notebooks |
| `manage_connections` | Full control over database connections |
| `view_all` | View any resource in the system |
| `edit_all` | Edit any resource in the system |
| `delete_all` | Delete any resource in the system |
| `create_notebook` | Create new notebooks |
| `create_connection` | Create new database connections |
| `view_assigned` | View resources explicitly assigned |
| `edit_assigned` | Edit resources explicitly assigned |

---

## User Management

### Create User (Admin Only)

**Endpoint**: `POST /api/admin/users`

```json
{
    "username": "john",
    "email": "john@example.com",
    "password": "securepassword123",
    "roles": ["user"]
}
```

**Response**:
```json
{
    "success": true,
    "user": {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "username": "john",
        "email": "john@example.com",
        "roles": ["user"],
        "api_key": "dbn_a1b2c3d4e5f6..."
    }
}
```

### List Users (Admin Only)

**Endpoint**: `GET /api/admin/users`

Returns all users with their roles.

### Update User (Admin Only)

**Endpoint**: `PUT /api/admin/users/<user_id>`

```json
{
    "email": "newemail@example.com",
    "roles": ["user", "viewer"]
}
```

### Reset Password (Admin Only)

**Endpoint**: `PUT /api/admin/users/<user_id>/password`

```json
{
    "password": "newpassword123"
}
```

### Change Own Password

**Endpoint**: `POST /api/auth/password`

```json
{
    "current_password": "oldpassword",
    "new_password": "newpassword123"
}
```

### Delete User (Admin Only)

**Endpoint**: `DELETE /api/admin/users/<user_id>`

---

## API Keys

### Overview

Each user has a unique API key for programmatic access. API keys:
- Are prefixed with `dbn_` for easy identification
- Are unique per user
- Can be regenerated at any time
- Do not expire automatically

### Using API Keys

Include the API key in the `X-API-Key` header:

```bash
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dbn_a1b2c3d4e5f6..." \
  -d '{"notebook_id": "...", "query": "..."}'
```

### Regenerate API Key

**Self-service**: `POST /api/auth/api-key`

Returns a new API key. The old key is immediately invalidated.

**Admin action**: `POST /api/admin/users/<user_id>/api-key`

Generates a new API key for the specified user.

### API Key Format

```
dbn_<32 hexadecimal characters>
```

Example: `dbn_00000000000000000000000000000001`

---

## Access Control

### Notebook Access

Users can be granted access to specific notebooks with different access levels:

| Access Level | Capabilities |
|--------------|--------------|
| `owner` | Full control (edit, delete, share) |
| `editor` | Edit documents, run queries |
| `viewer` | View documents, run queries (read-only) |

**Grant Access (Admin/Owner)**:
```
POST /api/admin/notebooks/<notebook_id>/access
{
    "user_id": "...",
    "access_level": "editor"
}
```

### SQL Connection Access

Database connections can be shared with specific users:

| Access Level | Capabilities |
|--------------|--------------|
| `admin` | Full control (edit, delete, share) |
| `user` | Run queries, view schema |
| `viewer` | View schema only |

**Grant Access (Admin/Owner)**:
```
POST /api/admin/connections/<connection_id>/access
{
    "user_id": "...",
    "access_level": "user"
}
```

### Global Notebooks

Notebooks owned by the default admin user (`00000000-0000-0000-0000-000000000001`) are automatically visible to all users. This is useful for:
- Shared knowledge bases
- Company-wide documentation
- Public datasets

---

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    api_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP
);
```

### Roles Table

```sql
CREATE TABLE roles (
    role_id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### User Roles Table

```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, role_id)
);
```

### Notebook Access Table

```sql
CREATE TABLE notebook_access (
    id SERIAL PRIMARY KEY,
    notebook_id UUID REFERENCES notebooks(notebook_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    access_level VARCHAR(20) DEFAULT 'viewer',
    granted_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    granted_at TIMESTAMP DEFAULT NOW()
);
```

### SQL Connection Access Table

```sql
CREATE TABLE sql_connection_access (
    id SERIAL PRIMARY KEY,
    connection_id UUID REFERENCES database_connections(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    access_level VARCHAR(20) DEFAULT 'user',
    granted_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    granted_at TIMESTAMP DEFAULT NOW()
);
```

---

## Security Best Practices

1. **Change Default Password**: Immediately change `admin123` in production
2. **Use Strong Passwords**: Enforce minimum length and complexity
3. **Rotate API Keys**: Regenerate API keys periodically
4. **Principle of Least Privilege**: Assign minimum necessary roles
5. **Audit Access**: Regularly review user roles and notebook/connection access
6. **Secure Transport**: Always use HTTPS in production
7. **Session Management**: Configure appropriate session timeouts

---

## Related Documentation

- [API Guide](api/API_GUIDE.md) - Programmatic API documentation
- [Architecture](ARCHITECTURE.md) - System architecture overview
- [Multi-User Architecture Plan](MULTI_USER_ARCHITECTURE_PLAN.md) - Design details
