# MBS Hospital Management System — Project Backlog

> Last updated: 2026-06-05
> Project: MBS Hospital Management System (HMS)
> Stack: Node.js/Express (backend) + Next.js 14/TypeScript (frontend) + PostgreSQL/Prisma
> Production: Backend on EC2 (api.sarvikatech.in) | Frontend on Vercel
> Security score: 100% (34/34 automated tests passing)

---

## ✅ Phase 0 — Completed (Multi-Tenant Architecture)

### MT. Multi-Tenant Foundation
- [x] Tenant model with hospitalId/isolation support across all entities
- [x] tenantMiddleware for request-scoped tenant isolation
- [x] employeeId login support
- [x] New roles: CASHIER, OPD_NURSE, SUPER_ADMIN
- [x] Composite unique indexes (tenantId + entityId)
- [x] Merged to main/master across all 3 repos
- [x] Deployed to production EC2 backend
- [x] Database migration applied (9 migrations, up to date)
- [x] employeeId assigned to all 21 users (ADMIN-001, RECP-001-004, DOC-001-011, DISP-001-005)

---

## ✅ Phase 1 — Completed (Emergency Module)

### 1A. Database Schema (Prisma)
- [x] Medicine model
- [x] BillModificationRequest model (id, billId, billItemId, requestedBy, reason, status, reviewedBy)
- [x] Doctor: emergencyConsultationFee field
- [x] Bill: EMERGENCY BillType, admissionRecommended, confirmedAt, confirmedBy
- [x] BillItem: itemType enum (CONSULTATION/MEDICINE/CONSUMABLE/PROCEDURE/OTHER), isModified
- [x] All new models include tenantId

### 1B. Backend — Emergency Module
- [x] POST /emergency/bills — create emergency bill draft
- [x] POST /emergency/bills/:id/confirm — confirm bill, lock items
- [x] POST /emergency/bills/:id/payment — collect payment
- [x] POST /emergency/bills/:id/items — add item to confirmed bill
- [x] POST /emergency/bills/:id/modify-request — request item modification
- [x] PATCH /emergency/bills/:id/modify-request/:reqId — approve/reject modification
- [x] GET /emergency/bills/pending — cashier dashboard feed
- [x] GET /emergency/bills/today — today's emergency bills
- [x] GET /emergency/bills/:id — single bill detail
- [x] Routing order bug fixed (pending/today routes registered before /:id)

### 1C. Backend — Modified Files
- [x] Auth middleware: CASHIER, OPD_NURSE, SUPER_ADMIN roles
- [x] Doctor routes: emergencyConsultationFee in POST/PATCH
- [x] Billing routes: billType + EMERGENCY support
- [x] server.js: emergency routes registered
- [ ] Notifications: trigger on modification request *(deferred — no notification system yet)*

### 1D. Frontend — New Pages
- [x] Receptionist emergency dashboard (`/emergency`)
- [x] Emergency bill creation form (`/emergency/new`)
- [x] Cashier bill detail view (`/emergency/[billId]`)
- [x] Medicines catalogue management (`/medicines`)

### 1E. Frontend — Modified
- [x] Doctor profile: Emergency Consultation Fee field
- [x] Settings: Emergency section + Medicines Catalogue link
- [x] Navigation: Emergency sidebar link (role-based)
- [x] API client: emergencyApi + medicinesApi exports
- [x] Patient profile: Emergency tab for visit history

### 1F. CASHIER Role
- [x] Route guards: CASHIER restricted to emergency/billing/patients
- [x] Auth middleware + frontend guards (AppLayout, Sidebar, getRoleHomePage)

---

## ✅ Phase 2 — Completed (IPD Module)

### 2A. Database Schema
- [x] Ward model (name, type, dailyRate, isActive)
- [x] Bed model (wardId, bedNumber, status: AVAILABLE/OCCUPIED/MAINTENANCE)
- [x] IPDAdmission model (admissionNumber, patientId, admittingDoctorId, attendingDoctorId, wardId, bedId, status, diagnosis, etc.)
- [x] IPDCharge model (admissionId, chargeType, description, quantity, unitPrice)
- [x] IPDPayment model (admissionId, amount, paymentMethod)
- [x] IPDWardChange model (admissionId, fromWardId, toWardId, fromBedId, toBedId, reason)
- [x] VitalRecord model (admissionId, bp, pulse, temperature, spo2, weight)
- [x] NurseNote model (admissionId, note, authorId)
- [x] IPDModifyRequest model
- [x] DutyRoster / DutyAssignment models
- [x] NurseSuperintendent management
- [x] All models include tenantId

