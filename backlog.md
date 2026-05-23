# HMS Project — Backlog & Handoff Document

> Last updated: 2026-05-23
> Branch: `joti` (all active work here; `master` = last stable deploy)
> Stack: Node.js/Express + Next.js 14 App Router + PostgreSQL/Prisma + Docker Compose

---

## Quick-start for AI agents

```
Working dirs:
  Backend:  hms-backend/          (Node/Express/Prisma — all .js)
  Frontend: hms-frontend/src/     (Next.js 14 App Router, TypeScript)
  Schema:   hms-backend/prisma/schema.prisma

Apply schema changes (shadow DB incompatible with Docker):
  docker exec project-hms-backend-1 npx prisma db push --schema /app/prisma/schema.prisma --accept-data-loss

Restart backend after any schema push or route file changes:
  docker restart project-hms-backend-1
```

**Critical conventions — read before touching anything:**
1. Every Prisma query MUST include `tenantId: req.tenantId` — no exceptions.
2. Use `prisma.*.findFirst({ where: { id, tenantId } })` not `findUnique` for tenant-scoped lookups.
3. Never commit or push without explicit user instruction.
4. `api.ts` is the single source of truth for frontend API calls — add all new endpoints there.
5. The `useAuth()` hook returns `{ isAdmin, isDoctor, isReception, isCashier, isNurse, isNurseSuperintendent }`.

---

## Project Architecture

```
Project-hms/                   ← git root (submodule coordinator)
  hms-backend/                 ← git submodule, branch: joti
  hms-frontend/                ← git submodule, branch: joti
  hms-docs/                    ← git submodule, branch: main
  UAT/                         ← UAT .docx documents (tracked in root)
  backlog.md                   ← THIS FILE
```

**Backend structure:**
```
hms-backend/src/
  middleware/auth.js            ← authenticate + authorize(ROLES...) + ROLES constants
  modules/
    auth/         auth.routes.js
    appointment/  appointment.routes.js, checkin.helper.js
    billing/      billing.routes.js
    consumables/  consumables.routes.js
    doctor/       doctor.routes.js
    emergency/    emergency.routes.js
    ipd/          ipd.routes.js          ← largest file, ~1200 lines
    nurse/        nurse.routes.js
    opd/          opd.routes.js
    patient/      patient.routes.js
    reports/      reports.routes.js
    settings/     settings.routes.js
  prisma.js                     ← singleton PrismaClient
  server.js                     ← Express app + route registration
```

**Frontend structure:**
```
hms-frontend/src/
  app/
    billing/        page.tsx, new/page.tsx, invoice/[id]/page.tsx
    dashboard/      page.tsx
    ipd/
      page.tsx                   ← IPD list
      [admissionId]/page.tsx     ← IPD detail (largest page, ~1100 lines)
      beds/page.tsx              ← Bed grid
      new/page.tsx               ← New admission form
      discharge-summary/[id]/    ← Discharge summary print view
    nurse/          page.tsx
    patients/       page.tsx, [id]/page.tsx, new/page.tsx
    settings/       page.tsx
    ...
  components/layout/
    AppLayout.tsx   ← route guard + layout wrapper
    Sidebar.tsx     ← nav items with role filtering
  lib/
    api.ts          ← ALL api calls (billingApi, ipdApi, patientApi, etc.)
    auth-context.tsx ← useAuth() hook
```

---

## Module Status

### ✅ Phase 0 — Multi-Tenant Architecture (deployed to master)
Full tenant isolation on all 38 Prisma models. employeeId login. CASHIER, OPD_NURSE, SUPER_ADMIN roles.

### ✅ Phase 1 — Emergency Module (deployed to joti)
Emergency bill creation, modification workflow, admission-from-emergency. CASHIER role fully built.

### ✅ Phase 2 — IPD Module (joti branch, NOT yet in master)
Full IPD module built and UAT tested through 5 rounds. See detailed status below.

### ⏳ Phase 3 — Docker & CI/CD (not started)
Needs: Dockerfile (backend + frontend), GitHub Actions CI, production deploy scripts.

### ⏳ Phase 4 — Code Quality (not started)
See code review section at the bottom.

---

## IPD Module — Current State (as of 2026-05-22)

