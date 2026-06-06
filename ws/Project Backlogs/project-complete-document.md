# MBS Hospital Management System (HMS) — Complete Project Document

> **Current branch:** `joti` (all Phase 1 Emergency Module work)
> **Last updated:** 2026-05-11
> **Stack:** Node.js/Express (backend, plain JS) + Next.js 14/TypeScript (frontend) + PostgreSQL/Prisma ORM + Redis
> **Production:** Backend on AWS EC2 (api.sarvikatech.in) | Frontend on Vercel

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Infrastructure & DevOps](#2-infrastructure--devops)
3. [Multi-Tenant Architecture](#3-multi-tenant-architecture)
4. [Database Schema (Prisma)](#4-database-schema-prisma)
5. [Backend Architecture](#5-backend-architecture)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Roles & Permissions](#7-roles--permissions)
8. [Business Workflows](#8-business-workflows)
9. [Emergency Module (Phase 1)](#9-emergency-module-phase-1)
10. [IPD Module (Phase 2 — Planned)](#10-ipd-module-phase-2--planned)
11. [Employee ID Generation](#11-employee-id-generation)
12. [Known Credentials](#12-known-credentials)
13. [Project Backlog](#13-project-backlog)
14. [Appendix: All Backend API Endpoints](#14-appendix-all-backend-api-endpoints)
15. [Appendix: All Frontend Pages](#15-appendix-all-frontend-pages)
16. [Recent Changes (joti branch)](#16-recent-changes-joti-branch)
17. [UAT Summary](#17-uat-summary)

---

## 1. Project Overview

MBS HMS is a comprehensive hospital management system designed for Indian hospitals, built with a multi-tenant architecture. It covers:

- **OPD Management** – Appointments, walk-ins, token queue, doctor consultation
- **Emergency Department** – Emergency billing, cashier collection, modification requests with admin approval
- **Billing & Payments** – OPD, Emergency bills, payment collection
- **Patient Management** – Registration, visit history, emergency history
- **Doctor Management** – Profiles, schedules, chamber assignments
- **Lab & Diagnostics** – Lab test catalogue, order management
- **Pharmacy** – Medicine catalogue with stock/batch management
- **IPD (In-Patient)** – Wards, beds, admissions, discharge (Phase 2)
- **Daycare** – Same-day procedure admissions
- **Reports** – Summary, analytics
- **Settings** – Staff management, consumables, chambers, emergency config
- **Token Board** – Live display for patient queue
- **Compliance (DPDPA 2023)** – Consent logging, data export/deletion requests, audit trail

### Key Design Decisions

- **Multi-tenant isolation**: Every model has a `tenantId` field. All queries are scoped by tenant. Login uses `tenantId` + `employeeId` (not email).
- **Auto-generated Employee IDs**: Format `MBS{ROLE}{YEAR}{SEQ}` e.g. `MBSRECP2026001`. Generated server-side on user creation.
- **No separate Emergency form**: Emergency bill creation is integrated into the billing page via a bill type selector.
- **Cashier is limited**: Cashier sees only Billing + Patients. No sidebar access to other modules.
- **Bill modification needs admin approval**: After confirmation, any item changes require creating a `BillModificationRequest` that an admin must approve.
- **Interactive Prisma transactions** preferred over batch array form for reliability.
- **JWT auth** with 8h expiry, bcrypt (cost 12) password hashing.

---

## 2. Infrastructure & DevOps

| Component | Location | URL / Details |
|---|---|---|
| **Backend API** | AWS EC2 (ap-south-1) | `https://api.sarvikatech.in` |
| **Frontend** | Vercel | Vercel deployment URL |
| **Database** | AWS RDS PostgreSQL (ap-south-1) | `hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com` |
| **Redis** | Same EC2 | `localhost:6379` (session, queue tokens, rate limiting) |
| **Git Parent** | GitHub | `https://github.com/jotirmoymajumder195/project-hms` |
| **Git Backend** | GitHub | `https://github.com/jotirmoymajumder195/hms-backend` |
| **Git Frontend** | GitHub | `https://github.com/jotirmoymajumder195/hms-frontend` |

### Deployment Process

1. **Backend**: Commit to `main` → push to GitHub → SSM into EC2 → `export HOME=/home/ubuntu` → `cd /home/ubuntu/hms-backend && git pull && npm install && npx prisma generate && pm2 restart hms-backend`
2. **Frontend**: Commit to `main` → push to GitHub → Vercel auto-deploys from main branch
3. **DB Migrations**: Run via `npx prisma migrate deploy` or apply raw SQL via SSM for emergency/patch migrations. Current production DB has schema changes applied manually via raw SQL (NOT through Prisma migrate).

### Local Development

- Backend: `http://localhost:5000` (run `node src/server.js` from `hms-backend/`)
- Frontend: `http://localhost:3000` (run `npx next dev` from `hms-frontend/`)
- Local DB: `postgresql://hms_user:strongpassword@localhost:5432/hms_db`
- Redis: `redis://localhost:6379`

---

## 3. Multi-Tenant Architecture

### Tenant Model

Every tenant gets their own isolated data. The `Tenant` model serves as the root:

- **Tenant** (`tenants`): `id` (UUID), `name`, `subdomain` (unique), `settings` (JSON), `isActive`
- **38 other models** all have `tenantId` + `@@index([tenantId])` + `@@map("table_name")`

### Tenant Middleware

- `tenantMiddleware` extracts tenant from `x-tenant-id` header
- Attaches `req.tenantId` for use in all downstream queries
- Applied to login route (user provides tenant via `x-tenant-id` header or tenant field in login form)

### Login Flow

1. User provides `employeeId` + `password` + tenant (via `x-tenant-id` header + form field)
2. Backend queries `User` by `[tenantId, employeeId]` composite unique
3. Validates password with bcrypt
4. Returns JWT token (contains `userId`, `role`, `tenantId`)
5. Frontend stores token in `hms_token` cookie, tenant in `hms_tenant` cookie

### Unique Constraints Pattern

All unique identifiers are scoped by tenant:
- `@@unique([tenantId, employeeId])` for users
- `@@unique([tenantId, email])` for users
- `@@unique([tenantId, uhid])` for patients
- `@@unique([tenantId, billNumber])` for bills
- `@@unique([tenantId, admissionNumber])` for IPD admissions
- `@@unique([tenantId, daycareNumber])` for daycare admissions
- `@@unique([tenantId, opdNumber])` for OPD registrations
- `@@unique([tenantId, name])` for lab tests and OPD chambers

---

## 4. Database Schema (Prisma)

**Total: 40 models, 21 enums, 1210 lines**

### Enums (21)

| Enum | Values |
|---|---|
| `Role` | `ADMIN`, `RECEPTION`, `DOCTOR`, `LAB`, `PHARMACIST`, `PATIENT`, `DISPLAY`, `CASHIER`, `OPD_NURSE`, `SUPER_ADMIN` |
| `Gender` | `MALE`, `FEMALE`, `OTHER`, `PREFER_NOT_TO_SAY` |
| `BloodGroup` | `A_POS`, `A_NEG`, `B_POS`, `B_NEG`, `AB_POS`, `AB_NEG`, `O_POS`, `O_NEG`, `UNKNOWN` |
| `AppointmentStatus` | `SCHEDULED`, `CHECKED_IN`, `IN_CONSULTATION`, `COMPLETED`, `CANCELLED`, `NO_SHOW` |
| `VisitType` | `OPD`, `EMERGENCY`, `FOLLOW_UP` |
| `PaymentStatus` | `PENDING`, `PARTIALLY_PAID`, `PAID`, `REFUNDED`, `WAIVED` |
| `BillType` | `OPD`, `EMERGENCY`, `IPD`, `LAB`, `PHARMACY` |
| `ItemType` | `CONSULTATION`, `MEDICINE`, `CONSUMABLE`, `PROCEDURE`, `OTHER` |
| `ModificationStatus` | `PENDING`, `APPROVED`, `REJECTED` |
| `PaymentMethod` | `CASH`, `CARD`, `UPI`, `NETBANKING`, `INSURANCE`, `TPA` |
| `LabOrderStatus` | `ORDERED`, `SAMPLE_COLLECTED`, `PROCESSING`, `COMPLETED`, `CANCELLED` |
| `IPDStatus` | `ADMITTED`, `DISCHARGED`, `TRANSFERRED`, `DECEASED` |
| `BedStatus` | `AVAILABLE`, `OCCUPIED`, `UNDER_MAINTENANCE`, `RESERVED` |
| `BedType` | `GENERAL`, `SEMI_PRIVATE`, `PRIVATE`, `ICU`, `NICU`, `HDU` |
| `NotificationType` | `APPOINTMENT_REMINDER`, `REPORT_READY`, `BILL_GENERATED`, `DISCHARGE_SUMMARY`, `LOW_STOCK_ALERT`, `GENERAL` |
| `NotificationChannel` | `SMS`, `WHATSAPP`, `EMAIL`, `IN_APP` |
| `AuditAction` | `CREATE`, `READ`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, `EXPORT`, `PRINT` |
| `ConsentPurpose` | `DATA_COLLECTION`, `TREATMENT`, `SHARING_LAB`, `MARKETING` |
| `DataRequestType` | `EXPORT`, `DELETION`, `CORRECTION` |
| `DataRequestStatus` | `PENDING`, `IN_PROGRESS`, `COMPLETED`, `REJECTED` |
| `DaycareStatus` | `ADMITTED`, `PROCEDURE_IN_PROGRESS`, `PROCEDURE_DONE`, `DISCHARGED`, `CANCELLED` |

### Models (40) — Grouped by Module

#### Tenant & Users (Module 1)
| Model | Table | Key Fields | Relations |
|---|---|---|---|
| `Tenant` | `tenants` | `id`, `name`, `subdomain`, `settings` | → all models |
| `User` | `users` | `id`, `tenantId`, `employeeId`, `name`, `email?`, `phone?`, `passwordHash`, `role`, `isActive`, `mustChangePassword`, `lastLoginAt?` | → Doctor, AuditLog |

#### Patient Management (Module 2)
| Model | Table | Key Fields |
|---|---|---|
| `Patient` | `patients` | `id`, `tenantId`, `uhid`, `name`, `phone`, `dateOfBirth?`, `gender`, `bloodGroup`, `abhaNumber?`, `aadhaarEncrypted?` |

#### Compliance / DPDPA 2023
| Model | Table | Purpose |
|---|---|---|
| `ConsentLog` | `consent_logs` | Patient consent for data use |
| `DataRequest` | `data_requests` | Export/deletion/correction requests |
| `AuditLog` | `audit_logs` | All auditable actions with `userId`, `action`, `resource`, `details` |

#### Doctor Management (Module 3)
| Model | Table | Key Fields |
|---|---|---|
| `Doctor` | `doctors` | `tenantId`, `userId`, `specialization`, `consultationFee`, `followUpFee`, `emergencyConsultationFee?`, `isOPD`, `isEmergency`, `isIPD` |
| `DoctorSchedule` | `doctor_schedules` | `tenantId`, `doctorId`, `dayOfWeek`, `startTime`, `endTime`, `slotMinutes`, `scheduleType` |

#### Appointments & Queue (Module 4)
| Model | Table | Key Fields |
|---|---|---|
| `Appointment` | `appointments` | `tenantId`, `patientId`, `doctorId`, `appointmentDate`, `slotTime`, `tokenNumber`, `visitType`, `status` |
| `OPDRegistration` | `opd_registrations` | `tenantId`, `opdNumber`, `patientId` (unique) |
| `DoctorQueue` | `doctor_queues` | `tenantId`, `doctorId` (unique), `currentToken`, `isActive` |
| `OPDChamber` | `opd_chambers` | `tenantId`, `name` |
| `OPDChamberAssignment` | `opd_chamber_assignments` | `tenantId`, `chamberId`, `doctorId`, `dayOfWeek?` |

#### OPD Visit (Module 5)
| Model | Table | Key Fields |
|---|---|---|
| `OPDVisit` | `opd_visits` | `tenantId`, `patientId`, `doctorId`, `visitDate`, `chiefComplaint?`, `vitalSigns?`, `diagnosis?`, `isCompleted` |

#### Prescription (Module 6)
| Model | Table | Key Fields |
|---|---|---|
| `Prescription` | `prescriptions` | `tenantId`, `visitId`, `doctorId`, `patientId` |
| `PrescriptionMedicine` | `prescription_medicines` | `prescriptionId`, `medicineName`, `dosage`, `frequency`, `duration` |

#### Billing & Payments (Module 7)
| Model | Table | Key Fields |
|---|---|---|
| `Bill` | `bills` | `tenantId`, `billNumber`, `patientId`, `billType`, `admissionRecommended`, `confirmedAt?`, `subtotal`, `totalAmount`, `paidAmount`, `balanceAmount`, `paymentStatus` |
| `BillItem` | `bill_items` | `tenantId`, `billId`, `itemType`, `itemName`, `quantity`, `unitPrice`, `totalPrice`, `isModified` |
| `BillModificationRequest` | `bill_modification_requests` | `tenantId`, `billId`, `billItemId`, `requestedBy`, `reason`, `newItemName?`, `newQuantity?`, `newUnitPrice?`, `status`, `reviewedBy?` |
| `Payment` | `payments` | `tenantId`, `billId`, `amount`, `paymentMethod`, `receivedBy` |

#### Lab (Module 8)
| Model | Table |
|---|---|
| `LabTest` | `lab_tests` |
| `LabOrder` | `lab_orders` |
| `LabOrderItem` | `lab_order_items` |

#### Pharmacy (Module 9)
| Model | Table |
|---|---|
| `Medicine` | `medicines` |
| `MedicineBatch` | `medicine_batches` |
| `MedicineDispense` | `medicine_dispenses` |
| `MedicineDispenseItem` | `medicine_dispense_items` |

#### Inventory (Module 10)
| Model | Table |
|---|---|
| `InventoryItem` | `inventory_items` |
| `InventoryTransaction` | `inventory_transactions` |

#### IPD (Module 11 — Phase 2)
| Model | Table |
|---|---|
| `Ward` | `wards` |
| `Bed` | `beds` |
| `IPDAdmission` | `ipd_admissions` |
| `BedAllocation` | `bed_allocations` |

#### Daycare (Module 13)
| Model | Table |
|---|---|
| `DaycareAdmission` | `daycare_admissions` |
| `DaycareProcedure` | `daycare_procedures` |
| `DaycareBill` | `daycare_bills` |

#### Auxiliary
| Model | Table | Purpose |
|---|---|---|
| `Consumable` | `consumables` | Consumables catalogue |
| `VisitConsumable` | `visit_consumables` | Consumables used per visit |
| `Notification` | `notifications` | Outgoing SMS/WhatsApp/Email |
| `HospitalSettings` | `hospital_settings` | Per-tenant hospital config |

---

## 5. Backend Architecture

### Tech Stack
- **Runtime**: Node.js
- **Framework**: Express.js (plain JavaScript, not TypeScript)
- **ORM**: Prisma 5.22.0
- **Database**: PostgreSQL
- **Cache**: Redis (via ioredis)
- **Auth**: JWT (jsonwebtoken) + bcryptjs
- **Validation**: express-validator
- **Logging**: Winston + Morgan
- **Security**: Helmet, CORS, rate-limit (express-rate-limit)

### Directory Structure

```
hms-backend/
├── prisma/
│   ├── schema.prisma          # Full database schema
│   ├── seed.js                # Seed data
│   └── migrations/            # Prisma migrations
├── src/
│   ├── config/
│   │   ├── index.js           # Central config (reads env vars)
│   │   └── redis.js           # Redis client setup
│   ├── middleware/
│   │   ├── auth.js            # Authentication + authorization middleware
│   │   └── errorHandler.js    # Global error handler
│   ├── modules/
│   │   ├── appointment/       # Appointment management
│   │   ├── audit/             # Audit log queries
│   │   ├── auth/              # Login, register, user management
│   │   ├── billing/           # Bill creation and management
│   │   ├── consumables/       # Consumables catalogue
│   │   ├── doctor/            # Doctor profiles, schedules, slots
│   │   ├── emergency/         # Emergency billing (Phase 1)
│   │   ├── inventory/         # Inventory management
│   │   ├── ipd/               # IPD (stub — Phase 2)
│   │   ├── lab/               # Lab (stub)
│   │   ├── medicines/         # Medicine catalogue
│   │   ├── notifications/     # Notifications (stub)
│   │   ├── opd/               # OPD visit management
│   │   ├── opd-chambers/      # Chamber + session management
│   │   ├── patient/           # Patient CRUD
│   │   ├── pharmacy/          # Pharmacy (stub)
│   │   └── reports/           # Reports
│   ├── utils/
│   │   ├── auditHelper.js     # Audit log helper
│   │   ├── encryption.js      # Aadhaar encryption
│   │   ├── errors.js          # AppError class
│   │   ├── idGenerators.js    # ID generators
│   │   └── logger.js          # Winston logger
│   └── server.js              # Entry point
```

### Key Configuration

**`src/config/index.js`** reads from `process.env`:
- `NODE_ENV`, `PORT`, `FRONTEND_URL`
- `JWT_SECRET`, `JWT_EXPIRES_IN` (default 8h), `JWT_REFRESH_EXPIRES_IN` (default 7d)
- `DATABASE_URL` (PostgreSQL)
- `REDIS_URL` (default `redis://localhost:6379`)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET`
- `ENCRYPTION_KEY`
- `RATE_LIMIT_WINDOW_MS` (default 15min), `RATE_LIMIT_MAX_REQUESTS` (default 100)

**`src/server.js`** loads `.env` via `dotenv.config({ path: path.join(__dirname, '..', '.env') })`.

### Auth Middleware (`src/middleware/auth.js`)

- **`tenantMiddleware`**: Reads `x-tenant-id` header → `req.tenantId`
- **`authenticate`**: Verifies JWT from `Authorization: Bearer <token>` → `req.user = { id, role, tenantId }`
- **`authorize(...roles)`**: Checks `req.user.role` against allowed roles
- **`ROLES`**: `{ ADMIN, RECEPTION, DOCTOR, LAB, PHARMACIST, PATIENT, DISPLAY, CASHIER, OPD_NURSE, SUPER_ADMIN }`

### Employee ID Generation (`auth.routes.js`)

Format: `MBS{ROLE_CODE}{YEAR}{SEQ}`

```javascript
const ROLE_CODE = {
  ADMIN: 'ADM', RECEPTION: 'RECP', DOCTOR: 'DOC', CASHIER: 'CA',
  LAB: 'LAB', PHARMACIST: 'PHA', DISPLAY: 'DISP', NURSE: 'NUR',
  OPD_NURSE: 'NUR', SUPER_ADMIN: 'SUP',
};
```

Sequence is computed by counting existing users with the same prefix for the current year.

### Important Backend Fixes

- **JWT_SECRET loading**: `dotenv.config()` must use explicit path to `.env` (fixed in `918a9b1`)
- **Doctor schedule transaction**: Uses interactive `$transaction(async (tx) => {...})` instead of batch array form (fixed duplicate `deleteMany` + `createMany` issue in Prisma 5.x)
- **Doctor schedule createMany**: Includes `tenantId: doctor.tenantId` (was missing, causing "Invalid invocation" error)
- **Employee ID auto-generation**: Added `generateEmployeeId()` — `employeeId` field made optional in validation; server auto-generates if omitted
- **Overpayment cap**: `POST /bills/:id/payment` validates `amount <= balanceAmount` (400 error if exceeded)

---

## 6. Frontend Architecture

### Tech Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: lucide-react
- **HTTP Client**: axios
- **Notifications**: react-hot-toast
- **Auth**: JWT via cookies (js-cookie)

### Directory Structure

```
hms-frontend/src/
├── app/
│   ├── (print)/                # Print-only layouts (invoice, prescription)
│   ├── appointments/           # Appointment scheduling + walk-in
│   ├── audit/                  # Audit log viewer
│   ├── billing/                # Billing (OPD + Emergency tabs)
│   │   └── new/                # New bill creation form
│   ├── dashboard/              # Admin dashboard
│   ├── doctors/                # Doctor list / detail / new
│   │   ├── [id]/               # Doctor profile + schedule
│   │   └── new/                # Add doctor
│   ├── emergency/              # Emergency (redirects to /billing now)
│   │   ├── [billId]/           # Cashier payment collection
│   │   └── new/                # Redirects to /billing/new
│   ├── inventory/              # Inventory (stub)
│   ├── ipd/                    # IPD (stub — Phase 2)
│   ├── lab/                    # Lab (stub)
│   ├── login/                  # Login page
│   ├── medicines/              # Medicine catalogue
│   ├── notifications/          # Notifications
│   ├── opd/                    # OPD visit management
│   ├── patients/               # Patient CRUD
│   │   ├── [id]/               # Patient detail (visits, emergency history)
│   │   └── new/                # Register patient
│   ├── pharmacy/               # Pharmacy (stub)
│   ├── reports/                # Reports
│   ├── settings/               # Staff management, consumables, chambers, emergency
│   ├── token-board/            # Live token display
│   ├── globals.css             # Tailwind + custom styles
│   ├── layout.tsx              # Root layout with AuthProvider
│   └── page.tsx                # Redirects to /dashboard
├── components/
│   ├── CheckInModal.tsx        # Patient check-in modal
│   └── layout/
│       ├── AppLayout.tsx       # Auth guard + sidebar layout
│       ├── CheckInModal.tsx    # (duplicate — must be merged per H6)
│       └── Sidebar.tsx         # Navigation sidebar
├── lib/
│   ├── api.ts                  # Axios instance + API methods
│   └── auth-context.tsx        # Auth context provider
```

### Root Layout (`layout.tsx`)

- Wraps all pages with `AuthProvider`
- Includes `Toaster` from react-hot-toast
- Google Fonts: Outfit (display), DM Sans (body)

### Auth Context (`auth-context.tsx`)

**State**: `user`, `isLoading`
**Methods**: `login()`, `logout()`, `clearMustChangePassword()`
**Helpers**: `isAdmin`, `isDoctor`, `isReception`, `isLab`, `isPharmacist`, `isDisplay`, `isCashier`
**`getRoleHomePage(role)`**: Returns the home page for each role:
- ADMIN → `/dashboard`
- RECEPTION → `/appointments`
- DOCTOR → `/opd`
- LAB → `/lab`
- PHARMACIST → `/pharmacy`
- CASHIER → `/billing`
- DISPLAY → `/token-board`
- Others → `/dashboard`

**On mount**: Checks `hms_token` cookie → calls `authApi.me()` → sets user or removes cookie on failure.

### Route Permissions (`AppLayout.tsx`)

```javascript
const ROUTE_PERMISSIONS = {
  '/dashboard':    ['ADMIN', 'RECEPTION', 'DOCTOR'],
  '/patients':     ['ADMIN', 'RECEPTION', 'DOCTOR', 'CASHIER'],
  '/appointments': ['ADMIN', 'RECEPTION', 'DOCTOR'],
  '/opd':          ['ADMIN', 'RECEPTION', 'DOCTOR'],
  '/billing':      ['ADMIN', 'RECEPTION', 'CASHIER'],
  '/doctors':      ['ADMIN'],
  '/lab':          ['ADMIN', 'LAB'],
  '/pharmacy':     ['ADMIN', 'PHARMACIST'],
  '/inventory':    ['ADMIN', 'PHARMACIST'],
  '/ipd':          ['ADMIN', 'RECEPTION'],
  '/emergency':    ['ADMIN', 'RECEPTION', 'CASHIER'],
  '/medicines':    ['ADMIN', 'RECEPTION'],
  '/reports':      ['ADMIN'],
  '/audit':        ['ADMIN'],
  '/settings':     ['ADMIN'],
  '/token-board':  ['DISPLAY'],
}
```

Uses `startsWith` matching so sub-routes like `/patients/123` are also protected.

### API Client (`api.ts`)

- Axios instance with `baseURL` from `NEXT_PUBLIC_API_URL` (falls back to production URL)
- 15-second timeout
- Request interceptor: attaches `hms_token` cookie as `Authorization` header
- Response interceptor: on 401, clears cookies and redirects to `/login`
- Named exports: `authApi`, `doctorApi`, `patientApi`, `appointmentApi`, `billingApi`, `emergencyApi`, `medicinesApi`, `labApi`, `opdApi`, `pharmacyApi`, `inventoryApi`, `reportsApi`, `notificationApi`, `settingsApi`, `consumableApi`

---

## 7. Roles & Permissions

### Role Definitions

| Role | Description | Frontend Home | Key Routes |
|---|---|---|---|
| `SUPER_ADMIN` | System-wide admin | /dashboard | Everything |
| `ADMIN` | Hospital admin | /dashboard | Everything |
| `DOCTOR` | Practicing doctor | /opd | OPD, Appointments, Patients |
| `RECEPTION` | Front desk | /appointments | Appointments, Billing, Patients |
| `CASHIER` | Payment collection | /billing | Billing only |
| `LAB` | Lab technician | /lab | Lab (stub) |
| `PHARMACIST` | Pharmacy | /pharmacy | Pharmacy, Inventory |
| `DISPLAY` | Token board TV | /token-board | Token board only |
| `OPD_NURSE` | OPD nurse | (not set) | (not fully implemented) |
| `PATIENT` | Patient self-service | /dashboard | (not implemented) |

### CASHIER Role Details

- **Home page**: `/billing` (Emergency tab by default)
- **Sidebar**: Only "Billing" and "Patients" visible
- **Route permissions**: `/billing`, `/patients`, `/emergency` (for bill detail only)
- **NOT allowed**: `/doctors`, `/medicines`, `/appointments`, `/opd`, `/settings`, etc.
- **Workflow**: Can create/collect payments on emergency bills, view patient profiles

---

## 8. Business Workflows

### 8.1 OPD Workflow

```
Patient arrives
    → RECEPTION registers patient (if new, creates Patient record + UHID)
    → RECEPTION books appointment (scheduled/walk-in)
    → RECEPTION checks patient in → token assigned + appears on DoctorQueue
    → DOCTOR views queue → starts consultation
        → Records vitals, symptoms, diagnosis, prescriptions
        → Uploads prescription image
        → Marks visit complete
    → BILLING generates OPD bill
    → CASHIER collects payment
```

### 8.2 Emergency Workflow (Phase 1)

```
Patient arrives in Emergency
    → RECEPTION finds/registers patient
    → RECEPTION creates bill with billType = EMERGENCY
    → Selects doctor from dropdown → consultation fee auto-fills as first item
    → Optionally checks "Admission Recommended"
    → Confirmation modal: "Further modification needs admin approval"
    → Bill created in PENDING status (unconfirmed)
    → CASHIER sees bill on Emergency tab (30s auto-poll)
    → CASHIER opens bill detail (/emergency/[billId])
    → CASHIER collects payment (partial or full, cannot exceed balance)
    → If more items needed after confirmation:
        → CASHIER adds items (creates modification request)
        → ADMIN approves/rejects via API
        → CASHIER collects additional payment
```

### 8.3 Bill Modification Workflow

```
CASHIER adds new item to confirmed bill
    → BillModificationRequest created (status: PENDING)
    → ADMIN must approve or reject via PATCH endpoint
    → On APPROVE: item added to bill, totals recalculated
    → On REJECT: modification cancelled
```

Note: There is currently NO notification system. Admin must manually check for pending requests.

### 8.4 IPD Workflow (Phase 2 — Planned)

```
Doctor recommends admission
    → RECEPTION creates IPD admission
    → Assigns ward/bed
    → Nurse records vitals, nursing notes
    → Doctor visits, updates diagnosis, treatment plan
    → Bill accumulates (daily charges + procedures + medicines)
    → CASHIER collects advance/periodic payments
    → Doctor initiates discharge
    → Final bill settled → patient discharged
```

### 8.5 Appointment Flow

```
RECEPTION books appointment (scheduled or walk-in)
    → Selects date + doctor + time slot
    → Token number assigned automatically
    → Patient arrives → RECEPTION checks in
    → Patient appears on DoctorQueue + Token Board
    → RECEPTION starts doctor session → first checked-in patient advances
    → DOCTOR completes consultation → visit recorded
    → Queue advances to next patient
```

---

## 9. Emergency Module (Phase 1)

### Status: ✅ COMPLETED (joti branch)

### Database Changes

- `BillType` enum: Added `EMERGENCY`
- `ItemType` enum: Added `CONSULTATION`, `MEDICINE`, `CONSUMABLE`, `PROCEDURE`, `OTHER`
- `Doctor` model: Added `emergencyConsultationFee` (Decimal, optional)
- `Bill` model: Added `admissionRecommended` (Boolean), `confirmedAt` (DateTime?), `confirmedBy` (String?)
- `BillItem` model: Added `itemType` (ItemType), `isModified` (Boolean)
- `BillModificationRequest` model: New — tracks item modification requests with approval flow

### Backend Endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/emergency/bills/pending` | RECEPTION, CASHIER | List pending (unconfirmed) emergency bills |
| GET | `/emergency/bills/today` | RECEPTION, CASHIER | List today's confirmed emergency bills |
| GET | `/emergency/bills/:id` | RECEPTION, CASHIER, ADMIN | Single bill detail with items |
| POST | `/emergency/bills` | RECEPTION, CASHIER | Create emergency bill draft |
| POST | `/emergency/bills/:id/confirm` | RECEPTION, CASHIER | Confirm bill (lock items) |
| POST | `/emergency/bills/:id/payment` | CASHIER | Collect payment (capped at balanceAmount) |
| POST | `/emergency/bills/:id/items` | CASHIER | Add item to confirmed bill (creates modification request) |
| POST | `/emergency/bills/:id/modify-request` | CASHIER | Request item modification |
| PATCH | `/emergency/bills/:id/modify-request/:reqId` | ADMIN | Approve/reject modification request |

### Billing Routes Changes

- `POST /bills`: Added `billType` support (`OPD`/`EMERGENCY`), `admissionRecommended` field
- `GET /bills/:id`: Added billType filtering
- `POST /bills/:id/payment`: Added overpayment validation

### Doctor Routes Changes

- `POST /doctors`: Added `emergencyConsultationFee`
- `PATCH /doctors/:id`: Added `emergencyConsultationFee`
- `POST /doctors/:id/schedules`: Fixed — uses interactive transaction, includes `tenantId`

### Medicines Routes (New)

- `GET /medicines` — List all (with optional search)
- `GET /medicines/:id` — Single item detail
- `POST /medicines` — Create (with `tenantId`)
- `PATCH /medicines/:id` — Update
- `DELETE /medicines/:id` — Soft delete (deactivate)
- `PATCH /medicines/:id/toggle-status` — Activate/deactivate

### Frontend Pages

- `/billing` — Tabbed view: OPD / Emergency / IPD (Soon). Emergency tab shows pending + today bills with 30s auto-poll. CASHIER lands here by default.
- `/billing/new` — Bill creation with EMERGENCY type selector, doctor dropdown with consultation fee auto-fill, admission recommended checkbox, confirmation modal.
- `/emergency` — Redirects to `/billing`
- `/emergency/new` — Redirects to `/billing/new`
- `/emergency/[billId]` — Cashier payment collection view
- `/medicines` — Medicine catalogue CRUD
- `/settings` — Emergency tab + CASHIER role creation
- `/patients/[id]` — Emergency tab showing emergency bill history

### Frontend Key UI Behaviors

- **Emergency Bill Creation**: When bill type = EMERGENCY:
  - Shows "Admission Recommended" checkbox
  - Shows doctor dropdown (hidden for OPD)
  - Selecting a doctor auto-fills a consultation fee item with `emergencyConsultationFee`
  - On submit: confirmation modal warns "Further modification needs admin approval"
- **Emergency Tab** (Cashier View):
  - "Pending" list: unconfirmed bills awaiting cashier action
  - "Today" list: all of today's emergency bills
  - 30-second auto-polling
  - Stats card: total pending, total today, total collected today
- **Payment Collection**: Amount cannot exceed `balanceAmount` — API returns 400 if exceeded

---

## 10. IPD Module (Phase 2 — Planned)

### Status: ⏳ NOT STARTED — depends on Emergency completion

### Database Models to Add
- WardType, Bed, NurseDepartment, NurseDutyAssignment
- IPDAdmission, IPDBillItem, IPDPayment, IPDWardChange
- VitalRecord, NurseNote
- Bill model needs `ipdAdmissionId` FK

### Backend Endpoints (13 planned)
- `POST /ipd/admissions` — Create IPD admission
- `GET /ipd/admissions` — List active admissions
- `GET /ipd/admissions/:id` — Full admission detail
- `PATCH /ipd/admissions/:id` — Update admission / initiate discharge
- `POST /ipd/admissions/:id/discharge` — Complete discharge
- `POST /ipd/admissions/:id/ward-change` — Change ward/bed
- `POST /ipd/admissions/:id/bill-items` — Add item to ongoing bill
- `POST /ipd/admissions/:id/payments` — Record payment
- `POST /ipd/admissions/:id/vitals` — Record vitals
- `POST /ipd/admissions/:id/notes` — Add nursing note
- `GET /ipd/beds` — Bed availability grid
- `POST /ipd/duty-assignments` — Assign nurse to department
- `GET /ipd/duty-assignments` — List duty assignments

### Frontend Pages (7 planned)
- `/ipd` — Main page with active admissions
- `/ipd/new` — New admission form
- `/ipd/[admissionId]` — Admission detail (Bill, Vitals, Notes, Ward History, Payments tabs)
- `/ipd/beds` — Bed management grid
- `/nurse` — Nurse dashboard
- `/nurse-superintendent` — Nurse Superintendent dashboard
- `/settings/ipd-config` — IPD configuration

---

## 11. Employee ID Generation

### Format

```
MBS{ROLE_CODE}{YEAR}{SEQ}
```

### Examples
- `MBSADM2026001` — Admin 2026
- `MBSDOC2026001` — Doctor 2026
- `MBSRECP2026001` — Reception 2026
- `MBSCA2026001` — Cashier 2026

**Older format** (pre-existing users): `ADMIN-001`, `RECP-001`, `DOC-001`, `DISP-001`

### Generation Logic (`auth.routes.js`)

```javascript
async function generateEmployeeId(tenantId, role) {
  const year = new Date().getFullYear();
  const prefix = ROLE_CODE[role] || 'XXX';
  const maxSeq = await prisma.user.findFirst({
    where: { tenantId, employeeId: { startsWith: `MBS${prefix}${year}` } },
    orderBy: { employeeId: 'desc' },
    select: { employeeId: true },
  });
  const nextSeq = maxSeq ? parseInt(maxSeq.employeeId.slice(-4), 10) + 1 : 1;
  return `MBS${prefix}${year}${String(nextSeq).padStart(4, '0')}`;
}
```

### When `employeeId` Is Auto-Generated

- `/auth/register` — If `employeeId` is omitted from request body, it's auto-generated
- Doctors created via `/doctors/new` frontend page send to `/auth/register` without `employeeId`
- Staff created via Settings → Staff modal → no `employeeId` field — auto-generated

---

## 12. Known Credentials

### Local Development

| Employee ID | Name | Password | Role |
|---|---|---|---|
| ADMIN-001 | Hospital Administrator | Admin@123! | ADMIN |
| MBSDOC2026001 | Test Doctor Auto | (set on first login) | DOCTOR |

### Production (from seed)

| Employee ID | Role | Name |
|---|---|---|
| ADMIN-001 | ADMIN | Hospital Administrator |
| RECP-001 to RECP-004 | RECEPTION | Staff 1–4 |
| DOC-001 to DOC-011 | DOCTOR | Various doctors |
| DISP-001 to DISP-005 | DISPLAY | TV/display users |

All production passwords follow the hospital's secure password policy. Contact admin for current passwords.

---

## 13. Project Backlog

### Phase 0 — Multi-Tenant Architecture ✅ Complete
- [x] Tenant model + middleware + scoped queries
- [x] employeeId login + composite unique keys
- [x] New roles: CASHIER, OPD_NURSE, SUPER_ADMIN
- [x] Deployed to production

### Phase 1 — Emergency Module ✅ Complete (joti)
- [x] DB schema: BillModificationRequest, enums, new fields
- [x] Backend: 9 emergency endpoints, billing & doctor changes, medicines CRUD
- [x] Frontend: Billing page with tabs, Emergency bill creation, Cashier payment view
- [x] CASHIER role with route guards (billing/patients only)
- [x] Employee ID auto-generation
- [x] Doctor schedule fix (tenantId + transaction)
- [x] Staff list shows employeeId in settings

**Pending fixes:**
- [ ] Notification system for modification requests (deferred to Phase 2)
- [ ] modify-request can be called on unconfirmed bills (low priority)
- [ ] Merge duplicate CheckInModal components (code review item H6)

### Phase 2 — IPD Module (Next)
See [Section 10](#10-ipd-module-phase-2--planned) for full scope.

### Phase 3 — Docker & Deployment
- [ ] Backend Dockerfile
- [ ] Frontend Dockerfile
- [ ] docker-compose.yml
- [ ] GitHub Actions CI/CD

### Phase 4 — Code Quality & Safety
- [ ] C1: Create `.env.example` + startup config validation
- [ ] C2/C3: Validate ENCRYPTION_KEY and JWT_SECRET at startup
- [ ] C4: Set up test framework (Jest + Supertest)
- [ ] C5: Fix ID generator race conditions (use DB sequences)
- [ ] H1: Refactor modules to service/controller pattern
- [ ] H2: Migrate backend to TypeScript (incremental)
- [ ] H4: JWT revocation + limit DISPLAY token lifetime
- [ ] Various code review items (see `backlog.md`)

---

## 14. Appendix: All Backend API Endpoints

### Auth (`/api/v1/auth`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/login` | Public | Login with employeeId + password |
| POST | `/register` | ADMIN | Create staff/doctor account |
| POST | `/force-change-password` | Authenticated | First-login password change |
| POST | `/change-password` | Authenticated | Regular password change |
| POST | `/logout` | Authenticated | Logout (audit trail) |
| GET | `/me` | Authenticated | Current user profile |
| GET | `/users` | ADMIN | List all staff |
| PATCH | `/users/:id` | ADMIN | Edit staff details |
| PATCH | `/users/:id/toggle-active` | ADMIN | Activate/deactivate staff |
| POST | `/admin/reset-password` | ADMIN | Reset user password |

### Doctor (`/api/v1/doctors`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/` | ADMIN | Create doctor |
| GET | `/` | ALL | List doctors |
| GET | `/:id` | ALL | Doctor detail with schedules |
| PATCH | `/:id` | ADMIN/DOCTOR | Update doctor profile |
| PATCH | `/:id/toggle-status` | ADMIN | Activate/deactivate |
| POST | `/:id/schedules` | ADMIN | Set weekly schedule |
| GET | `/:id/available-slots` | ALL | Get available slots for a date |
| GET | `/:id/patients` | DOCTOR | List doctor's patients |

### Patient (`/api/v1/patients`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/` | RECEPTION, ADMIN | Register patient |
| GET | `/` | ALL | List/search patients |
| GET | `/my-patients` | DOCTOR | List doctor's patients |
| GET | `/:id` | ALL | Patient detail |
| PATCH | `/:id` | RECEPTION, ADMIN | Update patient |

### Appointment (`/api/v1/appointments`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/` | ALL | List appointments (filtered by date/doctor/status) |
| POST | `/` | RECEPTION | Book appointment |
| POST | `/walk-in` | RECEPTION | Book walk-in |
| PATCH | `/:id/check-in` | RECEPTION | Check in patient |
| PATCH | `/:id/skip` | RECEPTION | Skip token |
| PATCH | `/:id/cancel` | RECEPTION | Cancel appointment |
| POST | `/doctor/start-session` | RECEPTION | Start doctor session |
| POST | `/doctor/end-session` | RECEPTION | End doctor session (auto no-shows remaining) |

### Billing (`/api/v1/billing`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/bills` | RECEPTION, CASHIER | Create bill (OPD/EMERGENCY) |
| GET | `/bills/:id` | RECEPTION, CASHIER, ADMIN | Bill detail |
| GET | `/patient/:patientId` | RECEPTION, CASHIER | Patient's bills |
| POST | `/bills/:id/payment` | CASHIER | Collect payment |
| GET | `/summary` | ADMIN, RECEPTION | Billing summary |

### Emergency (`/api/v1/emergency`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/bills` | RECEPTION, CASHIER | Create emergency bill draft |
| POST | `/bills/:id/confirm` | RECEPTION, CASHIER | Confirm bill |
| POST | `/bills/:id/payment` | CASHIER | Collect payment (capped) |
| POST | `/bills/:id/items` | CASHIER | Add item (creates modification request) |
| POST | `/bills/:id/modify-request` | CASHIER | Request modification |
| PATCH | `/bills/:id/modify-request/:reqId` | ADMIN | Approve/reject |
| GET | `/bills/:id` | RECEPTION, CASHIER, ADMIN | Bill detail |
| GET | `/bills/pending` | RECEPTION, CASHIER | Pending emergency bills |
| GET | `/bills/today` | RECEPTION, CASHIER | Today's emergency bills |

### Medicines (`/api/v1/medicines`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/` | ADMIN, RECEPTION | List/search medicines |
| GET | `/:id` | ADMIN, RECEPTION | Single medicine |
| POST | `/` | ADMIN | Create medicine |
| PATCH | `/:id` | ADMIN | Update medicine |
| DELETE | `/:id` | ADMIN | Soft delete |
| PATCH | `/:id/toggle-status` | ADMIN | Activate/deactivate |

### OPD (`/api/v1/opd`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/visits` | DOCTOR | Today's visits |
| POST | `/visits` | DOCTOR | Create visit |
| GET | `/visits/:id` | DOCTOR | Visit detail |
| PATCH | `/visits/:id` | DOCTOR | Update visit |
| POST | `/visits/:id/prescription` | DOCTOR | Add prescription |
| GET | `/queue/:doctorId` | RECEPTION, DOCTOR | Doctor's queue |

### OPD Chambers (`/api/v1/opd-chambers`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/` | ADMIN, RECEPTION | List chambers |
| POST | `/` | ADMIN | Create chamber |
| PATCH | `/:id` | ADMIN | Update chamber |
| DELETE | `/:id` | ADMIN | Delete chamber |
| POST | `/start-session` | RECEPTION, ADMIN | Start doctor session |
| POST | `/end-session` | RECEPTION, ADMIN | End doctor session |
| POST | `/assign` | ADMIN | Assign doctor to chamber |

### Reports (`/api/v1/reports`)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/summary` | ADMIN | Dashboard summary |
| GET | `/patient/:patientId/summary` | ADMIN, DOCTOR | Patient visit summary |

### Lab (`/api/v1/lab`) — **STUB**
| GET | `/tests` | — | Placeholder |

### Pharmacy (`/api/v1/pharmacy`) — **STUB**
| GET | `/` | — | Placeholder |

### Inventory (`/api/v1/inventory`) — **STUB**
| GET | `/` | — | Placeholder |

---

## 15. Appendix: All Frontend Pages

| Route | File | Layout | Purpose |
|---|---|---|---|
| `/` | `page.tsx` | None | Redirects to `/dashboard` |
| `/login` | `login/page.tsx` | None | Login form + force password change |
| `/dashboard` | `dashboard/page.tsx` | AppLayout | Admin dashboard with summary |
| `/appointments` | `appointments/page.tsx` | AppLayout | Appointment list + actions |
| `/appointments/new` | `appointments/new/page.tsx` | AppLayout | Book appointment |
| `/appointments/walk-in` | `appointments/walk-in/page.tsx` | AppLayout | Walk-in booking |
| `/patients` | `patients/page.tsx` | AppLayout | Patient list + search |
| `/patients/new` | `patients/new/page.tsx` | AppLayout | Register patient |
| `/patients/[id]` | `patients/[id]/page.tsx` | AppLayout | Patient detail (visits, emergency history) |
| `/doctors` | `doctors/page.tsx` | AppLayout | Doctor list |
| `/doctors/new` | `doctors/new/page.tsx` | AppLayout | Add doctor (redirects to `/auth/register`) |
| `/doctors/[id]` | `doctors/[id]/page.tsx` | AppLayout | Doctor profile + schedule management |
| `/opd` | `opd/page.tsx` | AppLayout | OPD visit management |
| `/opd/[visitId]` | `opd/[visitId]/page.tsx` | AppLayout | Visit detail + prescription |
| `/billing` | `billing/page.tsx` | AppLayout | OPD/Emergency/IPD tabs |
| `/billing/new` | `billing/new/page.tsx` | AppLayout | New bill creation |
| `/emergency` | `emergency/page.tsx` | AppLayout | Redirects to `/billing` |
| `/emergency/new` | `emergency/new/page.tsx` | AppLayout | Redirects to `/billing/new` |
| `/emergency/[billId]` | `emergency/[billId]/page.tsx` | AppLayout | Cashier payment collection |
| `/medicines` | `medicines/page.tsx` | AppLayout | Medicine catalogue CRUD |
| `/lab` | `lab/page.tsx` | AppLayout | Lab (stub) |
| `/pharmacy` | `pharmacy/page.tsx` | AppLayout | Pharmacy (stub) |
| `/inventory` | `inventory/page.tsx` | AppLayout | Inventory (stub) |
| `/ipd` | `ipd/page.tsx` | AppLayout | IPD (stub) |
| `/settings` | `settings/page.tsx` | AppLayout | Staff, consumables, chambers, emergency config |
| `/reports` | `reports/page.tsx` | AppLayout | Reports |
| `/audit` | `audit/page.tsx` | AppLayout | Audit log |
| `/notifications` | `notifications/page.tsx` | AppLayout | Notifications |
| `/token-board` | `token-board/page.tsx` | None | Live queue display (fullscreen) |
| `/billing/invoice/[billId]` | `(print)/billing/invoice/[billId]/page.tsx` | Print | Invoice print layout |
| `/opd/prescription/[visitId]` | `(print)/opd/prescription/[visitId]/page.tsx` | Print | Prescription print layout |

---

## 16. Recent Changes (joti branch)

### Backend Commits

| Hash | Date | Message |
|---|---|---|
| `918a9b1` | 2026-05-11 | fix: add employeeId to staff list, fix doctor schedule transaction, fix dotenv path for JWT_SECRET |
| `4b5621a` | 2026-05-11 | fix: cap overpayment, add GET /emergency/bills/:id, add medicines routes with tenantId |
| `db6f308` | 2026-05-10 | fix: remove trailing characters from emergency migration SQL |
| `f2397b2` | 2026-05-10 | feat: Emergency module backend - routes, billing types, doctor fee |
| `45a49dd` | 2026-05-10 | feat: add Emergency module database schema |

### Frontend Commits

| Hash | Date | Message |
|---|---|---|
| `2667050` | 2026-05-11 | fix: show employeeId in staff table and creation toast |
| `8bf9641` | 2026-05-11 | feat: emergency frontend pages + medicines catalogue + bill detail fixes |
| `5b98ea4` | 2026-05-10 | feat: multi-tenant login with tenant field and x-tenant-id header |
| `95b0021` | 2026-05-10 | fix: add const keyword to handleToggleActive and handleResetPassword |
| `d1e8624` | 2026-05-10 | fix: restore handle prefix on handleToggleActive and handleResetPassword |

### Summary of All Fixed Issues

1. **Doctor schedule update fails** — `deleteMany` + `createMany` inside batch `$transaction` didn't work; fixed by using interactive `$transaction(async (tx) => {...})`. Also added missing `tenantId` field.
2. **JWT_SECRET not loading** — `dotenv.config()` was loading `.env` from CWD (which was `ws/` not `hms-backend/`); fixed by using explicit `path.join(__dirname, '..', '.env')`.
3. **Employee ID not visible** — `/auth/users` GET endpoint didn't return `employeeId` in its select; added it. Frontend staff table and mobile cards now display it. Creation toast now shows the generated ID.
4. **Overpayment possible** — `POST /bills/:id/payment` now validates `amount <= balanceAmount`.
5. **Medicine catalogue GET /:id** — Added single-item endpoint.
6. **Missing tenantId on medicine create** — Added `tenantId` to medicine creation.
7. **Stale frontend instances** — Two Next.js dev servers were conflicting on port 3000 (from different restart attempts).

---

## 17. UAT Summary

**Full document**: `ws/Project Backlogs/emergency-module-uat.md` (334 lines, 108 test cases)

| Section | Tests | Focus |
|---|---|---|
| TC-A | 10 | Authentication & Authorization |
| TC-B | 7 | Billing Page — Emergency Tab |
| TC-C | 6 | Generate Emergency Bill |
| TC-D | 6 | Doctor Selector & Consultation Fee |
| TC-E | 7 | Confirmation Popup & Bill Creation |
| TC-F | 10 | Cashier Payment Collection |
| TC-G | 3 | Real-Time Polling |
| TC-H | 4 | Patient Profile — Emergency Tab |
| TC-I | 13 | Backend API — Emergency Endpoints |
| TC-J | 6 | Medicines Catalogue |
| TC-K | 3 | Doctor Routes |
| TC-L | 9 | Modified Existing Pages |
| TC-M | 12 | End-to-End Workflow |
| TC-N | 12 | Edge Cases & Error Handling |
| **Total** | **108** | |

### Known Issues

1. **Low**: `modify-request` can be called on unconfirmed bills (should only apply after confirmation). No validation for this yet.
2. **Medium (deferred)**: No notification system for modification requests — admin must manually poll/call API to see pending requests.

---

*This document was generated on 2026-05-11 from the `joti` branch of both hms-backend (`918a9b1`) and hms-frontend (`2667050`). Any AI/developer picking up this document should have a complete understanding of the project's architecture, workflows, and current state.*