### 2B. Backend — IPD Module
- [x] POST /ipd/admissions — create admission (serializable UHID generation)
- [x] GET /ipd/admissions — list active admissions with filters
- [x] GET /ipd/admissions/:id — full admission detail with charges/payments
- [x] GET /ipd/admissions/:id/bill-summary — live bill with auto bed accrual (optimistic lock)
- [x] POST /ipd/admissions/:id/discharge/initiate — initiate discharge
- [x] POST /ipd/admissions/:id/discharge/confirm — confirm discharge (accrual before balance check)
- [x] POST /ipd/admissions/:id/ward-change — change ward/bed with history
- [x] POST /ipd/admissions/:id/charges — add charge item
- [x] POST /ipd/admissions/:id/payments — record advance/partial/final payment
- [x] POST /ipd/admissions/:id/vitals — record vital signs
- [x] POST /ipd/admissions/:id/notes — add nursing note
- [x] GET /ipd/beds — bed availability grid by ward
- [x] POST /ipd/admissions/:id/modify-request — request charge modification
- [x] PATCH /ipd/admissions/:id/modify-request/:reqId — approve/reject modification
- [x] File upload for IPD prescriptions (magic byte validation, random UUID filename)

### 2C. Backend — Modified Files
- [x] Auth middleware: NURSE, NURSE_SUPERINTENDENT, DUTY_MANAGER restrictions
- [x] Billing routes: IPD billing endpoints + unified bill view
- [x] server.js: IPD routes registered
- [ ] Notifications: discharge, modification requests *(deferred)*

### 2D. Frontend — New Pages
- [x] IPD admissions list (`/ipd`)
- [x] New admission form (`/ipd/new`)
- [x] Admission detail with tabs — Bill, Vitals, Notes, Ward History, Payments (`/ipd/[admissionId]`)
- [x] Bed management grid (`/ipd/beds`)
- [x] Nurse dashboard — assigned patients (`/nurse`)
- [x] Nurse Superintendent dashboard — duty assignment (`/nurse-superintendent`)
- [x] Duty manager dashboard (`/duty-manager`)
- [x] IPD config settings (`/settings/ipd-config`)

### 2E. Frontend — Modified
- [x] Billing page: IPD Billing tab/section
- [x] Patient profile: IPD tab
- [x] Navigation: IPD, Nurse, Nurse Superintendent links
- [x] API client: ipdApi, nurseApi exports
- [x] Auth context: isNurse, isNurseSuperintendent, isCashier, isSuperAdmin helpers

---

## ✅ Phase 3 — Completed (Docker & Deployment Infrastructure)

### 3A. Docker Setup
- [x] Backend Dockerfile — builder, dev, runner (production) stages
- [x] Frontend Dockerfile — dev and production stages
- [x] docker-compose.yml — backend + frontend + PostgreSQL + Redis
- [x] .dockerignore files
- [x] Separate `migrate` service in docker-compose (runs migrations before backend starts)
- [x] Redis password configured (no host port exposure — internal Docker network only)
- [x] Backend modules volume for fast local dev (no rebuild on code change)
- [x] All containers verified running and healthy locally

### 3B. CI/CD
- [ ] GitHub Actions: automated security scan on PR
- [ ] GitHub Actions: automated deploy to EC2 on merge to main
- [ ] Vercel: auto-deploy from main (frontend) — *Vercel handles this automatically*
- [ ] Branch protection rules on main/master

### 3C. Zero-Downtime Deployment *(completed 2026-06-05)*
- [x] Dockerfile production CMD: migrations removed from startup (`node src/server.js` only)
- [x] PM2 ecosystem config (`ecosystem.config.js`) — cluster mode, graceful reload
- [x] Deploy script (`scripts/deploy.sh`) — pull → deps → migrate → `pm2 reload` → health check
- [x] Rollback documented: `pm2 reload` previous image; all migrations must be additive-only

---

## ✅ Phase 4 — Completed (Security & Production Hardening)

> Full pass completed 2026-06 against production-readiness audit.
> Security test suite: **34/34 passing (100%)**.
> Production readiness score improved from 28/100 → 100% on automated tests.

