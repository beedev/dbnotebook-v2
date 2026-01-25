# API Authentication

DBNotebook supports multiple authentication methods for API access.

---

## Authentication Methods

### 1. Session-Based (Web UI)

The web interface uses session-based authentication:

```bash
# Login
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

# Response
{
  "success": true,
  "user": {
    "id": "uuid",
    "username": "admin",
    "role": "admin"
  },
  "api_key": "your-api-key"
}
```

Session cookies are automatically managed by the browser.

---

### 2. API Key Authentication

For programmatic access, use API keys via the `X-API-Key` header:

```bash
curl -X POST http://localhost:7860/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "notebook_id": "uuid",
    "query": "What are the key findings?"
  }'
```

#### Getting Your API Key

1. **Via Login Response**: Returned when you log in
2. **Via Profile**: `GET /api/auth/me` returns your API key
3. **Regenerate**: `POST /api/auth/regenerate-api-key`

#### API Key Endpoints

```bash
# Get current user info and API key
GET /api/auth/me
X-API-Key: your-api-key

# Regenerate API key
POST /api/auth/regenerate-api-key
X-API-Key: your-current-api-key

# Response
{
  "success": true,
  "api_key": "new-api-key"
}
```

---

### 3. Global API Key (Legacy)

For simple deployments, you can set a global API key:

```bash
# .env
API_KEY=your-global-api-key
```

This key works for the `/api/query` endpoint only.

---

## Protected Endpoints

### Requires Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/chat/*` | ALL | V2 Chat API |
| `/api/notebooks/*` | ALL | Notebook management |
| `/api/sql-chat/*` | ALL | SQL Chat |
| `/api/analytics/*` | ALL | Excel Analytics |
| `/api/studio/*` | ALL | Content Studio |
| `/api/admin/*` | ALL | Admin operations |

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Login |
| `/api/health` | GET | Health check |

### Optional Authentication

| Endpoint | Notes |
|----------|-------|
| `/api/query` | Uses `API_KEY` env var or `X-API-Key` header |
| `/chat` | Legacy endpoint, session-based |

---

## Role-Based Access Control (RBAC)

### Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access, user management |
| `user` | Standard access, own resources only |

### Enabling Strict Mode

```bash
# .env
RBAC_STRICT_MODE=true
```

In strict mode:
- Users can only access their own notebooks
- Users cannot see other users' data
- Admin endpoints require admin role

---

## User Management (Admin)

### List Users

```bash
GET /api/admin/users
X-API-Key: admin-api-key
```

### Create User

```bash
POST /api/admin/users
X-API-Key: admin-api-key
Content-Type: application/json

{
  "username": "newuser",
  "password": "securepassword",
  "role": "user"
}
```

### Delete User

```bash
DELETE /api/admin/users/{user_id}
X-API-Key: admin-api-key
```

---

## Password Management

### Change Password

```bash
POST /api/auth/change-password
X-API-Key: your-api-key
Content-Type: application/json

{
  "current_password": "oldpassword",
  "new_password": "newpassword"
}
```

### Password Requirements

- Minimum 8 characters (configurable)
- Stored using bcrypt hashing

---

## Session Configuration

```bash
# .env
FLASK_SECRET_KEY=your-secret-key  # Required for sessions
SESSION_COOKIE_SECURE=true        # HTTPS only
SESSION_COOKIE_HTTPONLY=true      # No JavaScript access
SESSION_COOKIE_SAMESITE=Lax       # CSRF protection
```

!!! warning "Production Requirement"
    Always set a strong `FLASK_SECRET_KEY` in production. Without it, sessions won't persist across server restarts.

---

## Security Best Practices

### 1. Use HTTPS in Production

```bash
# Behind reverse proxy (nginx)
PREFERRED_URL_SCHEME=https
```

### 2. Rotate API Keys Regularly

```bash
# Regenerate periodically
POST /api/auth/regenerate-api-key
```

### 3. Use Read-Only Database Users for SQL Chat

```sql
CREATE USER readonly_user WITH PASSWORD 'password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```

### 4. Enable RBAC in Multi-User Deployments

```bash
RBAC_STRICT_MODE=true
```

### 5. Change Default Credentials

The default admin credentials are:
- Username: `admin`
- Password: `admin123`

**Change immediately in production!**

---

## Troubleshooting

### "Unauthorized" Errors

1. Check API key is correct
2. Verify header name: `X-API-Key` (case-sensitive)
3. Ensure user exists and is active

### Session Not Persisting

1. Set `FLASK_SECRET_KEY` in .env
2. Check cookie settings if behind proxy
3. Verify same-origin policy

### API Key Not Working

1. Try regenerating: `POST /api/auth/regenerate-api-key`
2. Check user role has required permissions
3. Verify RBAC mode settings
