# HMS Project — Backlog & Handoff Document

> Last updated: 2026-06-06
> Branch: `Jotirmoy` (all active work here; `master` = last stable deploy)
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
5. The `useAuth()` hook returns `{ isAdmin, isDoctor, isReception, isCashier, isNurse, isNurseSuperintendent, isDutyManager }`.

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
    duty-manager/
      layout.tsx                 ← DashboardLayout wrapper (prevents sidebar disappear)
      page.tsx                   ← Doctor + Nurse duty tabs (ADMIN/DUTY_MANAGER/NURSE_SUP)
    inventory/      page.tsx     ← Medicines Catalogue tab (admin + pharmacist)
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
  components/
    layout/
      AppLayout.tsx   ← route guard + layout wrapper
      Sidebar.tsx     ← nav items with role filtering
    ui/
      MedicineAutocomplete.tsx   ← reusable medicine search with catalogue + "Other" fallback
  lib/
    api.ts          ← ALL api calls (billingApi, ipdApi, patientApi, medicinesApi, etc.)
    auth-context.tsx ← useAuth() hook (includes isDutyManager)
```

---

## Module Status

### ✅ Phase 0 — Multi-Tenant Architecture (deployed to master)
Full tenant isolation on all 38 Prisma models. employeeId login. CASHIER, OPD_NURSE, SUPER_ADMIN roles.

### ✅ Phase 1 — Emergency Module (deployed to joti)
Emergency bill creation, modification workflow, admission-from-emergency. CASHIER role fully built.

### ✅ Phase 2 — IPD Module (Jotirmoy branch, NOT yet in master)
Full IPD module built and UAT tested through 8 rounds. See detailed status below.

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
| /wards | GET | ADMIN, RECEPTION, DOCTOR, NURSE, NURSE_SUP, DUTY_MANAGER (returns activePatientsCount per ward) |
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
| /admissions/:id/payments | GET/POST | CASHIER, ADMIN, RECEPTION |
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

---

### Post-UAT 8 — End-to-End Validation Fixes (2026-05-31)

#### Critical bugs found and fixed

| # | Bug | Fix |
|---|---|---|
| 1 | RECEPTION blocked from collecting payment on Emergency bill detail page | `emergency.routes.js` POST /bills/:id/payment — added `ROLES.RECEPTION` to `authorize()` |
| 2 | Emergency payment only accepted CASH/UPI/CARD/ONLINE; NETBANKING, INSURANCE, TPA rejected by backend | `emergency.routes.js` — updated `body('method').isIn()` to include all 6 methods |
| 3 | Insurance/TPA details entered in Emergency payment UI were silently discarded (backend never stored them) | `emergency.routes.js` — added insurance fields to body validation and `prisma.payment.create()` |
| 4 | Insurance/TPA details entered in IPD Record Payment UI were silently discarded (IPDPayment model missing columns) | `schema.prisma` — added 5 insurance columns to `IPDPayment`; `ipd.routes.js` — added fields to body validation and `iPDPayment.create()` |
| 5 | Receptionist permission gaps: could not collect payment, add charges, confirm discharge, or see billing tabs on IPD admission page | `ipd/[admissionId]/page.tsx` — `canConfirmDischarge`, `canAddCharge`, tab layout, Record Payment button all now include `isReception`; `billing/page.tsx` auto-collect trigger includes `isReception` |
| 6 | Add Charge backend blocked RECEPTION (403 error) | `ipd.routes.js` POST /admissions/:id/charges — added `ROLES.RECEPTION` |
| 7 | "Special Doctor" not visible in Type dropdown of Add Charge modal | `billing/page.tsx`, `patients/[id]/page.tsx`, `ipd/[admissionId]/page.tsx` — added `SPECIAL_DOCTOR` pseudo-type that maps to CONSULTATION + isSpecialDoctor internally |

#### Additional fixes (same session)

| # | Fix | Files |
|---|---|---|
| 8 | Insurance/TPA fields not showing in IPD Partial Payment modal on billing page | `billing/page.tsx` — added insurance state + fields + validation to `IPDPaymentModal` |
| 9 | Payment modals cut off Collect button when Insurance/TPA fields expand the content | `billing/page.tsx`, `ipd/[admissionId]/page.tsx`, `emergency/[billId]/page.tsx` — added `max-h-[90vh] overflow-y-auto` to all payment modal containers |
| 10 | Emergency bill payment at creation time blocked (Collect payment now hidden for Emergency) | `billing/new/page.tsx` — removed `billType !== 'EMERGENCY'` exclusion; added `emergencyApi.recordPayment()` call after bill creation |
| 11 | Emergency bill detail page: "Collect payment" visible without reviewing bill first | `emergency/[billId]/page.tsx` — gated `canCollect` on `bill.confirmedAt`; added "Review & Confirm Bill" button that calls `emergencyApi.confirmBill()` |

#### Known gaps (deferred, not blocking)

| # | Gap | Notes |
|---|---|---|
| A | Non-admin users who submit a Set Price request cannot track its pending status | Toast says "pending approval" but no UI shows request status to non-admins. Admin sees the amber section. |
| B | NURSE role cannot submit IPDModifyRequest for zero-price charges they added | Currently NURSE can add charges but not request price changes. Admin/Cashier/Reception can. |

---

### Post-UAT 8 — Feature additions (2026-05-31)

#### IPD & Receptionist Enhancements

| Feature | Files |
|---|---|
| Multiple special visiting doctors per IPD admission (name, specialization, fee) | `schema.prisma` (IPDSpecialVisit model), `ipd.routes.js` (POST/DELETE special-visits), `ipd/[admissionId]/page.tsx`, `(print)/ipd/discharge-summary/[admissionId]/page.tsx` |
| Special visiting doctors appear in Add Charge CONSULTATION dropdown with fee pre-fill | `ipd/[admissionId]/page.tsx`, `billing/page.tsx`, `patients/[id]/page.tsx` |
| Add Charge from Billing page IPD rows (no need to navigate to admission page) | `billing/page.tsx` — IPDAdmissionRow with Add Charge modal |
| Add Charge from Patient profile IPD tab | `patients/[id]/page.tsx` |
| Special visiting doctor fee shown in Generate Bill IPD doctor section | `billing/new/page.tsx` |
| Nurse duty assignment: edit and delete existing duties | `nurse-superintendent/page.tsx`, `ipd.routes.js` (PATCH/DELETE /duties/:id), `api.ts` |
| Cross-midnight nurse duty shifts (shiftStart/shiftEnd datetime fields) | `schema.prisma`, `ipd.routes.js`, `nurse-superintendent/page.tsx` |
| Insurance/TPA detail fields in IPD Record Payment and Emergency Collect Payment modals | `ipd/[admissionId]/page.tsx`, `emergency/[billId]/page.tsx` |
| Receptionist = Cashier permissions across all billing, IPD, patient pages | Multiple frontend files + backend route auth |

---

### UAT 8 — Issues fixed (2026-05-27)

#### UAT 8 — Add Charge, Doctor Fees, Set Price Approval

| ID | Issue | Fix location |
|---|---|---|
| 8-1 | Add Charge CONSULTATION dropdown didn't show the Admitting/Attending doctor when they're OPD/Emergency-typed (not IPD) | `ipd/[admissionId]/page.tsx` — load all doctors into `allDoctors` state alongside IPD-filtered `ipdDoctors`; prepend Admitting + Attending doctor options at top of dropdown if not already in IPD list |
| 8-2 | Settings page showed all four fee fields regardless of doctor type; wrong fee tagged to wrong type | `settings/page.tsx` — fee fields now conditional: OPD consultation fee + follow-up shown only when `isOPD` checked; Emergency fee only when `isEmergency` checked; IPD fee only when `isIPD` checked; all fields shown if none checked (prevents data loss) |
| 8-3 | Add Charge fee auto-populate resolved to ₹0 for non-IPD doctors (used only `ipdConsultationFee`) | `ipd/[admissionId]/page.tsx` — fee fallback chain: `ipdConsultationFee \|\| consultationFee \|\| 0`; lookup from `allDoctors` not `ipdDoctors` |
| 8-4 | Set Price approval flow broken: no admin UI to approve, admin's own Set Price also stuck at PENDING forever | `ipd/[admissionId]/page.tsx` — admin auto-approves immediately via `resolveChargeModification` after `requestChargeModification`; non-admin path unchanged. Added amber "Pending Price Updates" section in billing tab (admin-only) with Approve/Reject buttons. `ipd.routes.js` — added `modifyRequests` include to bill-summary charges query so pending requests come through in the API response |

---

### UAT 7 — Issues fixed (2026-05-24)

#### UAT 7 Billing Fixes

| ID | Issue | Fix location |
|---|---|---|
| 7-1 | PROCEDURE type in Generate Bill showed a catalogue dropdown ("No procedures found") instead of free text | `billing/new/page.tsx` — removed `proceduresApi` import, `procedures`/`procedureSearch`/`showProcedureDropdown` states, `filteredProcedures`, `addProcedureToItem`, and `proceduresApi.list()` call; removed PROCEDURE from `onFocus` dropdown trigger, ChevronDown button condition, and dropdown JSX; PROCEDURE now behaves as free-text like OTHER/LAB |
| 7-2 | Emergency bill charges double-counted in IPD billing totals | `ipd.routes.js` GET /admissions/:id/bill-summary + `billing.routes.js` GET /billing/ipd — excluded the linked emergency bill from `linkedBillsTotal` (items already copied as IPDCharges at admission); its payments are still counted in `totalPaid`. Also fixed `billing/page.tsx` expanded IPD card: TRANSFERRED bill now shows "To IPD" badge + "Moved to IPD charges" label instead of "Unpaid"/"Due" |

#### UAT 7 — RECEPTION role expansion

| Change | Files |
|---|---|
| RECEPTION can collect payment on OPD/Emergency/IPD bills (was CASHIER+ADMIN only) | `billing.routes.js`: added `ROLES.RECEPTION` to `POST /bills/:id/payment` authorize() + runtime payment guard inside `POST /bills`; `ipd.routes.js`: added `ROLES.RECEPTION` to `POST /admissions/:id/payments`; Frontend: `canCollectPayment` and `canCollect` now include `isReception` in `billing/new/page.tsx`, `billing/page.tsx`, `ipd/[admissionId]/page.tsx`, `emergency/[billId]/page.tsx` |
| RECEPTION can "Set Price" on ₹0 IPD charges added by nurses | `ipd/[admissionId]/page.tsx`: Set Price button gate changed from `(isAdmin \|\| isCashier)` to `(isAdmin \|\| isCashier \|\| isReception)`; backend `POST /admissions/:id/charges/:chargeId/modify-request` already included RECEPTION — no backend change needed |
| TRANSFERRED (emergency→IPD) bills now show Collect button in billing list | `billing/page.tsx`: removed `bill.paymentStatus !== 'TRANSFERRED'` exclusion from Collect button guard; after collection status naturally becomes PAID/PARTIALLY_PAID |
| Double-count regression fix: payment on TRANSFERRED bill changes status to PAID, old code re-included it in totalCharged | `ipd.routes.js` bill-summary + `billing.routes.js` GET /billing/ipd: switched from `paymentStatus === 'TRANSFERRED'` filter to permanent id-based identity using `admission.linkedEmergencyBillId`; emergency bill charges are never double-counted regardless of current payment status |

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

---

### Security & Production Readiness (2026-06-03)

| # | Fix | Files |
|---|---|---|
| S1 | RBAC gaps — missing role checks on several routes | `ipd.routes.js`, `billing.routes.js`, `emergency.routes.js` — audited and tightened `authorize()` calls |
| S2 | JWT cross-tenant vulnerability — token from one tenant was usable on another tenant's endpoints | `middleware/auth.js` — added tenantId claim check against DB on each request |
| S3 | Console.log noise in production — debug logs leaked patient data | Multiple backend route files — removed all `console.log` debug statements |
| S4 | Tenant auto-resolved from environment variable — removed manual login field | `auth.routes.js` + login page — `TENANT_ID` env var used on backend; no longer required in login form |

---

### Duty Management Consolidation (2026-06-04)

Unified the duty management experience into a single `/duty-manager` route accessible to ADMIN, DUTY_MANAGER, and NURSE_SUPERINTENDENT.

#### What changed

| Change | Files |
|---|---|
| Created `duty-manager/layout.tsx` — without this the sidebar disappeared on navigation | `hms-frontend/src/app/duty-manager/layout.tsx` (new) |
| Sidebar: merged two separate nav entries (nurse-superintendent + duty-manager) into one entry at `/duty-manager` | `Sidebar.tsx` — single entry with roles `[NURSE_SUPERINTENDENT, ADMIN, SUPER_ADMIN, DUTY_MANAGER]` |
| Page title: "Nurse Superintendent" → "Duty Management" | `duty-manager/page.tsx` |
| NURSE_SUPERINTENDENT sees only Nurse Duty tab; Doctor Duty tab hidden | `duty-manager/page.tsx` — `canManageDoctorDuty = !isNurseSuperintendent` |
| IPD Doctors tab added (was missing from admin view) | `duty-manager/page.tsx` — Doctor Duty tab shows ward cards with assigned doctors |
| Nurse Duty layout changed from department-grouped table to card grid (matches Doctor Duty style) | `duty-manager/page.tsx` — each department card shows nurse entries with shift badge + time + Edit/× actions + "Assign Nurse" dashed button |
| Pre-selected department when clicking "Assign Nurse" from a card — department locked in modal | `duty-manager/page.tsx` — `preselectedDeptId` state; AssignNurseModal shows read-only display when set |
| Fixed duplicate `GET /wards` routes — first route (line 110) blocked DUTY_MANAGER with 403; second route (line 1668) was never reached | `ipd.routes.js` — merged `activePatientsCount` into first route, added `ROLES.DUTY_MANAGER`, removed duplicate; frontend updated to use `wardRes.data.data` |

#### Access matrix (Duty Management page)

| Role | Doctor Duty tab | Nurse Duty tab |
|---|---|---|
| ADMIN / SUPER_ADMIN | ✅ view + assign + delete | ✅ view + assign + edit + delete |
| DUTY_MANAGER | ✅ view + assign + delete | ✅ view + assign + edit + delete |
| NURSE_SUPERINTENDENT | ❌ hidden | ✅ view + assign + edit + delete |

---

### Inventory — Medicines Catalogue (2026-06-04)

Moved the Medicines Catalogue from Settings → Emergency (admin-only quick-link) into its own tab on the Inventory page, accessible to both ADMIN and PHARMACIST roles.

| Change | Files |
|---|---|
| Inventory page rewritten from "Coming soon" placeholder to a tabbed page | `hms-frontend/src/app/inventory/page.tsx` |
| Medicines Catalogue tab: search, add, edit, toggle active/inactive | `inventory/page.tsx` — full inline management via `medicinesApi` |
| Removed Medicines Catalogue card from Settings → Emergency tab | `hms-frontend/src/app/settings/page.tsx` |

---

### Medicine Autocomplete — All Billing & Charge Pages (2026-06-04)

All pages that accept a MEDICINE item/charge type now use a reusable autocomplete component with catalogue search and "Other" fallback for custom medicines.

#### New component

**`hms-frontend/src/components/ui/MedicineAutocomplete.tsx`**
- Props: `{ value, onChange(name, price|null), placeholder?, disabled?, className? }`
- Three modes:
  - **idle**: search input with debounced API call (280ms), dropdown with results + "Other" always at bottom
  - **catalogue**: locked teal chip showing selected name + × to clear
  - **custom**: free-text input with "Custom" badge + × to return to search
- Closes on outside click; uses `onMouseDown` + `e.preventDefault()` on dropdown items to prevent blur-before-select
- Resets to idle when parent clears `value` (e.g. after form submit)

#### Pages updated

| Page | What changed |
|---|---|
| `ipd/[admissionId]/page.tsx` | MEDICINE charge type replaced with MedicineAutocomplete; price auto-fills from catalogue except for nurse/nurseSuperintendent roles |
| `emergency/[billId]/page.tsx` | MEDICINE item rows conditionally render MedicineAutocomplete; other item types keep plain input |
| `billing/page.tsx` (IPDAdmissionRow) | MEDICINE charge type in quick-add modal uses MedicineAutocomplete |
| `billing/new/page.tsx` | MEDICINE rows use MedicineAutocomplete; CONSUMABLE keeps existing dropdown unchanged |

No backend changes — `GET /medicines?search=` already supported search queries.

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

### ✅ Nurse duty assignment UI (done 2026-06-04)
Nurse Superintendent (and ADMIN / DUTY_MANAGER) now have a full Duty Management page at `/duty-manager` with card-grid layout for both nurse and doctor duty tabs. Backend endpoints (`GET/POST/PATCH/DELETE /ipd/duties`, `/ipd/nurses`, `/ipd/departments`) were already in place.

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
const { isAdmin, isDoctor, isReception, isCashier, isNurse, isNurseSuperintendent, isDutyManager } = useAuth()
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

---

## Production Deployment & Multi-Tenant Go-Live (2026-06-05 → 06-06)

### Infrastructure (AWS EC2 + Vercel)

| Item | Detail |
|---|---|
| Backend | Node/Express on EC2 (`i-03e57b8769126f532`), managed by PM2, at `api.sarvikatech.in` |
| Frontend | Next.js on Vercel, at `mbs.sarvikatech.in` (main hospital), `citycare.sarvikatech.in` (second tenant), `admin.sarvikatech.in` (super admin panel) |
| Database | AWS RDS PostgreSQL at `hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com` |
| Redis | On EC2 localhost:6379, password-protected, used for MFA tokens + login rate limiting |
| DNS | All subdomains are CNAMEs → Vercel edge; verified propagated as of 2026-06-06 |

### Auth / Token Architecture (production)

The backend sets a `hms_token` **httpOnly cookie** on `api.sarvikatech.in`. Because the frontend is on a different domain (`mbs.sarvikatech.in`), the browser cannot read this cookie in JavaScript. Resolution:

- Backend also returns the JWT as a plain `token` field in the login response body
- Frontend stores it in `localStorage` as `_hms_token`
- All API calls read from `localStorage` and attach `Authorization: Bearer <token>`
- `hms_user` (non-httpOnly) and `hms_tenant` cookies are set by the frontend for middleware/session use
- Next.js middleware checks `hms_user` cookie (readable) instead of `hms_token` (httpOnly, unreadable cross-domain)

### Multi-Tenant Subdomain Resolution

**Problem:** `NEXT_PUBLIC_TENANT_ID=mbs` is baked into Vercel at build time, so every login — including from `citycare.sarvikatech.in` — was sending `x-tenant-id: mbs`. Citycare users exist in the `citycare` tenant so auth always failed with "invalid credentials".

**Fix (`src/lib/api.ts`):**
```typescript
export function resolveTenantId(): string {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname
    const sub = host.split('.')[0]
    // Any subdomain of sarvikatech.in (except infrastructure ones) is a tenant — no hardcoded list needed
    if (host.endsWith('.sarvikatech.in') && !['api', 'www'].includes(sub)) return sub
    if ((host === 'localhost' || host === '127.0.0.1') && Cookies.get('hms_tenant')) {
      return Cookies.get('hms_tenant')!
    }
  }
  return Cookies.get('hms_tenant') || process.env.NEXT_PUBLIC_TENANT_ID || 'mbs'
}
```
Subdomain takes priority on `*.sarvikatech.in` — no hardcoded tenant list. Adding a new tenant requires zero frontend code changes.

### Settings Page — Missing `x-tenant-id` Headers (Fixed 2026-06-06)

14 axios calls in `settings/page.tsx` were missing `'x-tenant-id': getTenantId()` in their headers. These used raw `axios` (not the `api.ts` interceptor which adds the header automatically). Affected tabs:

| Tab | Calls fixed |
|---|---|
| Staff & Users | GET users, PATCH user, POST register |
| Consumables | GET consumables |
| OPD Chambers | GET chambers, GET schedule, DELETE chamber, DELETE assignment |
| IPD Config | GET wards, GET departments |
| Procedures | GET, PATCH toggle, PATCH/POST save |

**Rule going forward:** Any page that uses raw `axios` instead of the shared `api` instance from `api.ts` must manually add both `Authorization` and `x-tenant-id` headers. Better: always use `api` from `api.ts` — it handles both via interceptor.

### Super Admin Platform

| Item | Detail |
|---|---|
| Tenant | `svk-platform` (fixed string ID, not UUID) |
| Login | `admin.sarvikatech.in/admin-login` → dark-themed login, hardcodes `x-tenant-id: svk-platform` |
| Panel | `/super-admin` — list tenants, toggle modules, activate/deactivate, add hospital, add admin |
| First user | `SVK-ADMIN` / `SVKAdmin@2026!` (SUPER_ADMIN role, `mustChangePassword: false`) |
| Code | `hms-frontend/src/app/admin-login/page.tsx`, `src/app/super-admin/page.tsx`, `src/lib/api.ts` (`superAdminApi`), `hms-backend/src/modules/super-admin/super-admin.routes.js` |

### Tenants in Production DB

| id | name | subdomain | isActive |
|---|---|---|---|
| `2060cb00-466a-453c-be4b-75ac8343bcdd` | MBS Hospital | mbs | ✅ |
| `citycare` | City Care Hospital | citycare | ✅ |
| `svk-platform` | SVK Digital Innovations | svk-platform | ✅ |

**Note:** MBS tenant has a UUID id (not the string "mbs") — always use the full UUID in any direct DB/Prisma queries targeting MBS users.

### Citycare Admin Credentials

| Field | Value |
|---|---|
| Employee ID | `ADMIN-001` |
| Password | `Citycare@2026!` |
| mustChangePassword | false (reset directly in DB on 2026-06-06) |

Second admin: `MBSADM2026720` — password unknown (was set with old temp password before code was updated). Reset via admin panel if needed.

### Rate Limiter Behaviour

- **Per-user Redis limiter:** Key pattern `login_attempts:{tenantId}:{employeeId}`, max 5 attempts, 15-min block. Stored in Redis. Clear with: `redis-cli -a <password> DEL "login_attempts:citycare:ADMIN-001"`
- **Per-IP Express limiter:** `authLimiter` in `server.js`, uses in-memory store (not Redis). Clears on PM2 restart: `pm2 restart hms-backend`
- **To clear all blocks immediately:** `pm2 restart hms-backend` on EC2 via AWS SSM

### EC2 Access (AWS SSM)

```bash
# Get instance ID
aws ec2 describe-instances --filters "Name=tag:Name,Values=*hms*" --query "Reservations[0].Instances[0].InstanceId"
# Instance: i-03e57b8769126f532