### 4A. Authentication & Session Security
- [x] JWT stored as **httpOnly cookie** (server-set via `res.cookie`) — XSS cannot steal token
- [x] Frontend removed `Cookies.set('hms_token')` — token no longer JS-accessible
- [x] `withCredentials: true` on axios — httpOnly cookie sent automatically
- [x] JWT blocklist via Redis on logout (token revocation)
- [x] Redis blocklist check now **fail-closed** — 503 returned when Redis is down (revoked tokens not accepted)
- [x] Login rate limiter: atomic `INCR` in Redis (eliminates TOCTOU race in old GET+INCR pattern)
- [x] Rate limit fail-open for login logged explicitly (IP-based limiter still active as backup)
- [x] Password change endpoints: dedicated rate limiter (5 req/15 min)
- [x] Login password minimum: 8 chars (was 6)
- [x] Force-change-password and change-password: consistent PASSWORD_REGEX validation
- [x] Temp password removed from reset API response (must be shared out-of-band)
- [x] `UNAUTHORIZED_ACCESS_ATTEMPT` audit action (was `READ`)
- [x] DISPLAY role: blockDisplay enforced per-route (reviewed)

### 4B. Multi-Tenant Isolation
- [x] Emergency module: all 8 routes use `findFirst` with `tenantId: req.tenantId`
- [x] Emergency routing bug: `GET /bills/pending` and `/today` moved before `/:id`
- [x] Audit module: `tenantId: req.tenantId` filter added to all queries
- [x] Doctor module: `GET /doctors` now filters by tenantId
- [x] Doctor module: `PATCH /doctors/:id` uses `findFirst` with tenantId (was `findUnique`)
- [x] Doctor module: `POST /doctors` — user and doctor lookups scoped to tenantId
- [x] Consumables module: 3 `findUnique` calls replaced with `findFirst` + tenant check
- [x] Patient module: doctor cross-access check uses `findFirst` with tenantId
- [x] Reports module: tenantId filter on all findMany queries
- [x] IPD module: admission number generated inside serializable transaction

### 4C. Race Conditions & Data Integrity
- [x] **Payment race condition fixed**: entire read-check-write in `Serializable` transaction — concurrent payments cannot both pass balance check on stale data
- [x] UHID generation: `generateUHID(tx)` accepts transaction client — called inside serializable transaction
- [x] Bill number generation: same pattern
- [x] Admission number generation: same pattern
- [x] IPD bed charge double-accrual: optimistic lock via `updateMany` on `lastAccruedDate`
- [x] IPD discharge: `accrueCurrentBedCharge` called before balance check (not after)
- [x] Emergency bill confirmation: atomic check-and-set pattern

### 4D. File Upload Security
- [x] Billing prescriptions: magic byte validation via `file-type` library (not just MIME header)
- [x] Billing prescriptions: `crypto.randomUUID()` filename (was predictable timestamp+ID)
- [x] IPD prescriptions: same magic byte + UUID filename
- [x] OPD prescriptions: magic byte validation added + UUID filename (was completely missing)
- [x] `/uploads/*` served behind `authenticate` middleware (was publicly accessible)
- [x] Path traversal sanitization on `/uploads` route

### 4E. Infrastructure & Server Hardening
- [x] `NODE_ENV` required at startup — crashes with `[FATAL]` if not set (was defaulting to `'development'`)
- [x] Prisma connection pool: `connection_limit=20`, `pool_timeout=20` configured
- [x] Body size limit: `1mb` (was `10mb`)
- [x] CSP hardened: `connectSrc`, `fontSrc`, `objectSrc: none`, `frameSrc: none`, `manifestSrc`
- [x] Rate limiter: removed dev bypass (`skip: () => isDev`) — applies in all environments
- [x] Graceful shutdown: SIGTERM + SIGINT both handled; HTTP server drained before DB/Redis disconnect
- [x] `cookie-parser` installed and server.js updated for httpOnly cookie support
- [x] Redis Docker container: removed host port binding (internal-only — not exposed to host)

### 4F. Secrets & Configuration
- [x] `.env.docker` removed from git tracking (`git rm --cached`)
- [x] `.gitignore` updated: `.env.*` pattern (excludes `.env.example`)
- [x] Redis password set and configured across docker-compose + backend .env
- [x] Security test T5.1: changed from hardcoded `false` to dynamic `git ls-files` check

### 4G. Dependencies
- [x] Next.js: upgraded `14.1.0` → `14.2.29` (fixes CVE-2025-29927 SSRF in Server Actions)
- [x] `file-type` package installed for magic byte validation
- [x] `cookie-parser` package installed and integrated

### 4H. Database Indexes
- [x] `User`: `@@index([tenantId, isActive])`, `@@index([tenantId, employeeId])`
- [x] `Patient`: `@@index([tenantId, phone])`, `@@index([tenantId, isActive])`, `@@index([tenantId, name])`
- [x] `Appointment`: `@@index([tenantId, appointmentDate])`, `@@index([tenantId, status])`
- [x] `Bill`: `@@index([tenantId, paymentStatus])`, `@@index([tenantId, billType])`
- [x] `IPDAdmission`: `@@index([tenantId, status])`, `@@index([tenantId, patientId])`

