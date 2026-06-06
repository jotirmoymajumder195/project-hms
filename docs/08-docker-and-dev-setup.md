# HMS — Docker & Developer Setup Guide

This document covers all infrastructure changes made to the project and serves as the
reference for any developer onboarding or deploying the system.

---

## Table of Contents
1. [What Changed and Why](#1-what-changed-and-why)
2. [Repository Structure](#2-repository-structure)
3. [Local Development Setup](#3-local-development-setup)
4. [Environment Variables Reference](#4-environment-variables-reference)
5. [Production Deployment (AWS EC2)](#5-production-deployment-aws-ec2)
6. [Backend Code Changes](#6-backend-code-changes)
7. [Frontend Code Changes](#7-frontend-code-changes)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. What Changed and Why

### Infrastructure / Docker
| File | Change | Reason |
|------|--------|--------|
| `hms-backend/Dockerfile` | 2-stage build (builder + runner) + OpenSSL | Slim prod image; OpenSSL required by Prisma on Alpine |
| `hms-backend/.dockerignore` | Excludes node_modules, .env, logs, .git | Prevents secrets and large dirs from entering build context |
| `hms-backend/.env.docker` | Template env for Docker Compose local dev | Postgres/Redis use Docker service names, not localhost |
| `hms-backend/.env.prod` | Template env for EC2 production | All secrets as placeholders; `REDIS_URL=redis://redis:6379` |
| `hms-frontend/Dockerfile` | 3-stage build: dev / builder / runner | dev=HMR; builder=`next build`; runner=standalone serve |
| `hms-frontend/.dockerignore` | Excludes node_modules, .next, .env | Keeps build context small |
| `docker-compose.yml` | Local dev: Postgres + Redis + backend + frontend | One command starts everything with hot reload |
| `docker-compose.prod.yml` | Production: Redis + backend + frontend | Postgres uses AWS RDS; Nginx stays on host |
| `.env.example` | Root-level template for compose vars | `NEXT_PUBLIC_API_URL` and `DATABASE_URL` for compose interpolation |
| `hms-frontend/next.config.js` | Added `output: 'standalone'` | Required for the runner stage Docker image |

### Backend Code Fixes
| File | Change | Reason |
|------|--------|--------|
| `src/lib/prisma.js` | **NEW** — singleton PrismaClient | 13 files each called `new PrismaClient()`, exhausting the connection pool |
| `src/config/index.js` | Startup validation for required secrets | Fails fast with clear message instead of cryptic runtime errors |
| `src/server.js` | Unified `/health` + `/api/v1/health` endpoint | Both routes now check DB + Redis liveness |
| All module files | Import singleton from `lib/prisma` | Replaced all `new PrismaClient()` instances |
| `emergency/emergency.routes.js` | Bug fix: modify-request on unconfirmed bills | Was silently allowing modification of unconfirmed bills |

### Frontend Code Fixes
| File | Change | Reason |
|------|--------|--------|
| `src/lib/api.ts` | Removed hardcoded IP fallback | `http://13.206.144.153/api/v1` was baked in; now uses env var only |
| `src/lib/api.ts` | 401 redirect loop guard | Infinite redirect if login endpoint itself returned 401 |
| `src/lib/auth-context.tsx` | Silent catch replaced with `console.warn` | Logout failures were swallowed silently |
| `src/app/appointments/page.tsx` | Fixed import path for CheckInModal | Was importing from wrong path, causing a build error |
| `src/app/appointments/walk-in/page.tsx` | Silent catch replaced with `console.error` | Patient search failures were invisible |
| `src/app/token-board/page.tsx` | Exponential backoff polling (3s→30s) | Fixed polling: resets to 3s on success, doubles to 30s on repeated errors |
| `src/components/CheckInModal.tsx` | **DELETED** | Duplicate of `layout/CheckInModal.tsx`; mobile-optimised version kept |

---

## 2. Repository Structure

```
Project-hms/
├── docker-compose.yml          ← Local dev (4 services)
├── docker-compose.prod.yml     ← Production (3 services, RDS for DB)
├── .env.example                ← Copy to .env; sets NEXT_PUBLIC_API_URL + DATABASE_URL
├── hms-backend/
│   ├── Dockerfile              ← 2-stage: builder (devDeps) + runner (prod only)
│   ├── .dockerignore
│   ├── .env.docker             ← Template for local Docker dev (copy to .env)
│   ├── .env.prod               ← Template for EC2 production secrets
│   ├── prisma/
│   │   ├── schema.prisma
│   │   ├── seed.js             ← Seeds tenant + admin user + wards
│   │   └── migrations/
│   └── src/
│       └── lib/
│           └── prisma.js       ← Singleton PrismaClient (NEW)
└── hms-frontend/
    ├── Dockerfile              ← 3-stage: dev / builder / runner
    ├── .dockerignore
    └── next.config.js          ← output: 'standalone' (required for runner stage)
```

---

## 3. Local Development Setup

### Prerequisites
- Docker Desktop (Windows: enable "Use WSL 2 based engine" in Settings)
- Git with submodules (`git clone --recurse-submodules`)

### First-time setup (one command after cloning)

```bash
cd /path/to/Project-hms

# 1. Create env files from templates
cp hms-backend/.env.docker hms-backend/.env
cp .env.example .env

# 2. Fill in real secrets in hms-backend/.env
#    Generate ENCRYPTION_KEY:   openssl rand -hex 32
#    Generate JWT_SECRET:       openssl rand -base64 48
nano hms-backend/.env

# 3. Build and start all 4 services
docker compose up -d --build

# 4. Watch backend logs until you see "HMS Server running on port 5000"
docker compose logs -f backend

# 5. Seed the database (first time only)
docker compose exec backend node prisma/seed.js
```

### Default login credentials (after seeding)
| Field | Value |
|-------|-------|
| `x-tenant-id` header | `mbs` |
| Employee ID | `ADMIN-001` |
| Password | `Admin@123!` |

> **Change the password immediately after first login.**

### URLs
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:5000/api/v1 |
| Health check | http://localhost:5000/api/v1/health |
| Postgres | localhost:5432 (user: `hms_user`, pass: `strongpassword`, db: `hms_db`) |

### Useful commands

```bash
# Tail logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a single service after code changes (backend hot-reloads via nodemon)
docker compose up -d --build backend

# Run Prisma commands inside the container
docker compose exec backend npx prisma studio            # GUI DB browser
docker compose exec backend npx prisma db push           # Sync schema → DB (dev)
docker compose exec backend npx prisma migrate dev --name <name>  # Create migration

# Install a new npm package
# Backend: edit package.json, then:
docker compose up -d --build backend
# Frontend: edit package.json, then:
docker compose up -d --build frontend

# Stop everything (keeps DB volume)
docker compose down

# Stop and wipe DB data (full reset)
docker compose down -v
docker compose up -d --build
docker compose exec backend node prisma/seed.js
```

### Hot reload behaviour
| Service | How it works |
|---------|-------------|
| Backend | `nodemon` watches `src/` via volume mount — restarts on every `.js` save |
| Frontend | Next.js HMR via volume mount — instant in-browser update on `.tsx/.ts` save |
| `WATCHPACK_POLLING=true` | Required on Windows + WSL2 — inotify events aren't forwarded reliably |

---

## 4. Environment Variables Reference

### `hms-backend/.env` (local dev — copy from `.env.docker`)

| Variable | Example | Notes |
|----------|---------|-------|
| `NODE_ENV` | `development` | |
| `PORT` | `5000` | Must match Nginx config in prod |
| `DATABASE_URL` | `postgresql://hms_user:strongpassword@postgres:5432/hms_db` | Uses Docker service name `postgres`, not `localhost` |
| `REDIS_URL` | `redis://redis:6379` | Uses Docker service name `redis` |
| `JWT_SECRET` | ≥32 chars random string | Generate: `openssl rand -base64 48` |
| `ENCRYPTION_KEY` | Exactly 64 hex chars | Generate: `openssl rand -hex 32` — enforced at startup |
| `AWS_ACCESS_KEY_ID` | — | For S3 file uploads |
| `AWS_SECRET_ACCESS_KEY` | — | |
| `AWS_REGION` | `ap-south-1` | Mumbai |
| `AWS_S3_BUCKET` | — | |
| `TWILIO_ACCOUNT_SID` | — | For SMS notifications |
| `TWILIO_AUTH_TOKEN` | — | |
| `TWILIO_PHONE_NUMBER` | — | |
| `SMTP_HOST` | `smtp.gmail.com` | |
| `SMTP_PORT` | `587` | |
| `SMTP_USER` | — | |
| `SMTP_PASS` | — | Gmail app password, not account password |

### Root `.env` (compose-level vars — copy from `.env.example`)

| Variable | Local value | Production value |
|----------|-------------|-----------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:5000/api/v1` | `https://api.yourdomain.com/api/v1` |
| `DATABASE_URL` | _(not needed for local dev — overridden by compose)_ | RDS connection string |

> **Why two env files?**
> `hms-backend/.env` is loaded by the Node process inside the container.
> Root `.env` is read by Docker Compose itself for variable interpolation (e.g. `${NEXT_PUBLIC_API_URL}`).

---

## 5. Production Deployment (AWS EC2)

### Architecture
```
Browser → Nginx (EC2, port 443) → Docker backend (127.0.0.1:5000)
                                → Docker frontend (127.0.0.1:3000)
Docker backend → AWS RDS (Postgres)
Docker backend → Docker Redis (container)
```

### First-time EC2 setup

```bash
# 1. Clone the repo
git clone <repo-url> && cd Project-hms

# 2. Stop old PM2 + standalone Redis (if migrating from bare-metal)
pm2 stop all && pm2 delete all
sudo systemctl stop redis && sudo systemctl disable redis

# 3. Fill in backend production secrets
nano hms-backend/.env.prod    # replace every YOUR_VALUE_HERE

# 4. Create root .env for compose-level vars
cp .env.example .env
nano .env
# Set:
#   NEXT_PUBLIC_API_URL=https://your-api-domain.com/api/v1
#   DATABASE_URL=<your RDS connection string>

# 5. Generate secrets (if not done yet)
openssl rand -hex 32      # → paste as ENCRYPTION_KEY in .env.prod (64 hex chars)
openssl rand -base64 48   # → paste as JWT_SECRET in .env.prod

# 6. Build and start
docker compose -f docker-compose.prod.yml up -d --build

# 7. Seed the database (first time only)
docker compose -f docker-compose.prod.yml exec backend node prisma/seed.js

# 8. Verify
curl https://your-api-domain.com/api/v1/health
```

### Subsequent deployments

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Useful prod commands

```bash
# Logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# Container status
docker compose -f docker-compose.prod.yml ps

# Shell into backend
docker compose -f docker-compose.prod.yml exec backend sh

# Run Prisma migrate (after schema changes with a proper migration)
docker compose -f docker-compose.prod.yml exec backend npx prisma migrate deploy
```

### Nginx config (no changes needed)
The existing Nginx config routes to `localhost:5000` (backend) and `localhost:3000` (frontend).
The containers bind to `127.0.0.1` only (`127.0.0.1:5000:5000`) so they are never exposed
to the internet directly — only through Nginx.

---

## 6. Backend Code Changes

### Singleton PrismaClient — `src/lib/prisma.js`

**Problem:** Every module was calling `new PrismaClient()`, creating a separate connection pool
per module (13+ pools in dev, causing pool exhaustion and Prisma warnings).

**Fix:** A single shared instance stored on `globalThis` to survive hot-reload in development.

```js
// src/lib/prisma.js
const { PrismaClient } = require('@prisma/client');
const globalForPrisma = global;
const prisma = globalForPrisma.prisma ?? new PrismaClient();
if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
module.exports = prisma;
```

**Usage in any module:**
```js
const prisma = require('../../lib/prisma');   // adjust relative path
```

### Startup Secret Validation — `src/config/index.js`

Added at the very top, before `module.exports`. The process exits immediately if secrets
are missing or malformed, rather than crashing mid-request.

```
ENCRYPTION_KEY must be exactly 64 hex characters (32 bytes).
JWT_SECRET must be at least 32 characters.
DATABASE_URL, JWT_SECRET, ENCRYPTION_KEY are all required.
```

### Health Endpoint — `src/server.js`

Both `/health` and `/api/v1/health` now run the same async check:
- `prisma.$queryRaw\`SELECT 1\`` — confirms DB connectivity
- `getRedis().ping()` — confirms Redis connectivity
- Returns `200 OK` with `{ success: true, checks: { db: "ok", redis: "ok" } }`
- Returns `503 DEGRADED` if either check fails (useful for load balancer health checks)

---

## 7. Frontend Code Changes

### API Base URL — `src/lib/api.ts`

The hardcoded fallback IP (`http://13.206.144.153/api/v1`) was removed.
`NEXT_PUBLIC_API_URL` is now the only source of truth.

To change the backend URL: edit `NEXT_PUBLIC_API_URL` in root `.env` and rebuild the frontend.

### 401 Redirect Loop Guard — `src/lib/api.ts`

The Axios response interceptor now checks two conditions before redirecting to `/login`:
1. The request was not itself a login request (avoids loop on bad credentials)
2. The user is not already on `/login`

### Token Board Polling — `src/app/token-board/page.tsx`

Fixed from a fixed 3s `setInterval` to exponential backoff:
- Resets to 3s on every successful fetch
- Doubles (up to 30s max) on each consecutive error
- Prevents hammering the backend when it's temporarily unavailable

---

## 8. Troubleshooting

### "Invalid or inactive tenant" on login
The database is empty — run the seed:
```bash
docker compose exec backend node prisma/seed.js
```
Then log in with `x-tenant-id: mbs`, Employee ID: `ADMIN-001`, Password: `Admin@123!`.

### Backend crashes immediately on startup
Check for the `[FATAL]` line in logs:
```bash
docker compose logs backend | grep FATAL
```
Common causes:
- `ENCRYPTION_KEY` is not exactly 64 hex chars → regenerate with `openssl rand -hex 32`
- `JWT_SECRET` is shorter than 32 chars → regenerate with `openssl rand -base64 48`
- `DATABASE_URL` is missing or wrong

### Prisma "Cannot find module @prisma/client"
The Prisma client wasn't generated. Rebuild the backend image:
```bash
docker compose up -d --build backend
```

### Frontend hot reload not working (Windows/WSL2)
Ensure `WATCHPACK_POLLING: "true"` is set in the frontend service environment in `docker-compose.yml`.
If still broken, restart the frontend container:
```bash
docker compose restart frontend
```

### Port already in use
Another process is using 5000 or 3000. Find and stop it:
```bash
# Windows PowerShell
netstat -ano | findstr :5000
Stop-Process -Id <PID>
```

### Database migration error on fresh DB
The migration history assumes a base schema that predates the migrations folder.
For local dev, `prisma db push` is used (bypasses migration history).
For production, you need a proper baseline migration — ask the lead developer before
running `migrate deploy` on a fresh RDS instance.
