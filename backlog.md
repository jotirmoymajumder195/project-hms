# HMS Project — Code Review & Backlog

> Review date: 2026-05-09
> Project: MBS Hospital Management System (HMS)
> Stack: Node.js/Express (backend) + Next.js 14/TypeScript (frontend) + PostgreSQL/Prisma

---

## 🔴 Critical Issues

### C1. No .env.example — Configuration is undocumented
**Where:** `hms-backend/`
**Problem:** The project reads ~20 env vars (`JWT_SECRET`, `ENCRYPTION_KEY`, `AWS_*`, `TWILIO_*`, `SMTP_*`, etc.) but has no `.env.example` file. New developers have no idea what variables to set. The app will silently fail or crash at runtime with cryptic errors when required vars are missing.
**Fix:** Create `.env.example` with all variables, mark required vs optional, add startup validation that crashes with a clear message if required vars are missing.

### C2. ENCRYPTION_KEY is not validated at startup
**Where:** `hms-backend/src/utils/encryption.js:18`
**Problem:** `process.env.ENCRYPTION_KEY || ''` silently produces a 0-byte key. AES-256-GCM will throw a cryptic `Invalid key length` error at encryption time (runtime). Patient Aadhaar data would be unencryptable.
**Fix:** Validate at startup that `ENCRYPTION_KEY` is a 64-char hex string (32 bytes). Crash immediately if missing or malformed.

### C3. JWT_SECRET not validated at startup
**Where:** `hms-backend/src/config/index.js:13`
**Problem:** If `JWT_SECRET` is unset, `jsonwebtoken` uses `undefined` as the secret — all tokens become trivially forgeable. There is no crash or warning at startup.
**Fix:** Validate at startup. Crash if `JWT_SECRET` is missing.

### C4. Zero test coverage across the entire project
**Where:** `hms-backend/`, `hms-frontend/`
**Problem:** 0 test files found. No unit, integration, or E2E tests. Critical business logic (appointment booking, billing, check-in transaction) has zero automated verification.
**Fix:** Start with integration tests for Prisma operations (check-in transaction), then API endpoint tests, then frontend component tests.

### C5. ID generators have race conditions
**Where:** `hms-backend/src/utils/idGenerators.js` (all 5 functions)
**Problem:** Read-then-write pattern in separate queries — two concurrent requests can read the same `lastNum` and generate duplicate IDs (UHID, bill numbers, etc.). In a busy hospital, this WILL happen.
**Fix:** Use a database sequence (PostgreSQL `SERIAL`/`IDENTITY`) or wrap in a Prisma `$transaction` with proper locking (`SELECT ... FOR UPDATE`).

### C6. Check-in transaction has no compensation/rollback for downstream failures
**Where:** `hms-backend/src/modules/appointment/checkin.helper.js`
**Problem:** The check-in creates OPDVisit → Bill → Payment in a transaction, but if the HTTP response fails to send (network issue after DB commit), the patient is checked in but the frontend shows an error. No idempotency key or saga pattern.
**Fix:** Add idempotency key support or a reconciliation endpoint.

---

## 🟠 High Priority

### H1. Backend lacks service/controller layer — all logic in route files
**Where:** All `*.routes.js` files
**Problem:** Route files contain request handling, business logic, DB queries, and response formatting all in one function. Single files are 500-835 lines (appointment: 835, auth: 573, opd-chambers: 602). No separation of concerns, impossible to unit test.
**Fix:** Split into `routes/` → `controllers/` → `services/` → `repositories/`. Business logic in services, DB queries in repositories.

### H2. Backend is plain JavaScript — no TypeScript
**Where:** `hms-backend/src/` (all .js files)
**Problem:** Runtime errors from undefined properties, no type safety for Prisma queries, no IDE autocompletion for request/response shapes. Frontend is TypeScript but backend is not.
**Fix:** Migrate backend to TypeScript incrementally (start with shared types, then services).

### H3. No Docker/deployment configuration
**Where:** Project root
**Problem:** No `Dockerfile`, `docker-compose.yml`, or deployment scripts. The project requires Node.js, PostgreSQL 15, and Redis 7 — all must be manually installed and configured.
**Fix:** Add `docker-compose.yml` with backend, frontend, PostgreSQL, and Redis services. Add `Dockerfile` for both apps.