### Schema additions (applied via `prisma db push`)
```prisma
// New models
IPDCharge       ipd_charges        — charges during stay (BED_CHARGE/PROCEDURE/MEDICINE/etc.)
IPDPayment      ipd_payments       — CASHIER-only payment collection (ADVANCE/INTERIM/FINAL)
IPDWardChange   ipd_ward_changes   — bed/ward transfer history
VitalRecord     vital_records      — BP, pulse, temperature, SPO2, weight
NurseNote       nurse_notes        — categorized nursing notes
NurseDepartment nurse_departments  — ICU, Gen Ward, NICU, etc.
NurseDutyAssignment nurse_duty_assignments — nurse → dept per shift

// Modified models
Ward              — added dailyRate Decimal?
IPDAdmission      — added lastAccruedDate, dischargeRequestedAt/By, insuranceDetails (JSON),
                     specialDoctorVisit String?
Bill              — renamed admissionId → ipdAdmissionId
```

### Backend API (`/api/v1/ipd`)
All endpoints implemented in `hms-backend/src/modules/ipd/ipd.routes.js`:

| Endpoint | Method | Roles |
|---|---|---|
| /wards | GET | ADMIN, RECEPTION, DOCTOR, NURSE, NURSE_SUP |
| /wards/:id/beds | GET | ADMIN, RECEPTION, DOCTOR, NURSE, NURSE_SUP |
| /beds | POST | ADMIN, SUPER_ADMIN |
| /admissions | POST | ADMIN, RECEPTION, DOCTOR |
| /admissions | GET | ALL (doctors see own, nurses see assigned dept) |
| /admissions/:id | GET | ALL |
| /admissions/:id | PATCH | ADMIN, SUPER_ADMIN, DOCTOR, RECEPTION |
| /admissions/:id/ward-change | POST | ADMIN, RECEPTION |
| /admissions/:id/transfer | POST | ADMIN, RECEPTION |
| /admissions/:id/discharge | PATCH | ADMIN, SUPER_ADMIN, DOCTOR |
| /admissions/:id/discharge/confirm | POST | ADMIN, SUPER_ADMIN, CASHIER |
| /admissions/:id/bill-summary | GET | ALL |
| /admissions/:id/charges | POST | ADMIN, NURSE, NURSE_SUP, CASHIER |
| /admissions/:id/charges/:chargeId | DELETE | ADMIN, DOCTOR, NURSE |
| /admissions/:id/payments | GET/POST | CASHIER, ADMIN |
| /admissions/:id/vitals | GET/POST | DOCTOR, NURSE, NURSE_SUP, ADMIN |
| /admissions/:id/notes | GET/POST | DOCTOR, NURSE, NURSE_SUP, ADMIN |
| /admissions/:id/prescriptions | GET/POST | DOCTOR, ADMIN |
| /departments | GET/POST/PATCH | ADMIN, NURSE_SUP |
| /duty-assignments | GET/POST | ADMIN, NURSE_SUP |

Also `/api/v1/billing/ipd` — active admissions list for billing page.
And `/api/v1/billing/balance` — cumulative outstanding balance (all-time).

### Frontend pages
- `/ipd` — Admission list with status filter + pagination
- `/ipd/new` — New admission form (patient search + bed selection)
- `/ipd/[admissionId]` — Detail page with role-branched tabs (see tab matrix below)
- `/ipd/beds` — Bed availability grid
- `/ipd/discharge-summary/[admissionId]` — Printable discharge summary

### Role-based tab matrix (IPD admission detail)
| Role | Tabs shown |
|---|---|
| Nurse / Nurse Superintendent / Doctor | Overview, Vitals and Notes |
| Cashier | Overview & Bill, Payments |
| Admin / Reception | Overview & Bill, Vitals, Nurse Notes, Prescriptions, Payments |

### Bed charge accrual logic
- Lazy (no cron) — runs when `GET /admissions/:id/bill-summary` is called
- When status = ADMITTED: auto-posts charges for fully elapsed calendar days; live estimate shown for current partial day
- When doctor initiates discharge: `accrueCurrentBedCharge(admission, now)` is called BEFORE setting status to DISCHARGE_PENDING — this freezes the bed charges
- When status = DISCHARGE_PENDING or DISCHARGED: no further accrual or live estimate
- Function: `accrueCurrentBedCharge(admission, until)` in `ipd.routes.js` lines 27–68

### IPD payment → Bill status sync
When `POST /admissions/:id/payments` is called:
1. Creates IPDPayment record
2. Aggregates all IPD payments for this admission
3. Finds the linked non-TRANSFERRED Bill (via `bill.ipdAdmissionId`)
4. Updates Bill.paidAmount, balanceAmount, paymentStatus accordingly

