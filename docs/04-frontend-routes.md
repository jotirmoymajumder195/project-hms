# Frontend Routes & Pages

## Role-Based Access

| Page            | Path                          | Roles                           |
|-----------------|-------------------------------|---------------------------------|
| Login           | `/login`                      | Public                          |
| Dashboard       | `/dashboard`                  | ADMIN, RECEPTION, DOCTOR        |
| Patients        | `/patients`                   | ADMIN, RECEPTION, DOCTOR        |
| Patient New     | `/patients/new`               | ADMIN, RECEPTION                |
| Patient Detail  | `/patients/[id]`              | ADMIN, RECEPTION, DOCTOR        |
| Appointments    | `/appointments`               | ADMIN, RECEPTION, DOCTOR        |
| Appointment New | `/appointments/new`           | ADMIN, RECEPTION                |
| Walk-in         | `/appointments/walk-in`       | ADMIN, RECEPTION                |
| OPD Queue       | `/opd`                        | ADMIN, RECEPTION, DOCTOR        |
| OPD Consult     | `/opd/[visitId]`              | ADMIN, RECEPTION, DOCTOR        |
| Billing         | `/billing`                    | ADMIN, RECEPTION                |
| Billing New     | `/billing/new`                | ADMIN, RECEPTION                |
| Doctors         | `/doctors`                    | ADMIN                           |
| Doctor Detail   | `/doctors/[id]`               | ADMIN                           |
| Doctor New      | `/doctors/new`                | ADMIN                           |
| Lab             | `/lab`                        | ADMIN, LAB                      |
| Pharmacy        | `/pharmacy`                   | ADMIN, PHARMACIST               |
| Inventory       | `/inventory`                  | ADMIN, PHARMACIST               |
| IPD             | `/ipd`                        | ADMIN, RECEPTION                |
| Reports         | `/reports`                    | ADMIN                           |
| Audit           | `/audit`                      | ADMIN                           |
| Settings        | `/settings`                   | ADMIN                           |
| Token Board     | `/token-board`                | DISPLAY                         |
| Notifications   | `/notifications`              | ADMIN                           |
| Print Invoice   | `/(print)/billing/invoice/[billId]` | All (new tab)            |
| Print Rx        | `/(print)/opd/prescription/[visitId]` | All (new tab)           |

## Route Guard (AppLayout)

The `AppLayout` component enforces:
1. **Authentication**: No token → redirect to `/login`
2. **Authorization**: Wrong role for page → redirect to role's home page
3. **Role Home Pages**:
   - ADMIN → `/dashboard`
   - RECEPTION → `/appointments`
   - DOCTOR → `/opd`
   - LAB → `/lab`
   - PHARMACIST → `/pharmacy`
   - DISPLAY → `/token-board`
4. **DISPLAY role** gets fullscreen layout (no sidebar)

## Key Page Descriptions

### Dashboard (`/dashboard`)
- Today's key metrics: patients, revenue, visits, registrations
- Queue status breakdown (scheduled/checked-in/with-doctor/completed)
- Revenue breakdown with collection rate bar
- Quick action links

### Appointments (`/appointments`)
- Two tab views: **Queue** and **OPD Sessions**
- Queue: Filterable list of today's appointments by status
- Sessions: Chamber assignments with Start/End/Next buttons
- Check-in modal with billing UI
- Prescription upload modal for physical Rx

### OPD (`/opd`)
- Doctor's today queue with token numbers
- "Next" button to advance queue
- "Write Prescription" to start consultation
- My Patients tab (doctor's patient history)

### OPD Consultation (`/opd/[visitId]`)
- Vital signs entry
- Chief complaint, symptoms, clinical notes, diagnosis
- Prescription: digital (typed medicines) or paper upload
- Consumables (N02): select from catalogue, add to visit
- Save & complete marks visit done

### Billing (`/billing`)
- Daily summary stats (billed, collected, pending, collection rate)
- Clickable stat cards → filtered drill-down list
- Date picker for past dates
- Links to "Collect payment" and "Invoice" (print)

### Token Board (`/token-board`)
- Fullscreen display for waiting area TV
- Shows each chamber with doctor name and current token
- Auto-refreshes every 3 seconds
- Triple-click footer to reveal logout button

### Print Pages (`/(print)/`)
- `billing/invoice/[billId]` — Printable invoice
- `opd/prescription/[visitId]` — Printable prescription
- Separate layout with minimal styling for printing
