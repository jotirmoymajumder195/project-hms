# MBS Hospital Management System — Project Backlog

> Last updated: 2026-05-12
> Project: MBS Hospital Management System (HMS)
> Stack: Node.js/Express (backend) + Next.js 14/TypeScript (frontend) + PostgreSQL/Prisma
> Production: Backend on EC2 (api.sarvikatech.in) | Frontend on Vercel

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

## 🚀 Phase 1 — Emergency Module (NEXT UP)

> Based on: `Emergency_Workflow_Requirements.pdf` & `Emergency_Technical_Changes.pdf`
> Build order: Emergency → IPD (IPD depends on Emergency being done first)

### 1A. Database Schema (Prisma)
- [x] Medicine model (already exists in schema)
- [x] BillModificationRequest model (id, billId, billItemId, requestedBy, reason, status, reviewedBy)
- [x] Doctor: emergencyConsultationFee field (already exists in schema)
- [x] Bill: add EMERGENCY to BillType enum, admissionRecommended, confirmedAt, confirmedBy
- [x] BillItem: add itemType enum (CONSULTATION/MEDICINE/CONSUMABLE/PROCEDURE/OTHER), isModified
- [x] All new models to include tenantId from day one

### 1B. Backend — New Module: emergency/
- [x] Create `/api/v1/emergency/bills` — POST (create emergency bill draft)
- [x] Create `/api/v1/emergency/bills/:id/confirm` — POST (confirm bill, lock items)
- [x] Create `/api/v1/emergency/bills/:id/payment` — POST (collect payment)
- [x] Create `/api/v1/emergency/bills/:id/items` — POST (add item to confirmed bill)
- [x] Create `/api/v1/emergency/bills/:id/modify-request` — POST (request item modification)
- [x] Create `/api/v1/emergency/bills/:id/modify-request/:reqId` — PATCH (approve/reject)
- [x] Create `/api/v1/emergency/bills/pending` — GET (cashier dashboard feed)
- [x] Create `/api/v1/emergency/bills/today` — GET (today's emergency bills)
- [x] Create `/api/v1/emergency/bills/:id` — GET (single bill detail)

### 1C. Backend — Modify Existing Files
- [x] Auth middleware: Add CASHIER, OPD_NURSE, SUPER_ADMIN to ROLES — (already existed) 
- [x] Doctor routes: Add emergencyConsultationFee to POST/PATCH /doctors
- [x] Billing routes: Add billType and EMERGENCY support
- [ ] Notifications: Trigger notification on modification request (deferred — no notification system yet)
- [x] server.js: Register emergency/ routes

### 1D. Frontend — New Pages
- [x] Receptionist emergency dashboard (`/emergency`)
- [x] Emergency bill creation form (`/emergency/new`)
- [x] Cashier bill detail view (`/emergency/[billId]`)
- [x] Medicines catalogue management (`/medicines`)

### 1E. Frontend — Modify Existing
- [x] Doctor profile: Add Emergency Consultation Fee field
- [x] Settings page: Add Emergency section + Medicines Catalogue link
- [x] Navigation: Add Emergency sidebar link (role-based)
- [x] API client: Add emergencyApi + medicinesApi exports
- [x] Patient profile: Add Emergency tab for visit history

### 1F. New Role: CASHIER
- [x] Route guards: Restrict CASHIER to emergency/billing/patients only
- [x] Auth middleware + frontend guards (AppLayout ROUTE_PERMISSIONS, Sidebar navItems, getRoleHomePage)

---

## 🏥 Phase 2 — IPD Module

> Based on: `IPD_Workflow_Requirements.pdf` & `IPD_Technical_Changes.pdf`
> Depends on: Emergency module being complete

### 2A. Database Schema (Prisma)
- [ ] WardType model (name, dailyRate, hourlyRate, isActive)
- [ ] Bed model (wardTypeId, bedNumber, status: AVAILABLE/OCCUPIED/MAINTENANCE)
- [ ] NurseDepartment model (name, isActive)
- [ ] NurseDutyAssignment model (nurseId, departmentId, date)
- [ ] IPDAdmission model (ipdId, patientId, doctorId, wardTypeId, bedId, status, diagnosis, etc.)
- [ ] IPDBillItem model (admissionId, itemType, description, quantity, unitPrice)
- [ ] IPDPayment model (admissionId, amount, type: ADVANCE/PARTIAL/FINAL)
- [ ] IPDWardChange model (admissionId, fromWard, toWard, reason)
- [ ] VitalRecord model (admissionId, bp, pulse, temperature, spo2)
- [ ] NurseNote model (admissionId, note)
- [ ] Bill model: Add ipdAdmissionId FK
- [ ] All models to include tenantId

### 2B. Backend — New Module: ipd/
- [ ] POST /ipd/admissions — Create IPD admission
- [ ] GET /ipd/admissions — List active admissions
- [ ] GET /ipd/admissions/:id — Full admission detail
- [ ] PATCH /ipd/admissions/:id — Update admission / initiate discharge
- [ ] POST /ipd/admissions/:id/discharge — Complete discharge
- [ ] POST /ipd/admissions/:id/ward-change — Change ward/bed
- [ ] POST /ipd/admissions/:id/bill-items — Add item to ongoing bill
- [ ] POST /ipd/admissions/:id/payments — Record payment
- [ ] POST /ipd/admissions/:id/vitals — Record vitals
- [ ] POST /ipd/admissions/:id/notes — Add nursing note
- [ ] GET /ipd/beds — Bed availability grid
- [ ] POST /ipd/duty-assignments — Assign nurse to department
- [ ] GET /ipd/duty-assignments — List duty assignments

### 2C. Backend — Modify Existing
- [ ] Auth middleware: Add NURSE, NURSE_SUPERINTENDENT restrictions
- [ ] Billing routes: Add IPD billing section endpoints
- [ ] Notifications: Trigger on bill modification, role changes, discharge
- [ ] server.js: Register ipd/ routes

### 2D. Frontend — New Pages
- [ ] IPD main page with active admissions list (`/ipd`)
- [ ] New admission form (`/ipd/new`)
- [ ] Admission detail with tabs (Bill, Vitals, Notes, Ward History, Payments) (`/ipd/[admissionId]`)
- [ ] Bed management grid (`/ipd/beds`)
- [ ] Nurse dashboard (assigned patients) (`/nurse`)
- [ ] Nurse Superintendent dashboard (duty assignment) (`/nurse-superintendent`)
- [ ] IPD config settings (`/settings/ipd-config`)

### 2E. Frontend — Modify Existing
- [ ] Billing page: Add IPD Billing tab/section
- [ ] Patient profile: Add IPD tab
- [ ] Navigation: Add IPD, Nurse, Nurse Superintendent links
- [ ] API client: Add ipdApi, nurseApi exports
- [ ] Auth context: Add isNurse, isNurseSuperintendent, isCashier, isSuperAdmin helpers

---

## 🐳 Phase 3 — Docker & Deployment Infrastructure

### 3A. Docker Setup
- [ ] Backend Dockerfile (Node.js 20, production build)
- [ ] Frontend Dockerfile (Next.js build + serve)
- [ ] docker-compose.yml (backend + frontend + PostgreSQL + Redis)
- [ ] .dockerignore files
- [ ] Environment-specific docker-compose.override.yml
- [ ] Test Docker setup locally

### 3B. CI/CD
- [ ] GitHub Actions for automated testing on PR
- [ ] GitHub Actions for automated deployment to EC2
- [ ] Vercel auto-deploy from main (frontend)

---

## 🔧 Phase 4 — Code Quality & Safety (from Code Review)

### Sprint 4A — Foundation & Safety
- [ ] C1: Create `.env.example` + startup config validation
- [ ] C2: Validate `ENCRYPTION_KEY` at startup
- [ ] C3: Validate `JWT_SECRET` at startup
- [ ] C5: Fix ID generator race conditions (use DB sequences)
- [ ] C6: Add idempotency to check-in transactions
- [ ] M9: Singleton PrismaClient

### Sprint 4B — Testing & Quality
- [ ] C4: Set up test framework (Jest + Supertest + Testing Library)
- [ ] H1: Refactor first module to service/controller pattern
- [ ] M5: Fix silent catch blocks
- [ ] M6: Add loading/error/empty states

### Sprint 4C — Security Hardening
- [ ] H4: JWT revocation + limit DISPLAY token lifetime
- [ ] H6: Merge duplicate CheckInModals
- [ ] M8: CAPTCHA on login
- [ ] M4: Remove hardcoded production URL from codebase

### Sprint 4D — Architecture & Performance
- [ ] H2: Migrate backend to TypeScript (incremental)
- [ ] H5: Implement or remove stub modules (inventory, lab, pharmacy)
- [ ] M2: Split settings page into components
- [ ] M3: Use shared API client consistently
- [ ] M10: Complete API client coverage
- [ ] H8: Optimize /doctor/next query pattern
- [ ] M7: Token board exponential backoff
- [ ] L2: Inefficient summary computation

### Sprint 4E — Polish
- [ ] H7: Fix prescription upload (S3 or cleanup)
- [ ] H9: Database health checks in /health endpoint
- [ ] L1: Reduce body size limit
- [ ] M1: Audit helper fallback (Winston file transport)
- [ ] L3: State machine validation for appointment status
- [ ] L8: Error boundary
- [ ] L9: Meta tags / SEO
- [ ] L10: 401 redirect loop guard
- [ ] L4-L7: Minor fixes

---

## Known Credentials (Production)

| Employee ID | Role | Name |
|---|---|---|
| ADMIN-001 | ADMIN | Hospital Administrator |
| RECP-001 | RECEPTION | Staff 1 |
| RECP-002 | RECEPTION | Staff 2 |
| RECP-003 | RECEPTION | Staff 3 |
| RECP-004 | RECEPTION | Test Receptionist |
| DOC-001 to DOC-011 | DOCTOR | Various doctors |
| DISP-001 to DISP-005 | DISPLAY | Display/TV users |

---

## Infrastructure

| Component | Location | URL |
|---|---|---|
| Backend API | AWS EC2 (ap-south-1) | https://api.sarvikatech.in |
| Frontend | Vercel | (Vercel URL) |
| Database | AWS RDS PostgreSQL (ap-south-1) | hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com |
| Redis | Same EC2 | localhost:6379 |
| Git Parent | GitHub | https://github.com/jotirmoymajumder195/project-hms |
| Git Backend | GitHub | https://github.com/jotirmoymajumder195/hms-backend |
| Git Frontend | GitHub | https://github.com/jotirmoymajumder195/hms-frontend |