### 4I. Error Handling & Observability
- [x] Production error responses: stack trace hidden, generic message returned
- [x] Prisma P2002/P2025 errors caught and sanitized
- [x] Request ID (`uuid.v4()`) attached to every request for log tracing

---

## 🔴 Phase 5 — Remaining Security Items (Must Fix Before Heavy Production Load)

### 5A. Critical / High (block scale-up)
- [ ] **MFA/2FA**: TOTP-based second factor for ADMIN and DOCTOR roles (Google Authenticator compatible)
- [ ] **Redis TLS**: change `REDIS_URL` from `redis://` to `rediss://` for encrypted traffic in production
- [ ] **CI/CD security gate**: GitHub Actions — run `node ws/security-test-suite.js` on every PR; block merge on failure
- [ ] **Secrets rotation**: rotate JWT_SECRET (`openssl rand -hex 64`), ENCRYPTION_KEY, re-encrypt all Aadhaar fields with new key
- [ ] **Git history purge**: `git filter-repo --path hms-backend/.env.docker --invert-paths` to remove secrets from history on all branches
- [ ] **Token board auth**: `GET /appointments/token-board` and `/:doctorId` currently unauthenticated — add DISPLAY role auth or signed API key
- [ ] **Appointment module**: 11 `findUnique` calls without tenantId filter (flagged in audit scan) — review and fix individually

### 5B. Medium (fix within 2 weeks of go-live)
- [ ] **Password history**: store last 5 bcrypt hashes per user; reject reuse
- [ ] **Session timeout UI**: show countdown 5 min before JWT expiry; auto-logout with warning modal
- [ ] **Confirmation dialogs**: add to all destructive actions (deactivate user, cancel appointment, delete record)
- [ ] **PII in audit logs**: log only IDs; resolve names at display time (DPDPA compliance)
- [ ] **Email in staff registration response**: remove email from `POST /auth/register` response body
- [ ] **Request ID in response headers**: include `X-Request-ID` in all responses for client-side tracing
- [ ] **Upload rate limiting**: add rate limit middleware to all file upload endpoints (prevent storage exhaustion)
- [ ] **Emergency bill confirmation race**: add optimistic lock on `confirmedAt` field
- [ ] **Morgan log sanitization**: strip `password` field from morgan dev logs

### 5C. Low / Operational
- [ ] **HSTS explicit config**: add `helmet.hsts({ maxAge: 31536000, includeSubDomains: true })`
- [ ] **Winston log rotation**: configure `winston-daily-rotate-file` with 30-day retention
- [ ] **Audit log failure alerting**: alert ops when consecutive audit writes fail (NABH compliance gap)
- [ ] **`.nvmrc`**: pin `20` for consistent local dev
- [ ] **ESLint no-unused-vars**: clean up unused variable warnings across route files

---

## 🟡 Phase 6 — Compliance & Legal

### 6A. DPDPA 2023
- [x] Consent captured and logged at patient registration
- [x] Aadhaar encrypted at rest (AES-256-GCM)
- [x] Data export/deletion request endpoint (`POST /patients/:id/data-request`)
- [ ] **Deletion workflow**: automated GDPR/DPDPA right-to-deletion — anonymize PII on approved DELETION request (currently creates request record but no processing)
- [ ] **Data export workflow**: generate structured export (JSON/PDF) of patient data on approved EXPORT request
- [ ] **Consent re-capture**: prompt for re-consent if patient data purpose changes

### 6B. NABH / Clinical
- [ ] **Audit log retention**: enforce minimum 7-year retention policy (currently no enforcement)
- [ ] **Access review report**: monthly report of who accessed what (for NABH audit)
- [ ] **Prescription audit trail**: track every change to prescription content

### 6C. PCI-DSS (if card payments processed)
- [ ] **Payment tokenization**: do not store raw card data — use Razorpay/Stripe tokenization
- [ ] **PCI scope assessment**: determine if HMS is in-scope for PCI-DSS

---

## 🔵 Phase 7 — Stub Modules (Future)

> These modules exist as stubs in the sidebar. No backend implementation yet.

### 7A. Inventory Module
- [ ] Consumables/medicines stock tracking
- [ ] Purchase order management
- [ ] Stock alerts (low inventory)
- [ ] Integration with billing (auto-deduct on use)

### 7B. Lab Module
- [ ] Lab test order management
- [ ] Result entry and upload
- [ ] Integration with OPD/IPD visit
- [ ] Lab report PDF generation