### Patient/doctor routing
- `/my-patients` (DOCTOR) — queries both OPDVisit and IPDAdmission (admitting + attending doctor)
- `/ipd/admissions?patientId=<uuid>` — returns ALL statuses when patientId provided (no active-only filter)

---

## UAT Session History

### UAT 4 — Issues fixed (all done)
| ID | Issue | Fix location |
|---|---|---|
| A1 | Nurse dashboard: remove "Today's Duties" card | `nurse/page.tsx` |
| A2 | Nurse add charge: catalog price auto-resolution | `ipd/[admissionId]/page.tsx` |
| A3 | Doctor simplified view (Overview + Vitals and Notes) | `ipd/[admissionId]/page.tsx` |
| A4 | Nurse simplified view same | `ipd/[admissionId]/page.tsx` |
| B1 | 3-step emergency admission: checkbox→Yes/No→inline form | `billing/new/page.tsx` |
| B2 | Emergency doctor filter: isIPD (not isEmergency) | `billing/new/page.tsx` |
| B3 | Doctor dropdown hidden when admissionRecommended = false | `billing/new/page.tsx` |
| B5 | Reception can assign attending doctor | `ipd.routes.js` PATCH, `ipd/[admissionId]/page.tsx` |
| B6 | Special doctor visit field on admission | Schema: `specialDoctorVisit String?`, frontend edit UI |
| C1-C3 | Role-branched tabs in IPD detail | `ipd/[admissionId]/page.tsx` |
| C4 | Doctor can't see Appointments in sidebar | `Sidebar.tsx` |
| C5 | Doctor "My Patients" page | `patients/page.tsx`, `patient.routes.js` |
| C6 | Doctor-specific dashboard | `dashboard/page.tsx` |
| D1 | TRANSFERRED bill double-counting fix in bill summary | `ipd.routes.js` |
| D2 | "Today's Bills" heading on billing page | `billing/page.tsx` |
| E1 | Consumables multi-tenant bug (missing tenantId) | `consumables.routes.js` |

### UAT 6 — Issues fixed (all done, 2026-05-23)

#### UAT 6 Feature Issues

| ID | Issue | Fix location |
|---|---|---|
| 4a | Emergency doctor auto-populates "Attending doctor" in IPD Admission Details form | `billing/new/page.tsx` — useEffect watches `selectedDoctor` when `billType = 'EMERGENCY'` and writes to `emergencyIpdForm.admittingDoctorId` |
| 2 | MEDICINE item type in bill items now shows medicines catalog dropdown (same as CONSUMABLE) | `billing/new/page.tsx` — extended `onFocus`, ChevronDown trigger, and dropdown render condition to include `itemType === 'MEDICINE'`; `addMedicineToItem` no longer overrides `itemType` so MEDICINE stays MEDICINE |
| 1 | "Register new patient" link when no patients found in billing | `billing/new/page.tsx` — button redirects to `/patients/new?returnTo=/billing/new`; useEffect reads `patientId` query param on return and auto-fetches + auto-selects the newly registered patient; visible to ADMIN and RECEPTION only |
| 4b | Auto-create CONSULTATION IPD charge on admission if doctor has `ipdConsultationFee` set | `ipd.routes.js` — inside the admission creation `$transaction`, after bed allocation, queries doctor with `user` join; if `ipdConsultationFee > 0`, creates an `IPDCharge` of type `CONSULTATION` with `itemName = "Consultation — Dr. <name>"` and sets `notes = 'Initial consultation fee on admission'` |
| 3 | Nurse sees Emergency Visit Details on IPD overview tab | Backend: updated `GET /admissions/:id` include to add `prescriptionUrl` to `linkedEmergencyBill` select. Frontend `ipd/[admissionId]/page.tsx`: amber left-bordered card shows admitting doctor, admission reason, emergency notes, and a "View Prescription" link (visible only if `isEmergencyCase && linkedEmergencyBill` and user is nurse/nurse superintendent) |
| 5 | Nurse Add Charge modal redesign — type-based UI, price visibility rules, ₹0 highlighting, Set Price flow | `ipd/[admissionId]/page.tsx` — see detailed breakdown below |

**Issue 5 detailed breakdown:**