# Run a command
aws ssm send-command \
  --instance-ids "i-03e57b8769126f532" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["your command here"]' \
  --query "Command.CommandId" --output text

# Get result (wait ~6s first)
aws ssm get-command-invocation \
  --command-id "<CMD_ID>" \
  --instance-id "i-03e57b8769126f532" \
  --query "StandardOutputContent" --output text
```

Redis password: `c75e8121b7c06dcf9206fc1d7bbf271b759f259233d48a2b`
DB password: `cb9802095090bce05f5cdb5958d578a1b89e938d14bb97760d71d7ba41aa8fac`
DB host: `hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com`

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
| `hms-frontend/src/lib/auth-context.tsx` | useAuth() hook with all role flags (incl. isDutyManager) |
| `hms-frontend/src/app/duty-manager/layout.tsx` | Layout wrapper that keeps sidebar alive on this route |
| `hms-frontend/src/app/duty-manager/page.tsx` | Doctor + Nurse duty management (tabbed, role-branched) |
| `hms-frontend/src/app/inventory/page.tsx` | Inventory page with Medicines Catalogue tab |
| `hms-frontend/src/components/ui/MedicineAutocomplete.tsx` | Reusable medicine autocomplete with catalogue + "Other" fallback |

---

## New Tenant Onboarding Runbook (2026-06-06)

This runbook documents the exact steps to bring a new hospital tenant live on the platform. It also records every production issue we hit when onboarding Citycare so we never repeat them.

### What is already handled automatically (zero code changes needed)

| Concern | How it's handled |
|---|---|
| Frontend tenant detection | `resolveTenantId()` in `api.ts` uses `host.endsWith('.sarvikatech.in')` — any new subdomain is detected without touching code |
| Backend CORS | Wildcard regex `/^https:\/\/[a-z0-9-]+\.sarvikatech\.in$/` — new subdomains are allowed automatically |
| Helmet CSP | `connectSrc: ["'self'", "https://*.sarvikatech.in"]` — wildcard covers all subdomains |
| Auth token routing | `x-tenant-id` header resolved from subdomain at request time, not build time |
| Vercel deployment | Single build serves all tenants — no per-tenant deploy needed |

### Step-by-step: Adding a new tenant

#### 1. DNS — Add subdomain in your DNS provider

Add a CNAME record:
```
<hospital-code>.sarvikatech.in  →  cname.vercel-dns.com
```
Example: `greenvalley.sarvikatech.in → cname.vercel-dns.com`

#### 2. Vercel — Add the domain to the project

In Vercel dashboard → Project → Settings → Domains → Add `<hospital-code>.sarvikatech.in`.
Vercel will issue a TLS certificate automatically.

#### 3. Database — Create the tenant record

Connect to RDS from EC2 via SSM:

```bash
# Start SSM session
aws ssm send-command \
  --instance-ids "i-03e57b8769126f532" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["export HOME=/home/ubuntu && psql postgresql://hms_user:<DB_PASSWORD>@hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com:5432/hms_db -c \"INSERT INTO \\\"Tenant\\\" (id, name, subdomain, \\\"isActive\\\") VALUES ('<hospital-code>', '<Hospital Full Name>', '<hospital-code>', true);\""]' \
  --query "Command.CommandId" --output text