### H4. DISPLAY role receives 365-day JWT (security concern)
**Where:** `hms-backend/src/modules/auth/auth.routes.js` and `hms-frontend/src/lib/auth-context.tsx:70`
**Problem:** DISPLAY accounts get a 365-day token with no way to revoke it server-side (no JWT blacklist). If a token is stolen, it's valid for a year. Frontend sets `expires: 1` via cookie, but backend issue remains.
**Fix:** Add a JWT blacklist/revocation mechanism using Redis. Reduce max token lifetime. Or implement refresh token rotation.

### H5. 5 out of 14 backend modules are non-functional stubs
**Where:** `hms-backend/src/modules/inventory/`, `ipd/`, `lab/`, `pharmacy/`, `notifications/`
**Problem:** Return `"Module active — full build coming next session"`. The Prisma schema has full models for all these, so schema is ahead of implementation. This creates confusing 404s and dead frontend links.
**Fix:** Either implement the modules or remove the stub routes (return 404 properly). Also remove or label corresponding frontend sidebar links.

### H6. Two duplicate CheckInModal components
**Where:** `hms-frontend/src/components/layout/CheckInModal.tsx` (323 lines) and `hms-frontend/src/components/CheckInModal.tsx` (285 lines)
**Problem:** Two different versions of essentially the same modal. Creates maintenance burden — fixes in one won't apply to the other. Likely one is mobile-optimized and the other desktop.
**Fix:** Merge into a single responsive component with consistent behavior.

### H7. Uploaded prescription files have no cleanup mechanism
**Where:** `hms-backend/src/modules/opd/opd.routes.js` (prescription-upload endpoint)
**Problem:** Files uploaded via multer go to `uploads/prescriptions/` but there's no cleanup job, no TTL, no S3 lifecycle policy. Disk will fill up over time.
**Fix:** Add S3 upload (already configured in AWS config), or add a scheduled cleanup job, or configure multer to use S3 directly.

### H8. /doctor/next endpoint makes 10+ sequential DB queries
**Where:** `hms-backend/src/modules/appointment/appointment.routes.js:592-748`
**Problem:** The "Next Patient" flow sequentially queries: DoctorQueue lookup → update current visit → fetch linked visit → update appointment → loop fetch candidates → update skipped token → fallback query → upsert queue → update appointment → log audit. At high throughput, this will block the event loop and cause slow responses.
**Fix:** Batch queries using Prisma `$transaction`, use findMany with `skip` instead of loop, reduce round-trips.

### H9. No database health check in /health endpoint
**Where:** `hms-backend/src/server.js:128-149`
**Problem:** The health endpoint returns "OK" even when PostgreSQL or Redis is down. Load balancers/routers won't detect backend degradation.
**Fix:** Add Prisma `$queryRaw` and Redis `PING` checks to the health endpoint.

---

## 🟡 Medium Priority

### M1. Audit helper silently swallows all errors
**Where:** `hms-backend/src/utils/auditHelper.js:36-39`
**Problem:** If the audit log write fails (DB down, schema mismatch), the error is logged but the main operation continues. This is correct in principle (audit should never crash the app), but there's no alerting or fallback (e.g., write to a local file).
**Fix:** Add Winston file transport as fallback when DB audit fails. Add alerting threshold for audit failure rate.

### M2. Settings page is 1393 lines — should be split into separate files
**Where:** `hms-frontend/src/app/settings/page.tsx`
**Problem:** A single file contains 5 sub-components (SettingsPage, StaffTab, StaffModal, ConsumablesTab, ConsumableModal, OPDChambersTab, ChamberModal, ChangePasswordTab). Impossible to navigate, review, or test.
**Fix:** Split into `settings/staff-tab.tsx`, `settings/consumables-tab.tsx`, `settings/chambers-tab.tsx`, etc.

### M3. Settings page uses raw axios instead of the API client
**Where:** `hms-frontend/src/app/settings/page.tsx:45` and throughout
**Problem:** Settings page creates its own `API` constant (`'http://localhost:5000/api/v1'`) and manually attaches tokens via `getToken()`, bypassing the shared `api.ts` Axios instance that handles 401 redirects, base URL, and headers.
**Fix:** Use the imported `api` instance from `@/lib/api` consistently.