*Charge list UI (charges table):*
- ₹0 charges: amber-tinted row (`bg-amber-50/50`), `"Price pending"` badge, amber price text
- "Set Price" button on ₹0 rows — visible only to ADMIN and CASHIER on active admissions
- "Set Price" opens a modal with `newUnitPrice` + `reason` fields; submits `POST /admissions/:id/modify-requests` with `requestType: 'PRICE_UPDATE'` (IPDModifyRequest flow — requires admin approval to take effect)
- Delete button: unchanged (ADMIN only)

*Add Charge modal — type-specific input logic:*
- `CONSULTATION`: Doctor dropdown (all IPD doctors with fee in label) + special "Special Doctor (visiting/external)" option. Selecting a doctor auto-fills `itemName` and `unitPrice`. Special doctor shows free-text name input. Price field hidden for nurse/nurse superintendent for all types EXCEPT Special Doctor CONSULTATION (where nurse enters name only; price stays hidden)
- `CONSUMABLE`: searchable datalist of consumables catalog
- `MEDICINE`: searchable datalist of medicines catalog
- `PROCEDURE` / `OTHER`: plain free-text description field
- Quantity always shown; price field hidden for nurses on non-special consultation types

*Set Price modal:*
- Component: `showSetPriceModal` + `setPriceCharge` + `setPriceForm` states
- Submits `POST /admissions/:id/modify-requests` → `{ requestType: 'PRICE_UPDATE', chargeId, newUnitPrice, reason }`
- Toast: "Price update request submitted — pending admin approval"

#### Bug fixes (2026-05-23)

| Bug | Root cause | Fix |
|---|---|---|
| "View Prescription" link → 404 at `localhost:3000/uploads/...` | (1) Backend had no static file server for uploads; (2) `prescriptionUrl` stored as `/uploads/prescriptions/...` relative path, used directly as `href` so browser resolved it against frontend origin | (1) `server.js`: added `app.use('/uploads', express.static(path.join(__dirname, '../../uploads')))` pointing inside Docker container; (2) `ipd/[admissionId]/page.tsx`: href now prepends backend base URL derived from `NEXT_PUBLIC_API_URL` by stripping `/api/v1` suffix: `.replace(/\/api\/v1\/?$/, '')` |
| Docker uploads ephemeral — prescription files lost on container restart | No Docker volume for uploads directory | `docker-compose.yml`: added `- ./uploads:/uploads` bind-mount to backend service; files now persist on host at `./uploads/` |
| "Register new patient" inline modal → "Registration failed" toast | Backend returns 403 for RECEPTION role attempting `POST /patients`; also inline modal lacked DPDPA consent checkbox and full validation | Replaced inline modal with redirect flow: button now calls `router.push('/patients/new?returnTo=/billing/new')`; the existing `/patients/new` page already supports `returnTo` and redirects to `${returnTo}?patientId=${id}` on success; billing page useEffect reads `patientId` from URL and auto-selects patient |
| TRANSFERRED emergency bill shows "Paid" badge + "Due: ₹X" simultaneously | When IPD admission is linked to an emergency bill, `ipd.routes.js` correctly sets `paymentStatus = 'TRANSFERRED'`; but billing list had no handler for `TRANSFERRED` — it fell through the `else` branch showing "Paid" text with wrong green styling | `billing/page.tsx`: added `TRANSFERRED: 'bg-blue-100 text-blue-700'` to `STATUS_BADGE`; extracted `statusLabel()` helper that returns `"To IPD"` for TRANSFERRED; hid "Collect" button for TRANSFERRED bills (`bill.paymentStatus !== 'PAID' && bill.paymentStatus !== 'TRANSFERRED'`) |

#### Open item from UAT 6 (not yet fixed)

| ID | Issue | Status |
|---|---|---|
| — | PROCEDURE type in billing/new shows catalogue dropdown even when catalogue is empty — should degrade to free text | Decision pending: option A = always free text for PROCEDURE in billing; option B = hide dropdown trigger when `procedures.length === 0` |

---

### UAT 5 — Issues fixed (all done, committed 2026-05-22)
| ID | Issue | Fix location |
|---|---|---|
| 1 | Doctor My Patients shows 0 | `patient.routes.js` — IPD admissions + tenantId fix |
| 2 | Cashier sees Bed Grid button | `ipd/page.tsx` — hidden for isCashier |
| 3 | Cashier sees Vitals/Nurse Notes tabs | `ipd/[admissionId]/page.tsx` — cashier tab branch |
| 4 | Patient profile IPD tab misses discharged admissions | `ipd.routes.js` patientId param, `patients/[id]/page.tsx` |
| 5 | Balance Due stat date-filtered (should be cumulative) | `billing.routes.js` GET /balance, `billing/page.tsx` |
| 6 | Add Charge: all types used catalog; OTHER/PROCEDURE should be free text | `ipd/[admissionId]/page.tsx` |
| 7 | IPD payment doesn't update Bill.paymentStatus | `ipd.routes.js` POST payments — syncs linked Bill |
| 8 | Bed accrual continues after discharge initiation | `ipd.routes.js` — freeze on PATCH /discharge |