```

Or use the Super Admin Panel at `admin.sarvikatech.in/admin-login` → "Add Hospital" button (preferred — no SQL needed).

#### 4. Create the first admin user

**Via Super Admin Panel (recommended):**
- Login as `SVK-ADMIN` at `admin.sarvikatech.in`
- Click the new tenant → "Add Admin"
- Note the generated `employeeId` and temporary password shown on screen

**Via DB directly (fallback):**
```bash
# On EC2, generate bcrypt hash first
node -e "require('bcryptjs').hash('TempPass@2026!', 10).then(h => console.log(h))" --prefix /home/ubuntu/hms-backend
```
Then insert user via psql:
```sql
INSERT INTO users ("employeeId", name, role, "tenantId", "passwordHash", "mustChangePassword", "isActive", "mfaEnabled")
VALUES ('ADMIN-001', 'Hospital Admin', 'ADMIN', '<hospital-code>', '<bcrypt-hash>', true, true, false);
```

#### 5. Verify login

1. Go to `<hospital-code>.sarvikatech.in`
2. Login with `ADMIN-001` / `TempPass@2026!`
3. Since `mustChangePassword=true` you will be prompted to set a new password
4. Since `mfaEnabled=false` and role is ADMIN, you will be shown the MFA setup QR screen — scan with Google Authenticator or similar
5. After MFA setup, you land on the dashboard

#### 6. Verify tenant isolation

- Login as MBS admin on `mbs.sarvikatech.in` first (sets `hms_tenant=mbs` cookie)
- Without clearing cookies, open `<hospital-code>.sarvikatech.in` in the **same browser**
- Login should succeed as the new tenant's ADMIN — the stale MBS cookie must NOT override
- This works because `resolveTenantId()` now checks the subdomain BEFORE the cookie on `*.sarvikatech.in`

---

### Issues we hit onboarding Citycare (and how they're now permanently fixed)

#### Issue 1 — Stale `hms_tenant` cookie overriding subdomain detection

**Symptom:** Citycare admin login returned "invalid credentials". Settings page showed "Failed to load staff list".

**Root cause:** `resolveTenantId()` checked the cookie first. If a user had previously visited `mbs.sarvikatech.in`, the `hms_tenant=mbs` cookie (7-day TTL) caused every subsequent request — even from `citycare.sarvikatech.in` — to send `x-tenant-id: mbs`. The backend looked for citycare's ADMIN-001 in the MBS tenant and found no match.

**Fix (permanent):** Subdomain now takes priority on `*.sarvikatech.in`. Cookie is only consulted as a last resort.

**File:** `hms-frontend/src/lib/api.ts` — `resolveTenantId()`

#### Issue 2 — CORS blocking requests from new subdomain

**Symptom:** Browser console showed CORS error on POST `/api/v1/auth/login` from `citycare.sarvikatech.in`.

**Root cause:** Backend used `FRONTEND_URL` env var (a single string `https://mbs.sarvikatech.in`) as the CORS allowed origin.