### M4. Hardcoded fallback IP addresses
**Where:** 
- `hms-frontend/next.config.js:4` — `http://13.206.144.153/api/v1`
- `hms-frontend/src/lib/api.ts:12` — `http://13.206.144.153/api/v1`
- `hms-frontend/src/app/settings/page.tsx:45` — `http://localhost:5000/api/v1`
**Problem:** Three different fallback URLs, one pointing to a specific production IP. This is a security concern (production URL in code) and causes confusion between environments.
**Fix:** Use a single source of truth. Remove production IP from code. Use `.env.local` for all environment-specific values.

### M5. Silent catch blocks throughout backend
**Where:** Multiple files including `appointment.routes.js` lines 619-631, 816
**Problem:** `.catch(() => {})` patterns swallow errors silently. If the DB update fails after advancing the queue, the system state becomes inconsistent with no trace.
**Fix:** Log all caught errors at minimum. Implement compensation actions for failed secondary operations.

### M6. No loading/error/empty states on many pages
**Where:** Multiple frontend pages
**Problem:** Several pages don't show loading skeletons, error banners, or empty states when data is being fetched or unavailable. This creates a poor UX (blank screens, no feedback on failures).
**Fix:** Add consistent loading, error, and empty state handling across all pages. Use Suspense boundaries.

### M7. Token board polls every 3 seconds without backoff
**Where:** `hms-frontend/src/app/token-board/page.tsx`
**Problem:** The token board polls `/appointments/token-board` every 3 seconds. If the API fails (network issue, server restart), it continues poll-spamming at 3s intervals with no backoff.
**Fix:** Implement exponential backoff (3s → 6s → 12s → max 30s) on error. Reset interval on success.

### M8. Login form has no CAPTCHA or CSRF protection
**Where:** `hms-frontend/src/app/login/page.tsx`
**Problem:** While rate limiting exists server-side (5 req/15min), there's no CAPTCHA on the login form. Automated brute-force tools can hit the login endpoint until the IP is blocked.
**Fix:** Add Google reCAPTCHA v3 (invisible) or Cloudflare Turnstile on login.

### M9. No exclusive PrismaClient instance (new instance per module)
**Where:** `hms-backend/src/modules/*/` — each route file creates `new PrismaClient()`
**Problem:** Prisma recommends using a single global instance. Multiple instances create unnecessary connection pool overhead and can hit database connection limits.
**Fix:** Create a single PrismaClient singleton in `config/` and import it everywhere.

### M10. Frontend API client doesn't include OPD chambers, consumables, audit endpoints
**Where:** `hms-frontend/src/lib/api.ts`
**Problem:** The `opdChamberApi`, consumables, audit, and settings endpoints are called via raw `axios.get` in the settings page instead of being added to the shared API client. Inconsistent pattern.
**Fix:** Add all missing API endpoints to `api.ts`.

---

## 🟢 Low Priority

### L1. No request size validation for JSON body
**Where:** `hms-backend/src/server.js:107` — `limit: '10mb'`
**Problem:** 10MB JSON body parsing is excessive for an API that primarily sends small payloads. This is a DoS attack vector.
**Fix:** Reduce to 1-2MB. Use a separate larger limit only on the prescription upload endpoint.

### L2. Inefficient summary computation in /appointments/today
**Where:** `hms-backend/src/modules/appointment/appointment.routes.js:337-343`
**Problem:** Summary counts are computed by loading ALL appointments into memory and filtering in JS. For a busy hospital with 500+ appointments/day, this wastes memory and CPU.
**Fix:** Use Prisma aggregation (`_count` with `status` grouping) or separate count queries.

### L3. Prisma enum mismatch with appointment status flow
**Where:** `hms-backend/prisma/schema.prisma` AppointmentStatus enum
**Problem:** The appointment status flow (SCHEDULED → CHECKED_IN → IN_CONSULTATION → COMPLETED) is enforced by business logic, not by the database. There's nothing preventing a direct jump from SCHEDULED to COMPLETED.
**Fix:** Add a state machine validation in a service layer. Alternatively, use a Prisma `@database` enum with PostgreSQL enum type.

