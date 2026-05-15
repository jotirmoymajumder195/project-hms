# Security & Compliance

## Authentication & Authorization

- **JWT tokens** with 8-hour expiry (365-day for DISPLAY accounts)
- **bcrypt hash** cost factor 12 for password storage
- **Per-email rate limiting**: 3 failed attempts → 15-minute block (in-memory Map)
- **Global rate limiting**: 100 requests per 15 minutes per IP (/api/*)
- **Auth rate limiting**: 5 login attempts per 15 minutes
- **Role-based access control**: `authenticate` + `authorize(ROLES.ADMIN, ...)` middleware
- **DISPLAY role blocking**: `blockDisplay` middleware prevents token board accounts from accessing any other route
- **Self-deactivation prevention**: Admin cannot deactivate their own account
- **Cross-admin password reset blocked**: Admin cannot reset another admin's password

## API Security

- **Helmet**: XSS, clickjacking, MIME sniffing, CSP headers
- **CORS**: Only configured frontend URL + localhost:3000 allowed
- **Input validation**: express-validator on all mutation endpoints
- **Request body limit**: 10MB max
- **Compression enabled**

## Data Protection (DPDPA 2023)

- **Aadhaar encryption**: AES-256-GCM before storage. Encryption key from `ENCRYPTION_KEY` env var
- **Consent logging**: Every patient registration logs explicit consent with consent text
- **Audit trail**: All CREATE/READ/UPDATE/DELETE/LOGIN/LOGOUT/EXPORT/PRINT actions logged
- **Data requests**: Patients can request data export, correction, or deletion via `/data-request`
- **Password never returned**: `passwordHash` is excluded from all API responses
- **Sensitive field filtering**: Encrypted fields excluded from responses

## Infrastructure (Production)

- **AWS Mumbai region** (`ap-south-1`) — data stays in India
- **PostgreSQL** — encrypted at rest (RDS default)
- **S3** — Prescription uploads, logo, reports
- **S3 bucket policy**: Only accessible from the app's domain (CSP img-src directive)
- **Environment variables**: All secrets via `.env` (never committed)
- **Redis**: Session cache, queue state, rate limiting

## NABH Compliance (Audit)

- `AuditLog` captures: userId, action, resource, resourceId, details (JSON diff), ipAddress, userAgent, timestamp
- Searchable audit interface for ADMIN via `/audit`
- Actions logged: CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, PRINT

## Error Handling

- **Global error handler**: Catches all thrown errors, returns structured JSON
- **Prisma errors mapped**: P2002 (unique constraint → 409), P2025 (not found → 404)
- **JWT errors mapped**: Expired → 401, invalid → 401
- **Operational errors**: Custom `AppError` class with `isOperational` flag
- **Production safety**: Internal error details hidden in production mode
- **Unhandled rejections**: Logged and process exits (fail-fast)

## Password Policy

- Minimum 8 characters for registration
- Must contain: uppercase, lowercase, digit
- Regular password changes via `/auth/change-password`
- Admin can reset any staff's password → forces `mustChangePassword = true`
- Doctors forced to change password on first login (S01)