---

## Remaining / Deferred Items

### ✅ B4 — Emergency bill prescription upload (done 2026-05-22)
On the Generate Bill page (`/billing/new`), when bill type = EMERGENCY:
- A dashed file input appears for PDF/JPG/PNG (max 15 MB), visible in the form
- After bill is created, file is uploaded via `POST /billing/bills/:id/prescription-upload`
- File saved to `uploads/prescriptions/bill_rx_<id>_<timestamp>.<ext>`
- `Bill.prescriptionUrl String?` field added to schema and pushed to DB
- Success screen shows: upload in-progress, done tick, retry on error, or optional upload button if none selected during form fill
- Files: `billing.routes.js` (upload endpoint), `billing/new/page.tsx` (UI), `schema.prisma` (field)
- **Pending — S3 migration:** Currently stores to local disk. When AWS creds available, swap multer storage to `multer-s3` targeting `AWS_S3_BUCKET`. Same upgrade needed for OPD upload too.

### A5 — Show prescription medicine names inline (partially done)
**What:** In the IPD overview tab (for nurses and doctors), show prescription medicines as inline badges. This is already partially in the code — prescriptions are fetched on mount and shown in the overview. Verify it's working in UAT.

### Discharge summary print view
**What:** `/ipd/discharge-summary/[admissionId]` page was added in the latest frontend commit. Needs:
- Verify layout is print-friendly (CSS `@media print`)
- Include: patient info, admission dates, attending doctor, diagnosis, discharge notes, discharge condition, charges summary, payments summary
- May need a dedicated backend endpoint or use the existing bill-summary data

### IPD admin configuration
**What:** Settings page needs an "IPD Config" tab for admin to manage:
- Wards (add/edit name, total beds, dailyRate)
- Departments (add/edit for nurse duty assignments)
Currently ward/bed management is only via API (no UI).

### Nurse duty assignment UI
**What:** Nurse Superintendent needs a UI to assign nurses to departments per shift. Backend endpoints exist at `GET/POST /ipd/duty-assignments` and `GET/POST /ipd/departments`. Need a frontend page at `/nurse-superintendent` or inside settings.

### IPD module not yet in master
The IPD module schema was pushed to the production DB (`prisma db push --accept-data-loss`) but the code is on the `joti` branch. When ready to deploy: merge `joti` → `master` and restart Docker containers.

---

## Known Bugs / Edge Cases to Watch

### IPD bill totalAmount vs actual charges
The linked Bill record (created at admission from emergency conversion) has a `totalAmount` set at creation time. As IPD charges accrue, the actual total diverges from `Bill.totalAmount`. The IPD bill summary correctly uses `ipdChargesTotal + linkedBillsTotal` for display, but the `Bill` record's `totalAmount` is stale. This is OK for now but will be confusing at final discharge.

**Future fix:** When cashier confirms discharge, update `Bill.totalAmount` to the final computed total before updating paymentStatus.

### NURSE_SUPERINTENDENT role
The `isNurseSuperintendent` check exists in frontend but the backend `ROLES.NURSE_SUPERINTENDENT` might not be consistently applied across all nurse-related endpoints. Verify during next UAT round.

### Prescriptions tab in simple view
Nurses/doctors use the `vitals_notes` combined tab. Prescriptions are shown inline in the overview for these roles. Doctors can write prescriptions from the overview. No separate "Prescriptions" tab for nurses (by design).

---

## Technical Patterns Reference

### Authentication / Authorization
```javascript
// Backend
router.use(authenticate)  // attaches req.user, req.tenantId
authorize(ROLES.ADMIN, ROLES.RECEPTION)  // 403 if role not in list

// Frontend
const { isAdmin, isDoctor, isReception, isCashier, isNurse, isNurseSuperintendent } = useAuth()
```

