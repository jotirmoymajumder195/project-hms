# MBS HMS — IPD Module Complete Specification

> **Last updated:** 2026-05-11
> **Current branch:** `joti` (backend `bb37b62`, frontend `2667050`)
> **Schema migration:** `prisma/migrations/20260511_add_ipd_module/migration.sql`
> **State:** Schema designed & applied locally. Backend routes & frontend pending.

---

## Table of Contents

1. [Module Overview](#1-module-overview)
2. [Business Workflow](#2-business-workflow)
3. [Database Schema](#3-database-schema)
4. [Backend API Endpoints](#4-backend-api-endpoints)
5. [Frontend Pages](#5-frontend-pages)
6. [Bed Charge Auto-Accrual](#6-bed-charge-auto-accrual)
7. [Insurance Flow](#7-insurance-flow)
8. [Role-Based Access](#8-role-based-access)
9. [Implementation Order](#9-implementation-order)
10. [Backend Route Implementation Details](#10-backend-route-implementation-details)
11. [Frontend Implementation Details](#11-frontend-implementation-details)
12. [Appendix: Key Files](#12-appendix-key-files)

---

## 1. Module Overview

The IPD (In-Patient Department) module manages the complete lifecycle of a patient admitted to the hospital — from admission through discharge, including ward/bed management, daily charge accrual, ongoing billing with part-settlement, nursing care tracking, and insurance handling.

### Key Design Decisions

- **IPD billing is separate from OPD/Emergency billing:** Uses its own `IPDCharge` and `IPDPayment` models. At discharge, a final `Bill` record is created (`billType=IPD`, linked via `ipdAdmissionId`) for unified financial reporting.
- **Bed charges auto-accrue:** The system lazily-calculates un-accrued days when the bill is viewed or at settlement, using the bed's `dailyCharge` rate. Ward changes mid-stay update the accrual rate.
- **Part-settlement supported:** Patient can pay for accumulated charges at any point during their stay (recorded as `IPDPayment` with `paymentType=INTERIM`).
- **Cashier-only payment collection:** Only CASHIER role can record IPD payments. RECEPTION and DOCTOR can view and add charges but cannot collect.
- **Insurance-ready:** `insuranceDetails` JSON field on `IPDAdmission` stores TPA/policy info. Future: dedicated `InsuranceClaim` model for direct TPA integration.
- **Frontend on Billing tab:** IPD is a third tab on the `/billing` page (next to OPD and Emergency tabs).
- **Accessible on Billing page:** IPD is accessible as a tab on the `/billing` page (like Emergency).

---

## 2. Business Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    IPD FULL WORKFLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. ADMISSION                                                 │
│     ──────────                                                │
│     Doctor recommends admission (from Emergency triage        │
│     or OPD consultation)                                      │
│         ↓                                                     │
│     RECEPTION creates IPDAdmission                            │
│     → Selects Ward + Bed (bed status → OCCUPIED)              │
│     → Records admitting doctor, admission reason, diagnosis   │
│     → Optionally enters insurance details (TPA, policy info)  │
│     → lastAccruedDate set to admissionDate                    │
│                                                              │
│  2. DURING STAY                                               │
│     ────────────                                              │
│     DOCTOR rounds → updates diagnosis, adds charges           │
│     (procedures, medicines → IPDCharge with chargeType)       │
│         ↓                                                     │
│     NURSE records vitals (VitalRecord) + nursing notes        │
│     (NurseNote) at each shift                                 │
│         ↓                                                     │
│     Bed charges auto-accrue (see Section 6)                   │
│         ↓                                                     │
│     Optional: Patient changes ward/bed                        │
│     → RECEPTION records ward change (IPDWardChange)           │
│     → Bed allocation updated, accrual continues at new rate   │
│         ↓                                                     │
│     Optional: Part settlement                                 │
│     → Patient wants to clear dues till date                   │
│     → CASHIER views accumulated charges, collects payment     │
│     → Recorded as IPDPayment (paymentType=INTERIM)            │
│                                                              │
│  3. DISCHARGE                                                 │
│     ──────────                                                │
│     Doctor requests discharge                                 │
│     → dischargeRequestedAt + dischargeRequestedBy set         │
│         ↓                                                     │
│     System catches up bed charges → lastAccruedDate = today   │
│         ↓                                                     │
│     Final bill preview generated:                             │
│       Total IPDCharges - Total IPDPayments = Balance          │
│         ↓                                                     │
│     CASHIER settles final bill:                               │
│       a) Creates final Bill record (billType=IPD)             │
│          with ipdAdmissionId link                             │
│       b) Records final IPDPayment (paymentType=FINAL)         │
│          Split: patient share (CASH/UPI) + insurance share    │
│          (INSURANCE/TPA payment method)                       │
│         ↓                                                     │
│     Doctor completes discharge:                               │
│     → actualDischarge set, bed → AVAILABLE                    │
│     → discharge notes + condition recorded                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema

### 3.1 Modified Models

#### Ward (`wards`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | String (UUID) | — | PK |
| `tenantId` | String | — | FK → Tenant |
| `name` | String | — | Ward name (e.g. "General Ward A") |
| `wardType` | String | `"GENERAL"` | Free text: GENERAL, ICU, PRIVATE, etc. |
| `floor` | String? | — | Floor number/name |
| `totalBeds` | Int | — | Total bed count |
| `dailyRate` | Decimal(10,2) | 0 | Default daily charge for this ward (per-bed overrides via Bed.dailyCharge) |
| `isActive` | Boolean | true | Soft delete |
| `beds` | Bed[] | — | Relation |

#### Bed (`beds`) — unchanged

| Field | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `tenantId` | String | FK → Tenant |
| `wardId` | String | FK → Ward |
| `bedNumber` | String | Bed identifier |
| `bedType` | BedType enum | GENERAL / SEMI_PRIVATE / PRIVATE / ICU / NICU / HDU |
| `dailyCharge` | Decimal(10,2) | Per-bed rate (overrides Ward.dailyRate if non-zero) |
| `status` | BedStatus enum | AVAILABLE / OCCUPIED / UNDER_MAINTENANCE / RESERVED |
| `features` | String? | e.g. "Window side, near nurse station" |
| `isActive` | Boolean | |

#### IPDAdmission (`ipd_admissions`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | String (UUID) | — | PK |
| `tenantId` | String | — | FK → Tenant |
| `admissionNumber` | String | — | Unique per tenant, auto-generated |
| `patientId` | String | — | FK → Patient |
| `admittingDoctorId` | String | — | FK → Doctor |
| `admissionDate` | DateTime | now() | When admitted |
| `expectedDischarge` | DateTime? | — | Estimated discharge date |
| `actualDischarge` | DateTime? | — | Actual discharge datetime |
| `admissionReason` | String | — | Why admitted |
| `diagnosis` | String? | — | Medical diagnosis |
| `status` | IPDStatus | ADMITTED | ADMITTED / DISCHARGED / TRANSFERRED / DECEASED |
| `referredBy` | String? | — | Referring doctor name (free text) |
| **`lastAccruedDate`** | **DateTime?** | — | **Last date bed charges were accrued (for lazy accrual)** |
| **`dischargeRequestedAt`** | **DateTime?** | — | **When discharge was first requested** |
| **`dischargeRequestedBy`** | **String?** | — | **User ID who requested discharge** |
| `dischargeNotes` | String? | — | Notes at time of discharge |
| `dischargeCondition` | String? | — | e.g. "Stable", "Referred to higher center" |
| **`insuranceDetails`** | **Json?** | — | **Insurance info (TPA name, policy, pre-auth ref, amount)** |
| `createdAt` | DateTime | now() | |
| `updatedAt` | DateTime | updatedAt | |

**Relations:** tenant, patient, doctor, bedAllocations, ipdCharges, ipdPayments, wardChanges, vitalRecords, nurseNotes, bills

#### Bill (`bills`) — modified

| Change | Details |
|---|---|
| `admissionId` → **`ipdAdmissionId`** | Renamed, now a proper FK → `IPDAdmission` |
| New relation | `ipdAdmission IPDAdmission? @relation(...)` |

### 3.2 New Models

#### IPDCharge (`ipd_charges`)

Records every individual charge accrued during the IPD stay.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | String (UUID) | — | PK |
| `tenantId` | String | — | FK → Tenant |
| `admissionId` | String | — | FK → IPDAdmission |
| `chargeType` | IPDChargeType | — | BED_CHARGE / PROCEDURE / MEDICINE / CONSUMABLE / CONSULTATION / LAB / OTHER |
| `itemName` | String | — | Description (e.g. "Bed charge Day 3", "IV Antibiotic") |
| `quantity` | Int | 1 | |
| `unitPrice` | Decimal(10,2) | — | Per-unit price |
| `totalPrice` | Decimal(10,2) | — | quantity × unitPrice |
| `addedBy` | String | — | User ID who added this charge |
| `addedAt` | DateTime | now() | When charge was recorded |
| `notes` | String? | — | Optional notes |

#### IPDPayment (`ipd_payments`)

Records all payments collected during the IPD stay.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | String (UUID) | — | PK |
| `tenantId` | String | — | FK → Tenant |
| `admissionId` | String | — | FK → IPDAdmission |
| `amount` | Decimal(10,2) | — | Payment amount |
| `paymentMethod` | PaymentMethod | — | CASH / CARD / UPI / NETBANKING / INSURANCE / TPA |
| `paymentType` | IPDPaymentType | — | ADVANCE / INTERIM / FINAL |
| `transactionRef` | String? | — | UPI ref, cheque no., etc. |
| `receivedBy` | String | — | User ID (must be CASHIER) |
| `notes` | String? | — | Optional |
| `createdAt` | DateTime | now() | |

#### IPDWardChange (`ipd_ward_changes`)

Tracks every ward/bed transfer during the stay.

| Field | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `tenantId` | String | FK → Tenant |
| `admissionId` | String | FK → IPDAdmission |
| `fromWardId` | String? | NULL if initial assignment |
| `fromBedId` | String? | NULL if initial assignment |
| `toWardId` | String | New ward |
| `toBedId` | String | New bed |
| `reason` | String | Why changed (e.g. "Upgraded to Private", "ICU step-down") |
| `changedBy` | String | User ID |
| `changedAt` | DateTime | |

#### VitalRecord (`vital_records`)

Vital signs charting.

| Field | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `tenantId` | String | FK → Tenant |
| `admissionId` | String | FK → IPDAdmission |
| `bpSystolic` | Int? | Systolic BP |
| `bpDiastolic` | Int? | Diastolic BP |
| `pulse` | Int? | Heart rate (bpm) |
| `temperature` | Decimal(4,1)? | Body temperature |
| `spo2` | Int? | Oxygen saturation (%) |
| `respiratoryRate` | Int? | Breaths per minute |
| `weight` | Decimal(5,1)? | Weight (kg) |
| `recordedBy` | String | User ID |
| `recordedAt` | DateTime | |
| `notes` | String? | Free text |

#### NurseNote (`nurse_notes`)

Nursing observations and shift handover notes.

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | String (UUID) | — | PK |
| `tenantId` | String | — | FK → Tenant |
| `admissionId` | String | — | FK → IPDAdmission |
| `note` | String | — | Free text |
| `category` | NurseNoteCategory | GENERAL | GENERAL / MEDICATION / CARE / OBSERVATION / SHIFT_HANDOVER / OTHER |
| `recordedBy` | String | — | User ID |
| `recordedAt` | DateTime | now() | |

#### NurseDepartment (`nurse_departments`)

| Field | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `tenantId` | String | FK → Tenant |
| `name` | String | Unique per tenant (e.g. "ICU", "General Ward", "NICU") |
| `description` | String? | |
| `isActive` | Boolean | |

#### NurseDutyAssignment (`nurse_duty_assignments`)

| Field | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `tenantId` | String | FK → Tenant |
| `nurseId` | String | FK → User (user with role OPD_NURSE or other nurse role) |
| `departmentId` | String | FK → NurseDepartment |
| `dutyDate` | DateTime | Date of duty |
| `shift` | ShiftType | MORNING / EVENING / NIGHT |
| `assignedBy` | String | User ID |
| `createdAt` | DateTime | |

### 3.3 New Enums

| Enum | Values |
|---|---|
| `IPDChargeType` | `BED_CHARGE`, `PROCEDURE`, `MEDICINE`, `CONSUMABLE`, `CONSULTATION`, `LAB`, `OTHER` |
| `IPDPaymentType` | `ADVANCE`, `INTERIM`, `FINAL` |
| `ShiftType` | `MORNING`, `EVENING`, `NIGHT` |
| `NurseNoteCategory` | `GENERAL`, `MEDICATION`, `CARE`, `OBSERVATION`, `SHIFT_HANDOVER`, `OTHER` |

---

## 4. Backend API Endpoints

### Base path: `/api/v1/ipd`

#### Admissions

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/admissions` | RECEPTION, DOCTOR, ADMIN | Create new IPD admission |
| GET | `/admissions` | RECEPTION, DOCTOR, CASHIER, ADMIN | List admissions (filterable by status, date, patient) |
| GET | `/admissions/:id` | RECEPTION, DOCTOR, CASHIER, ADMIN | Full admission detail (charges, payments, vitals, notes) |
| PATCH | `/admissions/:id` | RECEPTION, DOCTOR, ADMIN | Update admission details (diagnosis, expected discharge, etc.) |
| POST | `/admissions/:id/discharge-request` | DOCTOR | Request discharge |
| POST | `/admissions/:id/discharge` | DOCTOR | Complete discharge (finalize) |

#### Ward & Bed Management

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/wards` | RECEPTION, DOCTOR, CASHIER, ADMIN | List wards with bed counts |
| GET | `/beds` | RECEPTION, DOCTOR, CASHIER, ADMIN | Bed availability grid (filterable by ward, status, type) |
| POST | `/admissions/:id/ward-change` | RECEPTION, ADMIN | Transfer patient to another ward/bed |

#### IPD Charges (Billing)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/admissions/:id/charges` | DOCTOR, NURSE, RECEPTION, ADMIN | Add charge (procedure, medicine, consumable, etc.) |
| GET | `/admissions/:id/charges` | DOCTOR, NURSE, CASHIER, RECEPTION, ADMIN | List all charges |
| POST | `/admissions/:id/accrue-bed-charges` | RECEPTION, CASHIER, ADMIN | Manually trigger bed charge accrual catch-up |

#### IPD Payments (Cashier Only)

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/admissions/:id/payments` | **CASHIER**, ADMIN | Record payment (ADVANCE / INTERIM / FINAL) |
| GET | `/admissions/:id/payments` | CASHIER, RECEPTION, ADMIN | List all payments |

#### Settlement & Final Bill

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/admissions/:id/settlement-preview` | CASHIER, ADMIN | Preview final settlement (total charges - payments = balance) |
| POST | `/admissions/:id/settle` | **CASHIER**, ADMIN | Create final Bill + record final payment + complete discharge billing |

#### Vitals & Notes

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/admissions/:id/vitals` | NURSE, DOCTOR, ADMIN | Record vitals |
| GET | `/admissions/:id/vitals` | NURSE, DOCTOR, ADMIN | List vitals (chronological) |
| POST | `/admissions/:id/notes` | NURSE, DOCTOR, ADMIN | Add nursing note |
| GET | `/admissions/:id/notes` | NURSE, DOCTOR, ADMIN | List nursing notes |

#### Nurse Management

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/nurse-departments` | ADMIN | Create department |
| GET | `/nurse-departments` | ADMIN, NURSE | List departments |
| POST | `/duty-assignments` | ADMIN | Assign nurse to shift |
| GET | `/duty-assignments` | ADMIN, NURSE | List duty assignments (filterable by date, department) |

---

## 5. Frontend Pages

| Route | File | Purpose |
|---|---|---|
| `/ipd` | `ipd/page.tsx` | Main IPD page with active admissions list + bed stats |
| `/ipd/new` | `ipd/new/page.tsx` | New IPD admission form |
| `/ipd/[admissionId]` | `ipd/[admissionId]/page.tsx` | Admission detail with tabs |
| `/ipd/[admissionId]/charges` | `ipd/[admissionId]/charges/page.tsx` | Charge management |
| `/ipd/[admissionId]/vitals` | `ipd/[admissionId]/vitals/page.tsx` | Vital signs chart |
| `/ipd/[admissionId]/notes` | `ipd/[admissionId]/notes/page.tsx` | Nursing notes |
| `/ipd/beds` | `ipd/beds/page.tsx` | Bed availability grid |
| `/billing` (IPD tab) | `billing/page.tsx` | Third tab showing active IPD admissions with settlement actions |

### IPD Tab on Billing Page

The `/billing` page gets a third tab next to OPD and Emergency:

**"IPD (Active)" tab content:**
- Stats cards: Active admissions, Occupied beds, Outstanding dues
- Table of active admissions: Admission #, Patient, Ward/Bed, Doctor, Days since admission, Total charges, Paid, Balance
- Action buttons per row: "View" (→ /ipd/[id]), "Part Settlement" (→ /ipd/[id]?tab=settlement), "Settle & Discharge" (→ /ipd/[id]?tab=settlement)

**Access:** RECEPTION sees all rows (can also create new admission). CASHIER sees all rows (can settle payment). DOCTOR sees their own patients' admissions.

---

## 6. Bed Charge Auto-Accrual

### How It Works

Bed charges are NOT accrued via a cron job. Instead, they are **lazily accrued** — calculated on-demand when the bill is viewed or at settlement time.

### Algorithm

```
function accrueBedCharges(admissionId):
    admission = get IPDAdmission
    if admission.status != ADMITTED:
        return  // don't accrue for discharged patients

    fromDate = admission.lastAccruedDate ?? admission.admissionDate
    toDate = today (or discharge date)

    if fromDate >= toDate:
        return  // already up to date

    // Get all bed allocations + ward changes in date order
    changes = get IPDWardChange sorted by changedAt ASC
    allocations = get BedAllocation sorted by allocatedAt ASC

    for each day from fromDate to toDate:
        // Determine which bed the patient was in on this day
        bed = resolveBedForDate(day, changes, allocations)
        dailyRate = bed.dailyCharge
        
        // Check if charge already exists for this day
        if NOT exists IPDCharge(admissionId, chargeType=BED_CHARGE, itemName="Bed charge Day {day}") 
            create IPDCharge(
                admissionId,
                chargeType: BED_CHARGE,
                itemName: "Bed charge - Day {day-index} ({bed.bedNumber})",
                quantity: 1,
                unitPrice: dailyRate,
                totalPrice: dailyRate,
                addedBy: "system"
            )

    admission.lastAccruedDate = toDate
    save admission
```

### Trigger Points

Accrual catch-up runs automatically when:
1. `GET /admissions/:id` is called (includes current total charges)
2. `GET /admissions/:id/settlement-preview` is called
3. `POST /admissions/:id/payments` is called (before recording payment)
4. `POST /admissions/:id/settle` is called (before finalization)
5. `POST /admissions/:id/accrue-bed-charges` is called manually

### Ward/Bed Changes

When a patient changes ward/bed mid-stay:
1. `IPDWardChange` records the transfer
2. Old `BedAllocation.vacatedAt` is set
3. New `BedAllocation` record created
4. Old bed status → AVAILABLE, new bed → OCCUPIED
5. Accrual for days after the change uses the new bed's `dailyCharge`

---

## 7. Insurance Flow

### Data Model

Insurance details are stored as JSON in `IPDAdmission.insuranceDetails`:

```json
{
  "provider": "Star Health Insurance",
  "tpaName": "Star Health TPA",
  "policyNumber": "SH-2024-12345",
  "preAuthRef": "PA-2425-67890",
  "preAuthAmount": 70000.00,
  "coPayPercent": 10,
  "coPayAmount": 7000.00,
  "coverageType": "CASHLESS",
  "claimNumber": null,
  "claimStatus": "PRE_AUTH_APPROVED",
  "validUntil": "2026-12-31"
}
```

### Collection Flow

At settlement (discharge or part-settlement):

1. System shows split settlement preview:
   - Total charges: ₹X
   - Insurance covers: ₹Y (up to preAuthAmount - coPay)
   - Patient pays: ₹Z (remaining balance)

2. Cashier creates **two IPDPayment records**:
   - `{ amount: ₹Z, paymentMethod: CASH/UPI/CARD, paymentType: INTERIM/FINAL }` — collected from patient
   - `{ amount: ₹Y, paymentMethod: INSURANCE/TPA, paymentType: INTERIM/FINAL }` — NOT collected, just recorded as receivable

3. At final settlement, the `Bill` record's `totalAmount` = total charges, `paidAmount` = patient cash portion only. The insurance portion is tracked in IPDPayments but the final Bill shows the total.

### Future Integration

The `insuranceDetails` JSON is designed to be replaced by a full `InsuranceClaim` model when direct TPA API integration is built. The JSON structure allows storing:
- TPA/provider identifiers that map to API endpoints
- Pre-auth request/response data
- Claim submission data
- Claim status tracking

---

## 8. Role-Based Access

| Action | RECEPTION | DOCTOR | NURSE | CASHIER | ADMIN |
|---|---|---|---|---|---|
| View admissions list | ✅ All | ✅ Own patients | ✅ Assigned dept | ✅ All | ✅ All |
| Create admission | ✅ | ✅ | ❌ | ❌ | ✅ |
| Update admission details | ✅ Basic | ✅ Diagnosis | ❌ | ❌ | ✅ |
| Add charges | ✅ | ✅ | ✅ | ❌ | ✅ |
| View charges | ✅ | ✅ | ✅ | ✅ | ✅ |
| Record payment | ❌ | ❌ | ❌ | ✅ | ✅ |
| View payments | ✅ | ✅ | ❌ | ✅ | ✅ |
| Settle bill | ❌ | ❌ | ❌ | ✅ | ✅ |
| Ward change | ✅ | ❌ | ❌ | ❌ | ✅ |
| Record vitals | ❌ | ✅ | ✅ | ❌ | ✅ |
| Add nurse notes | ❌ | ✅ | ✅ | ❌ | ✅ |
| Manage nurse dept | ❌ | ❌ | ❌ | ❌ | ✅ |
| Duty assignments | ❌ | ❌ | ❌ | ❌ | ✅ |
| Bed availability view | ✅ | ✅ | ✅ | ✅ | ✅ |
| Discharge request | ❌ | ✅ | ❌ | ❌ | ❌ |
| Complete discharge | ❌ | ✅ | ❌ | ❌ | ✅ |

---

## 9. Implementation Order

### Sprint 1 — Schema & Backend Foundation
1. ✅ Schema design & Prisma migration
2. [ ] IPD routes: admissions CRUD (create, list, get, update)
3. [ ] IPD routes: wards + beds (list, availability)
4. [ ] IPD routes: ward change + bed allocation management
5. [ ] IPD routes: charges (add, list, auto-accrue)
6. [ ] IPD routes: payments (record, list) — cashier-only guard
7. [ ] IPD routes: settlement preview + finalize (create Bill)
8. [ ] IPD routes: vitals + nurse notes CRUD
9. [ ] IPD routes: nurse departments + duty assignments
10. [ ] Register routes in server.js

### Sprint 2 — Frontend Foundation
11. [ ] IPD list page (`/ipd`) with filters + bed stats
12. [ ] New admission form (`/ipd/new`)
13. [ ] Admission detail page (`/ipd/[id]`) with tab navigation
14. [ ] Charges tab on admission detail
15. [ ] Vitals tab (chart/table view)
16. [ ] Nursing notes tab
17. [ ] Ward change modal

### Sprint 3 — Billing & Settlement
18. [ ] IPD tab on billing page (`/billing`)
19. [ ] Part-settlement flow (payment modal)
20. [ ] Settlement preview + final bill creation
21. [ ] Insurance details entry on admission form
22. [ ] Insurance split in settlement flow

### Sprint 4 — Admin & Management
23. [ ] Bed availability grid (`/ipd/beds`)
24. [ ] Nurse department management
25. [ ] Duty assignment management
26. [ ] Navigation + route permissions updates

---

## 10. Backend Route Implementation Details

### Route File: `src/modules/ipd/ipd.routes.js`

The existing file is a stub (8 lines). It will be fully rewritten.

#### Key Implementation Notes

**Admission Number Generation:**
Format: `IPD{TENANT_CODE}{YEAR}{SEQ}` (e.g. `IPDMBS2026001`)
Similar to employee ID generation — find max seq, increment.

**Validation Rules:**
- `POST /admissions`: patientId, admittingDoctorId, admissionReason required. wardId + bedId required (or allocated automatically).
- `POST /admissions/:id/charges`: chargeType, itemName, unitPrice required. Only for active admissions (status = ADMITTED).
- `POST /admissions/:id/payments`: amount, paymentMethod, paymentType required. CASHIER-only. Amount must be > 0.
- `POST /admissions/:id/settle`: Only for ADMITTED status. Creates a single IPDPayment with paymentType=FINAL.
- `POST /admissions/:id/discharge`: Only for ADMITTED status (or after settle). Sets actualDischarge, status=DISCHARGED.

**Cashier-Only Payment Guard:**
```javascript
// In the payments routes
if (req.user.role !== ROLES.CASHIER && req.user.role !== ROLES.ADMIN) {
  throw new AppError('Only cashiers can record payments.', 403);
}
```

**Settlement Logic (`POST /admissions/:id/settle`):**
```javascript
// 1. Accrue any pending bed charges
await accrueBedCharges(admissionId);

// 2. Calculate totals
const charges = await prisma.iPDCharge.findMany({ where: { admissionId } });
const totalCharges = charges.reduce((sum, c) => sum + Number(c.totalPrice), 0);
const payments = await prisma.iPDPayment.findMany({ where: { admissionId } });
const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount), 0);
const balance = totalCharges - totalPaid;

// 3. Create final Bill
const bill = await prisma.bill.create({
  data: {
    tenantId, billNumber, patientId, ipdAdmissionId: admissionId,
    billType: 'IPD', subtotal: totalCharges, totalAmount: totalCharges,
    paidAmount: totalPaid, balanceAmount: balance,
    paymentStatus: balance <= 0 ? 'PAID' : 'PARTIALLY_PAID',
    createdBy: req.user.id,
    // discount/tax handled if applicable
  }
});
```

---

## 11. Frontend Implementation Details

### IPD Admission Detail Page — Tab Structure

The `/ipd/[admissionId]` page has the following tabs:

| Tab | Content | Roles |
|---|---|---|
| **Overview** | Patient info, doctor, ward/bed, dates, diagnosis, insurance badge | All |
| **Charges** | Itemized list of IPDCharges grouped by type, add charge button | DOCTOR, NURSE, RECEPTION, ADMIN |
| **Payments** | List of IPDPayments, record payment button | CASHIER, ADMIN |
| **Settlement** | Preview: total charges - payments = balance, settle button | CASHIER, ADMIN |
| **Vitals** | Chronological list of VitalRecords, chart view, add vitals button | DOCTOR, NURSE, ADMIN |
| **Notes** | List of NurseNotes grouped by category, add note button | DOCTOR, NURSE, ADMIN |
| **Ward History** | Timeline of IPDWardChange records | RECEPTION, ADMIN |

### Key UI Components

**Bed Selector:**
- Dropdown cascading: Select Ward → Shows available beds in that ward → Select bed
- Shows bed type, daily charge, status
- Filters to show only AVAILABLE beds

**Charge Form:**
- Charge type dropdown (BED_CHARGE / PROCEDURE / MEDICINE / ...)
- Item name (text or pre-populated from catalogue)
- Quantity + unit price → auto-calculates total
- "Add" button → POST /admissions/:id/charges

**Payment Modal:**
- Shows current accumulated total (after accrual catch-up)
- Shows previous payments
- Amount input
- Payment method selector (CASH / CARD / UPI / NETBANKING / INSURANCE / TPA)
- Payment type: ADVANCE / INTERIM (for part settlement) or FINAL (at discharge)
- If INSURANCE/TPA: show insurance details from admission
- "Record Payment" button → POST /admissions/:id/payments

**Settlement Screen:**
- Full breakdown: all charges, all payments, balance
- Insurance split (if applicable): insurance covers X, patient pays Y
- "Settle & Generate Bill" button → POST /admissions/:id/settle
- After settle: show success with bill number + link to Bill

### API Client Additions (`api.ts`)

```typescript
export const ipdApi = {
  // Admissions
  createAdmission: (data) => api.post('/ipd/admissions', data),
  listAdmissions: (params) => api.get('/ipd/admissions', { params }),
  getAdmission: (id) => api.get(`/ipd/admissions/${id}`),
  updateAdmission: (id, data) => api.patch(`/ipd/admissions/${id}`, data),
  requestDischarge: (id) => api.post(`/ipd/admissions/${id}/discharge-request`),
  completeDischarge: (id, data) => api.post(`/ipd/admissions/${id}/discharge`, data),

  // Wards & Beds
  listWards: () => api.get('/ipd/wards'),
  listBeds: (params) => api.get('/ipd/beds', { params }),
  changeWard: (id, data) => api.post(`/ipd/admissions/${id}/ward-change`, data),

  // Charges
  addCharge: (id, data) => api.post(`/ipd/admissions/${id}/charges`, data),
  listCharges: (id) => api.get(`/ipd/admissions/${id}/charges`),
  accrueBedCharges: (id) => api.post(`/ipd/admissions/${id}/accrue-bed-charges`),

  // Payments
  recordPayment: (id, data) => api.post(`/ipd/admissions/${id}/payments`, data),
  listPayments: (id) => api.get(`/ipd/admissions/${id}/payments`),

  // Settlement
  getSettlementPreview: (id) => api.get(`/ipd/admissions/${id}/settlement-preview`),
  settle: (id, data) => api.post(`/ipd/admissions/${id}/settle`, data),

  // Vitals & Notes
  addVitals: (id, data) => api.post(`/ipd/admissions/${id}/vitals`, data),
  listVitals: (id) => api.get(`/ipd/admissions/${id}/vitals`),
  addNote: (id, data) => api.post(`/ipd/admissions/${id}/notes`, data),
  listNotes: (id) => api.get(`/ipd/admissions/${id}/notes`),

  // Nurse Management
  createDepartment: (data) => api.post('/ipd/nurse-departments', data),
  listDepartments: () => api.get('/ipd/nurse-departments'),
  assignDuty: (data) => api.post('/ipd/duty-assignments', data),
  listDutyAssignments: (params) => api.get('/ipd/duty-assignments', { params }),
};
```

---

## 12. Appendix: Key Files

| File | Path |
|---|---|
| Schema | `hms-backend/prisma/schema.prisma` (IPD section at ~line 911) |
| Migration SQL | `hms-backend/prisma/migrations/20260511_add_ipd_module/migration.sql` |
| Backend routes (stub) | `hms-backend/src/modules/ipd/ipd.routes.js` |
| Server registration | `hms-backend/src/server.js` (add line to register ipd routes) |
| Frontend IPD pages | `hms-frontend/src/app/ipd/*` |
| Frontend billing page | `hms-frontend/src/app/billing/page.tsx` |
| Frontend API client | `hms-frontend/src/lib/api.ts` |
| Route permissions | `hms-frontend/src/components/layout/AppLayout.tsx` |
| Auth context | `hms-frontend/src/lib/auth-context.tsx` |
| This document | `ws/Project Backlogs/ipd-module-document.md` |

---

*This document is a specialized companion to `project-complete-document.md`. For general project context (multi-tenant, auth, roles, deployment), refer to the main project document.*
