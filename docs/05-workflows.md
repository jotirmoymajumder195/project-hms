# Key Workflows

## 1. Patient Check-In Flow (Walk-In)

```
Reception opens Walk-In page
  → Selects patient (existing or register new)
  → Selects doctor
  → (Optional) Adds bill items, discount
  → (Optional) Collects payment
  → Submit

Backend (single transaction):
  1. Check for duplicate phone
  2. Generate token number (sequential per doctor per day)
  3. Create Appointment (status: SCHEDULED)
  4. Create OPDVisit
  5. Create Bill with items
  6. Record Payment (if any)
  7. Update Appointment status → CHECKED_IN
  8. Return bill + visit + appointment data

Reception sees success toast with "Print invoice" link
```

## 2. Scheduled Appointment + Check-In

```
Reception books appointment
  → Selects patient, doctor, date, time slot
  → Appointment created (SCHEDULED)

On appointment day:
  Reception clicks "Check in" on the queue row
  → CheckInModal opens with billing form
  → Same atomic transaction as walk-in
  → Appointment → CHECKED_IN
```

## 3. Doctor Consultation Flow

```
Reception starts doctor's session (OPD Sessions tab)
  → DoctorQueue created/updated (isActive: true)
  → If Token 1 checked in → auto-advances to IN_CONSULTATION

Doctor opens OPD page
  → Sees queue ordered by token number
  → Current patient highlighted with "Write Prescription" button

Doctor clicks "Write Prescription"
  → Consultation page opens with visit data
  → Enters vitals, complaint, symptoms, diagnosis
  → Adds medicines (digital) or uploads paper Rx
  → (Optional) Adds consumables used
  → Clicks "Complete consultation"

Doctor clicks "Next" button
  → Current visit marked awaitingCompletion
  → Token increments to next CHECKED_IN patient
  → If sequential gap → skips, tries later (skippedAt)

Reception sees awaitingCompletion = true
  → Uploads paper prescription if needed
  → Finalizes visit
```

## 4. Queue Skip & Recovery

```
Doctor clicks Next:
  1. Marks current patient's visit as awaitingCompletion
  2. Increments token (e.g., from 3 to 4)
  3. Checks token 4: if not CHECKED_IN → marks skippedAt, tries token 5
  4. If token 5 is CHECKED_IN → serves it
  5. If no sequential token found → looks for previously skipped patients
     who have since checked in → serves earliest skipped token
```

## 5. Token Board Display

```
DISPLAY account logs in → fullscreen token-board page
  → Polls GET /appointments/token-board every 3 seconds
  → Shows each active chamber with doctor name + current token
  → Live clock + date displayed
  → Never auto-logs out (1-year JWT token)
```

## 6. Billing & Payment

```
Option A: Collect at check-in
  → Items added in CheckInModal
  → Payment collected (CASH/UPI/CARD/etc.)
  → Bill status: PAID or PARTIALLY_PAID

Option B: Generate bill later
  → Billing page → "Generate bill" → select patient + items
  → Bill created PENDING
  → Later: "Collect payment" → record payment → status updates

Daily summary: Shows all bills for a date with totals
  → Clickable stat cards for drill-down
  → Paid / Pending / Partially paid breakdown
```

## 7. OPD Sessions & Chamber Management

```
Admin creates chambers → assigns doctors (one-off or recurring)
  → Recurring: dayOfWeek-based
  → One-off: specific date

Reception sees assignments on Appointments → OPD Sessions tab
  → "Start Session" for doctor whose time window is active
  → Auto-advances to Token 1 if patient checked in
  → "End Session" marks remaining SCHEDULED as NO_SHOW
  → Token board updates in real-time
```

## 8. DPDPA 2023 Compliance

```
- Patient registration requires explicit consent (checkbox)
- Consent logged in ConsentLog with exact text shown
- Aadhaar encrypted with AES-256-GCM before storage
- All data access logged to AuditLog
- Data export/deletion request workflow via /data-request
- Cross-patient access by doctors flagged in audit
- Audit logs searchable by admin with date/resource/user filters
```

## 9. First-Login Password Change (S01)

```
Doctor account created with mustChangePassword = true
Doctor logs in → frontend detects flag → ForcePasswordChange screen
Doctor sets new password → POST /auth/force-change-password
→ mustChangePassword set to false → redirects to login
→ Doctor logs in again with new password
```