### 7C. Pharmacy Module
- [ ] Prescription fulfillment workflow
- [ ] Medicine dispensing records
- [ ] Integration with medicines catalogue
- [ ] Stock deduction on dispense

### 7D. Notification System
- [ ] In-app notification bell (WebSocket or polling)
- [ ] SMS via AWS SNS or Twilio — discharge, appointment reminders
- [ ] Triggers: bill modification requests, duty assignments, discharge, appointment status changes

### 7E. Reporting & Analytics
- [ ] Revenue reports (daily/monthly/yearly)
- [ ] Patient statistics (OPD/IPD/Emergency footfall)
- [ ] Doctor-wise revenue and patient count
- [ ] Bed occupancy rate chart
- [ ] Export to Excel/PDF

---

## 🟠 Phase 8 — Operational Excellence

### 8A. Monitoring & Observability
- [ ] **Sentry**: error tracking + performance monitoring (frontend + backend)
- [ ] **CloudWatch / Datadog**: server metrics (CPU, memory, disk, request rate)
- [ ] **Uptime monitoring**: external health check every 60s (UptimeRobot / Better Uptime)
- [ ] **Alert rules**: error rate > 1%, p99 latency > 2s, disk > 80%, Redis down

### 8B. Testing
- [ ] **Backend unit tests**: Jest + Supertest — auth, billing, patient, IPD core flows
- [ ] **Frontend E2E**: Playwright — login, patient registration, appointment booking, OPD visit, billing
- [ ] **CI test gate**: PR blocked if tests fail
- [ ] **Load test**: k6 or Artillery — 50 concurrent users, peak scenario (morning OPD rush)

### 8C. Staging Environment
- [ ] Staging EC2 (smaller instance — t3.small)
- [ ] Staging DB (RDS t3.micro)
- [ ] GitHub Actions: auto-deploy to staging on PR merge to `develop`
- [ ] Production deploy: manual trigger after staging validation

### 8D. Backup & Recovery
- [ ] RDS automated backups: 7-day retention (verify currently enabled)
- [ ] Point-in-time recovery tested — document RTO/RPO
- [ ] Runbooks: DB failure, Redis failure, EC2 failure, rollback procedure

---

## Infrastructure

| Component | Location | Details |
|---|---|---|
| Backend API | AWS EC2 ap-south-1 | https://api.sarvikatech.in \| PM2 cluster mode |
| Frontend | Vercel | Next.js 14.2.29 |
| Database | AWS RDS PostgreSQL ap-south-1 | hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com |
| Redis | Same EC2 as backend | localhost:6379 (password-protected) |
| Git Parent | GitHub | https://github.com/jotirmoymajumder195/project-hms |
| Git Backend | GitHub | https://github.com/jotirmoymajumder195/hms-backend |
| Git Frontend | GitHub | https://github.com/jotirmoymajumder195/hms-frontend |

### Active branches
| Branch | Purpose |
|---|---|
| `Jotirmoy` | Main dev branch — backend + frontend submodules |
| `joti` | Mirror — kept in sync with Jotirmoy |
| `master` | Production base |

---

## Known Credentials (Production)

| Employee ID | Role | Name |
|---|---|---|
| ADMIN-001 | ADMIN | Hospital Administrator |
| RECP-001 to RECP-004 | RECEPTION | Reception Staff |
| DOC-001 to DOC-011 | DOCTOR | Various Doctors |
| DISP-001 to DISP-005 | DISPLAY | TV/Token Board Users |

---

## Security Posture Summary (as of 2026-06-05)

| Category | Status | Notes |
|---|---|---|
| Authentication | ✅ Strong | httpOnly JWT, Redis blocklist fail-closed, rate limiting |
| Tenant Isolation | ✅ Fixed | All critical modules patched; appointment module still has warnings |
| File Upload | ✅ Hardened | Magic bytes + UUID names on all 3 upload endpoints |
| Race Conditions | ✅ Fixed | Payment, UHID, admission number, bed accrual all atomic |
| Secrets | ✅ Clean | .env.docker removed from git; git history purge pending |
| Dependencies | ✅ Updated | Next.js 14.2.29; no critical CVEs in production deps |
| Deployment | ✅ Zero-downtime | PM2 cluster + separate migrate step + deploy script |
| MFA | ❌ Not implemented | Highest priority remaining security item |
| CI/CD security gate | ❌ Not implemented | Must run security-test-suite.js on PR |
| Redis TLS | ❌ Plaintext | `redis://` → `rediss://` needed in production |
| GDPR deletion | ⚠️ Partial | Request captured; workflow not automated |
| Automated tests | ❌ Zero | No Jest/Playwright tests exist |
