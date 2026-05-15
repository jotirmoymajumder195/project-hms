# Emergency Module — User Acceptance Testing (UAT) Document

> **Version:** 2.0  
> **Date:** 2026-05-12  
> **Module:** Emergency (Phase 1)  
> **Prepared for:** MBS Hospital Management System  
> **Tester:** _____________________  **Date Tested:** _____________________  

---

## Table of Contents

1. [Test Environment](#1-test-environment)
2. [Prerequisites](#2-prerequisites)
3. [TC-A: Authentication & Authorization](#3-tc-a-authentication--authorization)
4. [TC-B: Billing Page — EMERGENCY Tab (Cashier View)](#4-tc-b-billing-page--emergency-tab)
5. [TC-C: Generate Bill — EMERGENCY Type (Reception)](#5-tc-c-generate-bill--emergency-type)
6. [TC-D: Doctor Selector & Consultation Fee Pre-fill](#6-tc-d-doctor-selector--consultation-fee)
7. [TC-E: Confirmation Popup & Bill Creation](#7-tc-e-confirmation-popup--bill-creation)
8. [TC-F: Cashier Payment Collection](#8-tc-f-cashier-payment-collection)
9. [TC-G: Real-Time Polling](#9-tc-g-real-time-polling)
10. [TC-H: Patient Profile — Emergency Tab](#10-tc-h-patient-profile--emergency-tab)
11. [TC-I: Backend API — Emergency Endpoints](#11-tc-i-backend-api--emergency-endpoints)
12. [TC-J: Backend — Medicines Catalogue](#12-tc-j-backend--medicines-catalogue)
13. [TC-K: Backend — Doctor Routes](#13-tc-k-backend--doctor-routes)
14. [TC-L: Modified Existing Pages](#14-tc-l-modified-existing-pages)
15. [TC-M: End-to-End Workflow](#15-tc-m-end-to-end-workflow)
16. [TC-N: Edge Cases & Error Handling](#16-tc-n-edge-cases--error-handling)
17. [Summary](#17-summary)

---

## 1. Test Environment

| Parameter | Value |
|-----------|-------|
| Backend URL | `https://api.sarvikatech.in/api/v1` |
| Frontend URL | Vercel deployment or `http://localhost:3000` |
| Database | AWS RDS PostgreSQL |
| Browser | Chrome/Firefox/Edge latest |
| Screen sizes | Desktop (1920×1080), Tablet (768×1024), Mobile (375×812) |
| User roles to test | ADMIN, RECEPTION, CASHIER, DOCTOR |

### Test Accounts Required

| Employee ID | Role | Purpose |
|-------------|------|---------|
| ADMIN-001 | ADMIN | Full access, approve modifications |
| RECP-001 | RECEPTION | Create emergency bills using Generate Bill → EMERGENCY type |
| (Cashier TBD) | CASHIER | Collect payments via billing page EMERGENCY tab |
| DOC-001 | DOCTOR | Ensure has `emergencyConsultationFee` set |

> **Pre-test setup:** Ensure at least one doctor has `emergencyConsultationFee` set to a non-zero value.

---

## 2. Prerequisites

Before testing, verify these conditions:

- [ ] 2.1. Login page accepts Employee ID + Password + Tenant
- [ ] 2.2. Default tenant `mbs` exists
- [ ] 2.3. ADMIN-001 user exists
- [ ] 2.4. At least one RECEPTION user exists
- [ ] 2.5. At least one CASHIER user exists (create via Settings → Staff)
- [ ] 2.6. At least one doctor has `emergencyConsultationFee` set
- [ ] 2.7. At least one patient record exists (for testing)

---

## 3. TC-A: Authentication & Authorization

Verify role-based route access.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| A1 | RECEPTION logs in | Login as RECP-001, correct password | Redirected to `/dashboard` or `/billing` | | |
| A2 | CASHIER logs in | Login as CASHIER user | Redirected to `/billing` | | |
| A3 | ADMIN logs in | Login as ADMIN-001 | Redirected to `/dashboard` | | |
| A4 | DOCTOR logs in | Login as DOC-001 | Redirected to `/opd` | | |
| A5 | CASHIER sees only Billing + Patients in sidebar | Login as CASHIER, check sidebar | Only Billing and Patients links visible | | |
| A6 | CASHIER accesses `/billing` | Navigate to `/billing` | Page loads with OPD / Emergency / IPD tabs | | |
| A7 | CASHIER sees Emergency tab by default | Login as CASHIER, go to `/billing` | Emergency tab is active | | |
| A8 | RECEPTION sees OPD tab by default | Login as RECP-001, go to `/billing` | OPD tab is active | | |
| A9 | CASHIER cannot access `/settings` | Login as CASHIER, navigate to `/settings` | Redirected to `/billing` | | |
| A10 | CASHIER cannot access `/doctors` | Login as CASHIER, navigate to `/doctors` | Redirected to `/billing` | | |

---

## 4. TC-B: Billing Page — EMERGENCY Tab (Cashier View)

Cashier views and collects emergency bill payments from the billing page's Emergency tab.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| B1 | Tab bar visible | Navigate to `/billing` | OPD / Emergency / IPD (Soon) tabs visible | | |
| B2 | Emergency tab shows stats | Click Emergency tab | 4 stat cards visible: Pending, Collected today, Total today, Admission recommended | | |
| B3 | Pending bills listed | Create an emergency bill (see TC-C) | Bill appears in Pending list with patient name, amount, "Collect" button | | |
| B4 | View toggle works | Click "Today" vs "Pending" | List switches between views | | |
| B5 | Invoice button works | Click Invoice on a bill | Invoice PDF opens in new tab | | |
| B6 | Collect button navigates | Click "Collect" | Goes to `/emergency/{billId}` | | |
| B7 | New emergency bill button | Click "New emergency bill" | Goes to `/billing/new` | | |

---

## 5. TC-C: Generate Bill — EMERGENCY Type (Reception)

Receptionist creates an emergency bill using the existing billing form.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| C1 | EMERGENCY type exists | Navigate to `/billing/new` | EMERGENCY is one of the bill type options | | |
| C2 | Select EMERGENCY type | Click "EMERGENCY" button | Bill type switches to EMERGENCY; admission recommended checkbox + doctor selector appear | | |
| C3 | Switch away from EMERGENCY | Click "OPD" | Doctor selector and checkbox disappear | | |
| C4 | Fill patient + items | Select patient, add items | Items list works as before | | |
| C5 | Generate without doctor | Submit bill with EMERGENCY type, no doctor selected | Bill created successfully (doctor optional) | | |
| C6 | Generate with payment | Fill payment section, submit | Bill created with payment collected | | |

---

## 6. TC-D: Doctor Selector & Consultation Fee Pre-fill

When EMERGENCY is selected, a doctor picker appears that pre-fills the consultation fee.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| D1 | Doctor selector visible | Select EMERGENCY type | Doctor dropdown appears with "Attending doctor" label | | |
| D2 | Doctors listed | Open dropdown | All doctors shown, with emergency fee in parentheses if set | | |
| D3 | Select a doctor with emergency fee | Choose a doctor who has `emergencyConsultationFee` | First item auto-set to "Consultation - {doctor name}" with the correct fee as rate | | |
| D4 | Select a doctor without emergency fee | Choose a doctor with no emergency fee set | Consultation item added with their regular `consultationFee` or 0 | | |
| D5 | Change doctor | Select a different doctor | Consultation item updates to new doctor's name and fee | | |
| D6 | Switch to OPD then back | Switch to OPD then back to EMERGENCY | Doctor selector resets; no consultation item auto-added until doctor re-selected | | |

---

## 7. TC-E: Confirmation Popup & Bill Creation

Before finalizing, a confirmation popup warns about admin approval for modifications.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| E1 | Confirmation popup triggers | Click "Generate bill" button | Confirmation modal appears | | |
| E2 | Warning text visible | Check modal content | Warning: "Further modification to existing items will require admin approval." | | |
| E3 | Bill summary in modal | Check modal | Shows patient name, bill type, item count, total, payment details | | |
| E4 | Cancel from modal | Click "Cancel" in confirmation | Modal closes, form unchanged | | |
| E5 | Confirm creates bill | Click "Confirm & generate" | Bill created successfully, success screen shown | | |
| E6 | Success screen shows bill details | After creation | Bill number, amount, payment status shown; Print/WhatsApp/New bill buttons visible | | |
| E7 | New bill resets form | Click "New bill" on success screen | Form resets to initial state | | |

---

## 8. TC-F: Cashier Payment Collection

Cashier collects payment from the emergency bill detail page.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| F1 | Navigate to bill detail | Click "Collect" on pending emergency bill | `/emergency/{billId}` loads with bill details | | |
| F2 | Bill summary displayed | View page | Bill number, patient, status badge, amounts visible | | |
| F3 | Collect payment button visible | Unpaid bill | "Collect payment" button visible | | |
| F4 | Collect payment on paid bill | Fully paid bill | "Collect payment" NOT visible | | |
| F5 | Payment modal opens | Click "Collect payment" | Modal with method selector, amount field, transaction ref | | |
| F6 | Record full payment | Enter amount = balance, click Record | Payment recorded, status changes to PAID, balance = 0 | | |
| F7 | Record partial payment | Enter amount < balance | Status = PARTIALLY_PAID, balance reduced | | |
| F8 | Add items to bill | Click "Add items", fill form | Items added to bill, total recalculated | | |
| F9 | Request modification | Click modify icon on item, fill reason | Modification request created (PENDING) | | |
| F10 | Overpayment rejected | Enter amount > balance | Error shown: "Payment amount exceeds balance due" | | |

---

## 9. TC-G: Real-Time Polling

The Emergency tab auto-refreshes to show newly created bills.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| G1 | Auto-refresh | Stay on Emergency tab, create a new emergency bill in another tab | Within 30 seconds, new bill appears in the list | | |
| G2 | No duplicate data | Quick successive creates | Each bill appears once, no duplicates | | |
| G3 | Paid bills disappear from pending | Collect payment for a pending bill | After next poll, bill moves from Pending to Today (PAID) list | | |

---

## 10. TC-H: Patient Profile — Emergency Tab

Patient profile shows emergency bills under an "Emergency" tab.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| H1 | Patient profile has Emergency tab | Navigate to `/patients/{id}` | "Emergency" tab visible alongside OPD, Bills etc. | | |
| H2 | Emergency bills listed | Click Emergency tab | Shows emergency bills for this patient | | |
| H3 | Bill details | View an emergency bill in list | Bill number, date, amount, status visible | | |
| H4 | Link to invoice | Click invoice button | Invoice opens | | |

---

## 11. TC-I: Backend API — Emergency Endpoints

Test the dedicated emergency API endpoints.

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| I1 | Create emergency bill | POST `/emergency/bills` with valid body | 201, bill with `billType: EMERGENCY` | | |
| I2 | Confirm bill | POST `/emergency/bills/{id}/confirm` | Bill confirmed, items locked | | |
| I3 | Record payment | POST `/emergency/bills/{id}/payment` with valid amount | Payment recorded, balance updated | | |
| I4 | Add items | POST `/emergency/bills/{id}/items` | Items added to bill | | |
| I5 | Request modification | POST `/emergency/bills/{id}/modify-request` | Modification request created PENDING | | |
| I6 | Approve modification | PATCH `/emergency/bills/{id}/modify-request/{reqId}` with APPROVED | Item modified | | |
| I7 | Reject modification | PATCH with REJECTED | Request rejected | | |
| I8 | Get pending bills | GET `/emergency/bills/pending` | List of unpaid/unconfirmed emergency bills | | |
| I9 | Get today's bills | GET `/emergency/bills/today` | List of today's emergency bills | | |
| I10 | Get single bill | GET `/emergency/bills/{id}` | Full bill detail with items | | |
| I11 | Unauthorized access (DOCTOR) | Auth as DOC-001, call POST | 403 Forbidden | | |
| I12 | Invalid patientId | POST with non-existent patientId | 404 Not Found | | |
| I13 | Overpayment rejected | POST payment with amount > balance | 400 Bad Request | | |

---

## 12. TC-J: Backend — Medicines Catalogue

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| J1 | List medicines | GET `/medicines` | 200, array of medicines | | |
| J2 | Search medicines | GET `/medicines?search=para` | Filtered results | | |
| J3 | Get single medicine | GET `/medicines/{id}` | 200, medicine object | | |
| J4 | Create medicine | POST `/medicines` with valid body | 201, medicine created | | |
| J5 | Update medicine | PATCH `/medicines/{id}` | 200, medicine updated | | |
| J6 | Toggle active status | PATCH `/medicines/{id}/toggle-status` | Status toggled | | |

---

## 13. TC-K: Backend — Doctor Routes

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| K1 | Create doctor with emergency fee | POST `/doctors` with `emergencyConsultationFee` | Doctor created with fee saved | | |
| K2 | Update emergency fee | PATCH `/doctors/{id}` with new fee | Fee updated | | |
| K3 | Doctor list includes fee | GET `/doctors` | Fee field returned in response | | |

---

## 14. TC-L: Modified Existing Pages

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| L1 | Billing page has OPD/Emergency tabs | Go to `/billing` | Tabs visible | | |
| L2 | CASHIER home is `/billing` | Login as CASHIER | Redirected to `/billing` | | |
| L3 | Sidebar: Billing and Patients for CASHIER | Login as CASHIER | Only Billing + Patients in sidebar | | |
| L4 | Sidebar: No standalone Emergency nav | All roles | No "Emergency" nav item | | |
| L5 | `/emergency` redirects to `/billing` | Navigate to `/emergency` | Redirected to `/billing` | | |
| L6 | `/emergency/new` redirects to `/billing/new` | Navigate to `/emergency/new` | Redirected to `/billing/new` | | |
| L7 | Settings has Emergency tab | Go to `/settings` | Emergency tab visible with catalogue links | | |
| L8 | Settings can create CASHIER user | Admin creates user with CASHIER role | User created successfully | | |
| L9 | Doctor profile has emergencyConsultationFee | Edit doctor in settings | Fee field visible and saveable | | |

---

## 15. TC-M: End-to-End Workflow

Simulate a complete emergency visit.

| # | Step | Expected | Status | Notes |
|---|------|----------|--------|-------|
| 1 | RECEPTION logs in, goes to `/billing/new` | Form loads | | |
| 2 | Selects EMERGENCY bill type | EMERGENCY options appear | | |
| 3 | Selects a doctor | Consultation item pre-filled with fee | | |
| 4 | Checks "Admission recommended" | Checkbox ticked | | |
| 5 | Adds items (consumables, medicines) | Items added to list | | |
| 6 | Clicks "Generate bill" | Confirmation popup appears with warning text | | |
| 7 | Clicks "Confirm & generate" | Bill created, success screen shown | | |
| 8 | CASHIER logs in (different browser/tab), goes to `/billing` | Emergency tab is active, new bill visible in Pending list (within 30s) | | |
| 9 | CASHIER clicks "Collect" | Bill detail page loads | | |
| 10 | CASHIER records payment (full) | Payment recorded, bill status = PAID | | |
| 11 | CASHIER verifies bill no longer shows in Pending | Switches to Today tab, bill appears as PAID | | |
| 12 | ADMIN logs in, goes to patient profile | Emergency tab shows the bill with PAID status | | |

---

## 16. TC-N: Edge Cases & Error Handling

| ID | Test | Steps | Expected | Status | Notes |
|----|------|-------|----------|--------|-------|
| N1 | Create bill without selecting patient | Click Generate bill | Error: "Select a patient" | | |
| N2 | Create bill with empty items | Fill patient, leave items blank | Error: "Fill all item details" | | |
| N3 | Payment exceeds total | Enter payment > total | Frontend validation prevents | | |
| N4 | Overpayment via API | POST payment with amount > balance | 400 Bad Request | | |
| N5 | Pay already-paid bill | Collect payment on PAID bill | Error: "Bill is already fully paid" | | |
| N6 | Non-EMERGENCY bill on emergency endpoint | POST payment on OPD bill | Error: "Not an emergency bill" | | |
| N7 | Duplicate bill number | System generates unique bill number | Bill number is unique | | |
| N8 | Cashier cannot create bill | Login as CASHIER, try `/billing/new` or POST | 403 or redirect | | |
| N9 | RECEPTION cannot collect payment | Login as RECP-001, POST payment | 403 Forbidden | | |
| N10 | RECEPTION cannot approve modification | PATCH approve as RECP-001 | 403 Forbidden | | |
| N11 | CASHIER cannot approve modification | PATCH approve as CASHIER | 403 Forbidden | | |
| N12 | Invalid UUID in route | GET `/emergency/bills/not-a-uuid` | 422 Validation error | | |

---

## 17. Summary

| Section | Tests | Pass | Fail | Blocked | Notes |
|---------|-------|------|------|---------|-------|
| TC-A: Auth & Authorization | 10 | | | | |
| TC-B: Billing EMERGENCY Tab | 7 | | | | |
| TC-C: Generate Bill EMERGENCY Type | 6 | | | | |
| TC-D: Doctor Selector & Fee | 6 | | | | |
| TC-E: Confirmation Popup | 7 | | | | |
| TC-F: Cashier Payment Collection | 10 | | | | |
| TC-G: Real-Time Polling | 3 | | | | |
| TC-H: Patient Profile | 4 | | | | |
| TC-I: Backend API | 13 | | | | |
| TC-J: Medicines Catalogue | 6 | | | | |
| TC-K: Doctor Routes | 3 | | | | |
| TC-L: Modified Existing Pages | 9 | | | | |
| TC-M: E2E Workflow | 12 steps | | | | |
| TC-N: Edge Cases | 12 | | | | |
| **TOTAL** | **108** | | | | |

### Known Issues / Observations

| # | Issue | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | `modify-request` can be called on unconfirmed bills (no restriction) | Low | Open | Should limit to confirmed bills? |
| 2 | No notification system for modification requests | Medium | Deferred | Will be addressed in Phase 2 |

### Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Tested by | | | |
| Reviewed by | | | |
| Approved by | | | |

---

*End of UAT Document*