### Tenant-scoped Prisma queries (MANDATORY)
```javascript
// Always include tenantId in where clause
const record = await prisma.someModel.findFirst({
  where: { id: req.params.id, tenantId: req.tenantId }
})

// For creates
await prisma.someModel.create({ data: { tenantId: req.tenantId, ...rest } })

// For updates: use findFirst (not findUnique) + tenantId
const existing = await prisma.someModel.findFirst({ where: { id, tenantId: req.tenantId } })
if (!existing) throw new AppError('Not found', 404)
```

### Schema changes
```bash
# Do NOT use prisma migrate dev (shadow DB fails in Docker)
docker exec project-hms-backend-1 npx prisma db push \
  --schema /app/prisma/schema.prisma --accept-data-loss

# Then restart backend
docker restart project-hms-backend-1
```

### Adding a new API endpoint (frontend)
Always add to `hms-frontend/src/lib/api.ts`:
```typescript
export const myApi = {
  list: (params?: { foo?: string }) => api.get('/my-route', { params }),
  get: (id: string) => api.get(`/my-route/${id}`),
  create: (data: any) => api.post('/my-route', data),
  update: (id: string, data: any) => api.patch(`/my-route/${id}`, data),
}
```

### Role-conditional rendering pattern
```typescript
const { isDoctor, isNurse, isNurseSuperintendent, isCashier, isAdmin } = useAuth()
const isSimpleView = isNurse || isNurseSuperintendent || isDoctor
const showBilling = !isNurse && !isNurseSuperintendent && !isDoctor
```

### Error handling (backend)
```javascript
// Use AppError for expected errors
throw new AppError('Descriptive message', 404)

// All route handlers are auto-wrapped — errors propagate to global handler
// Do NOT catch internally unless you need fallback behavior
```

### Audit logging
```javascript
await logAudit({
  userId: req.user.id,
  tenantId: req.tenantId,
  action: 'CREATE' | 'UPDATE' | 'DELETE',
  resource: 'ModelName',
  resourceId: record.id,
  details: { /* any extra context */ },
})
```

---

## Code Review Debt (original items from 2026-05-09 review)

### Critical (unresolved)
- **C1** No `.env.example` — new devs can't configure the app
- **C4** Zero test coverage
- **C5** ID generators have race conditions (UHID, bill numbers)

### High Priority (unresolved)
- **H1** All business logic in route files — no service layer
- **H2** Backend is plain JS (no TypeScript)
- **H3** No Docker Compose — wait, this IS now resolved (Docker Compose exists)
- **H4** DISPLAY role has 365-day JWT with no revocation
- **H6** Two duplicate CheckInModal components

### Medium Priority (unresolved)
- **M2** Settings page is 1393 lines — needs splitting
- **M3** Settings page uses raw axios instead of shared api.ts
- **M7** Token board polls every 3s with no backoff

### Items already resolved
- ✅ **M9** Singleton PrismaClient (now in `src/prisma.js`)
- ✅ **M4** Hardcoded production IP (partially fixed via env vars)
- ✅ **H5** Stub modules — IPD is now implemented; lab/pharmacy still stubs

---

## IPD Module Files Reference

| File | What it does |
|---|---|
| `hms-backend/src/modules/ipd/ipd.routes.js` | All IPD backend routes (~1200 lines) |
| `hms-backend/src/modules/billing/billing.routes.js` | Billing including `/billing/balance` + `/billing/ipd` |
| `hms-backend/src/modules/patient/patient.routes.js` | Patient routes including `/my-patients` (IPD-aware) |
| `hms-backend/src/modules/consumables/consumables.routes.js` | Consumables catalog (multi-tenant fixed) |
| `hms-backend/prisma/schema.prisma` | Full schema including all IPD models |
| `hms-frontend/src/app/ipd/[admissionId]/page.tsx` | IPD detail — all tabs, modals (~1100 lines) |
| `hms-frontend/src/app/ipd/page.tsx` | IPD list page |
| `hms-frontend/src/app/ipd/new/page.tsx` | New admission form |
| `hms-frontend/src/app/billing/page.tsx` | Billing list + IPD billing tab |
| `hms-frontend/src/app/billing/new/page.tsx` | Create bill (including emergency→IPD flow) |
| `hms-frontend/src/app/dashboard/page.tsx` | Doctor dashboard (IPD + OPD stats) |
| `hms-frontend/src/app/patients/[id]/page.tsx` | Patient profile with IPD tab (all admissions) |
| `hms-frontend/src/lib/api.ts` | All frontend API clients |
| `hms-frontend/src/lib/auth-context.tsx` | useAuth() hook with all role flags |