**Fix (permanent):** Replaced with wildcard regex: `/^https:\/\/[a-z0-9-]+\.sarvikatech\.in$/`. Any new `*.sarvikatech.in` subdomain is automatically allowed — no env var change needed.

**File:** `hms-backend/src/server.js` — `corsOptions`

#### Issue 3 — PM2 crash due to invalid CSP directive

**Symptom:** After updating `FRONTEND_URL` to a comma-separated list in an earlier attempt to fix CORS, PM2 crashed (502 Bad Gateway). Error: "invalid directive value".

**Root cause:** Helmet's `connectSrc` was receiving `"https://mbs.sarvikatech.in, https://citycare.sarvikatech.in"` as a single string instead of an array.

**Fix (permanent):** `connectSrc: ["'self'", "https://*.sarvikatech.in"]` — wildcard, never needs updating.

**File:** `hms-backend/src/server.js` — `helmetOptions.contentSecurityPolicy`

#### Issue 4 — Wrong DB column name (`password` vs `passwordHash`)

**Symptom:** `UPDATE users SET "password"=...` failed silently (column doesn't exist).

**Root cause:** Prisma schema uses `passwordHash` as the column name, not `password`.

**Fix:** Always use `"passwordHash"` in direct SQL. Verify schema with:
```sql
SELECT column_name FROM information_schema.columns WHERE table_name='users' AND table_schema='public';
```

#### Issue 5 — PM2 restart failing via SSM

**Symptom:** `pm2 restart hms-backend` returned "command not found" via SSM.

**Root cause:** SSM runs without a user HOME, so nvm-managed node paths aren't sourced. PM2 binary path varies by nvm version.

**Fix:** Always use `/usr/bin/pm2` (the system-level symlink) and prepend `export HOME=/home/ubuntu &&`:
```bash
export HOME=/home/ubuntu && /usr/bin/pm2 restart hms-backend
```

#### Issue 6 — Vercel does not auto-deploy on push

**Symptom:** Pushed to `main` but `citycare.sarvikatech.in` still served old code.

**Root cause:** Vercel project is connected to the `hms-frontend` submodule repo, but auto-deploy is not triggered by pushes from the parent repo or by submodule updates.

**Fix:** After any frontend code change, manually redeploy:
```powershell
# From Windows terminal (WSL has no Vercel credentials)
echo y | npx vercel redeploy <DEPLOYMENT_URL> --token <VERCEL_TOKEN>
```
Or use Vercel Dashboard → Project → Deployments → "Redeploy".

#### Issue 7 — SSM command quoting failures

**Symptom:** Complex inline shell commands with nested quotes failed to execute correctly via `aws ssm send-command`.

**Fix:** Encode the script as base64 and decode+run on EC2:
```python
# Locally: generate the b64 string
import base64
script = """your multiline python script"""
print(base64.b64encode(script.encode()).decode())
```
```bash
# SSM command
echo '<b64>' | base64 -d | python3
```

---

### Quick reference: credentials and infrastructure

| Item | Value |
|---|---|
| EC2 instance | `i-03e57b8769126f532` (ap-south-1) |
| DB host | `hms-database.cl84c2imuzlr.ap-south-1.rds.amazonaws.com` |
| DB name | `hms_db` |
| DB user | `hms_user` |
| Redis | EC2 localhost:6379 |
| PM2 binary | `/usr/bin/pm2` |
| Backend process name | `hms-backend` |
| Backend code path | `/home/ubuntu/hms-backend` |
| Super admin login | `admin.sarvikatech.in/admin-login` |
| Super admin user | `SVK-ADMIN` |

**Note:** DB password, Redis password, and Vercel token are in `backlog.md` above (search "Redis password"). Do not commit these to git.