### L4. Next.js config exports production IP in client bundle
**Where:** `hms-frontend/next.config.js`
**Problem:** `NEXT_PUBLIC_API_URL` is embedded in the client-side JS bundle at build time. Even if set via env vars, the fallback production IP is visible to anyone who inspects the JS source.
**Fix:** Use `NEXT_PUBLIC_API_URL` exclusively via runtime env vars, not hardcoded in config.

### L5. No consistent error response shape
**Where:** All backend route files
**Problem:** Most responses use `{ success: true, ... }`, but some use different shapes or non-standard error formats. The error handler returns `{ success: false, message: "..." }` but some routes use `{ errors: [...] }`.
**Fix:** Standardize all API responses to `{ success: boolean, data?: any, message?: string, errors?: [...] }`.

### L6. Multiple Prisma schema types not yet used by any module
**Where:** Prisma schema models for Lab, Pharmacy, Inventory, IPD, Notifications
**Problem:** These models are well-designed but completely unused — no backend routes consume them. Schema is "ahead" of implementation.
**Fix:** Either implement the modules or add a validation layer. Consider removing unused models until implementation is ready.

### L7. Empty `uploads/prescriptions/` directory committed to git
**Where:** `uploads/prescriptions/`
**Problem:** Empty directory tracked in version control, presumably with a `.gitkeep`. Should be in `.gitignore` with a proper runtime initialization.
**Fix:** Add to `.gitignore`. Create directory at app startup if it doesn't exist.

### L8. No frontend error boundary
**Where:** Root layout `hms-frontend/src/app/layout.tsx`
**Problem:** No React error boundary wraps the app. A render crash in any page/component will show a white screen or Next.js default error page.
**Fix:** Add a custom ErrorBoundary component with user-friendly fallback UI.

### L9. No meta tags or SEO
**Where:** `hms-frontend/src/app/layout.tsx`
**Problem:** Root layout has minimal metadata. No description, OG tags, favicon configuration.
**Fix:** Add proper metadata export with Next.js 14 Metadata API.

### L10. 401 interceptor has no guard against login page redirect loop
**Where:** `hms-frontend/src/lib/api.ts:27-33`
**Problem:** If the login page itself triggers a 401 (e.g., expired token check), the interceptor redirects to `/login`, causing an infinite loop.
**Fix:** Check `window.location.pathname !== '/login'` before redirecting.

---

## 📋 Suggested Project Board

### Sprint 1 — Foundation & Safety
- [ ] C1: Create `.env.example` + startup config validation
- [ ] C2: Validate `ENCRYPTION_KEY` at startup
- [ ] C3: Validate `JWT_SECRET` at startup
- [ ] C5: Fix ID generator race conditions
- [ ] C6: Add idempotency to check-in transactions
- [ ] M9: Singleton PrismaClient

### Sprint 2 — Testing & Quality
- [ ] C4: Set up test framework (Jest + Supertest for API, Testing Library for frontend)
- [ ] H1: Refactor first module to service/controller pattern
- [ ] M5: Fix silent catch blocks
- [ ] M6: Add loading/error/empty states

### Sprint 3 — Deployment
- [ ] H3: Docker + docker-compose setup
- [ ] H7: Fix prescription upload (S3 or cleanup)
- [ ] H9: Database health checks
- [ ] L1: Reduce body size limit

### Sprint 4 — Security Hardening
- [ ] H4: JWT revocation + limit DISPLAY token lifetime
- [ ] H6: Merge duplicate CheckInModals
- [ ] M8: CAPTCHA on login
- [ ] M4: Remove hardcoded production URL

### Sprint 5 — Architecture
- [ ] H2: Migrate backend to TypeScript
- [ ] H5: Implement or remove stub modules
- [ ] M2: Split settings page
- [ ] M3: Use shared API client consistently
- [ ] M10: Complete API client coverage

### Sprint 6 — Performance & Polish
- [ ] H8: Optimize /doctor/next query pattern
- [ ] M7: Token board exponential backoff
- [ ] L2: Inefficient summary computation
- [ ] L3: State machine validation
- [ ] L8-L10: Error boundaries, SEO, redirect loop fix

---

*Generated from full codebase review. Backend: 26 JS files (~4,845 LOC). Frontend: 59 TS/TSX files. Prisma schema: 1001 lines, 24 models + 15 enums.*
