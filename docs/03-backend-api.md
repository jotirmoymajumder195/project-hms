# Backend API Reference

All routes prefixed with `/api/v1`.

## Auth (`/auth`)

| Method | Endpoint                        | Auth     | Roles   | Description                              |
|--------|----------------------------------|----------|---------|------------------------------------------|
| POST   | `/auth/login`                    | No       | —       | Staff login, returns JWT token           |
| POST   | `/auth/force-change-password`    | JWT      | All     | First-login password change (S01)        |
| POST   | `/auth/register`                 | JWT      | ADMIN   | Create new staff/doctor account          |
| GET    | `/auth/users`                    | JWT      | ADMIN   | List all staff accounts                  |
| PATCH  | `/auth/users/:id`                | JWT      | ADMIN   | Update staff details                     |
| PATCH  | `/auth/users/:id/toggle-active`  | JWT      | ADMIN   | Activate/deactivate staff                |
| GET    | `/auth/me`                       | JWT      | All     | Current user profile                     |
| POST   | `/auth/change-password`          | JWT      | All     | Change own password                      |
| POST   | `/auth/logout`                   | JWT      | All     | Logout (audit logged)                    |
| POST   | `/auth/admin/reset-password`     | JWT      | ADMIN   | Reset another staff's password           |

**Security**: Login rate-limited per-email (3 attempts → 15 min block). Passwords hashed with bcrypt cost 12.

## Patients (`/patients`)

| Method | Endpoint                          | Auth | Roles            | Description                      |
|--------|-----------------------------------|------|------------------|----------------------------------|
| POST   | `/patients`                       | JWT  | ADMIN, RECEPTION | Register new patient             |
| GET    | `/patients`                       | JWT  | All staff        | Search/list patients             |
| GET    | `/patients/my-patients`           | JWT  | DOCTOR           | Doctor's own patients            |
| GET    | `/patients/:id`                   | JWT  | All staff        | Full patient profile             |
| PATCH  | `/patients/:id`                   | JWT  | ADMIN, RECEPTION | Update patient                   |
| POST   | `/patients/:id/data-request`      | JWT  | ADMIN, RECEPTION | DPDPA data export/deletion req   |

**DPDPA**: Aadhaar encrypted (AES-256-GCM). Consent logged on registration. Cross-patient access flagged in audit for doctors.

## Doctors (`/doctors`)

| Method | Endpoint                             | Auth | Roles  | Description                     |
|--------|--------------------------------------|------|--------|---------------------------------|
| POST   | `/doctors`                           | JWT  | ADMIN  | Create doctor profile           |
| GET    | `/doctors`                           | JWT  | All    | List doctors (filterable)       |
| GET    | `/doctors/:id`                       | JWT  | All    | Single doctor profile           |
| PATCH  | `/doctors/:id`                       | JWT  | All    | Update doctor profile           |
| PATCH  | `/doctors/:id/toggle-status`         | JWT  | ADMIN  | Activate/deactivate             |
| POST   | `/doctors/:id/schedules`             | JWT  | ADMIN  | Set weekly schedule             |
| GET    | `/doctors/:id/available-slots`       | JWT  | All    | Available slots for a date      |
| GET    | `/doctors/:id/patients`              | JWT  | All    | Patients seen by doctor         |

**Schedule**: Clash detection prevents overlapping times. Type filter (OPD/EMERGENCY/IPD) supported.

## Appointments (`/appointments`)

| Method | Endpoint                               | Auth | Roles                    | Description                        |
|--------|----------------------------------------|------|--------------------------|------------------------------------|
| POST   | `/appointments`                        | JWT  | ADMIN, RECEPTION         | Book scheduled appointment         |
| POST   | `/appointments/walk-in`                | JWT  | ADMIN, RECEPTION         | Walk-in + check-in in one call     |
| GET    | `/appointments`                        | JWT  | All staff                | List appointments (filtered)       |
| GET    | `/appointments/today`                  | JWT  | All staff                | Today's queue                      |
| PATCH  | `/appointments/:id/status`             | JWT  | ADMIN, RECEPTION, DOCTOR | Update status (no CHECKED_IN here) |
| PATCH  | `/appointments/:id/cancel`             | JWT  | ADMIN, RECEPTION         | Cancel appointment                 |
| POST   | `/appointments/:id/check-in`           | JWT  | ADMIN, RECEPTION         | Check-in (creates visit + bill)    |
| GET    | `/appointments/available-slots-today/:doctorId` | JWT | All staff        | Walk-in slots today                |
| GET    | `/appointments/token-board/:doctorId`  | No   | Public                  | Token board per doctor             |
| GET    | `/appointments/token-board`            | No   | Public                  | Token board all chambers           |
| POST   | `/appointments/doctor/next`            | JWT  | DOCTOR, RECEPTION, ADMIN | Advance to next patient in queue   |
| POST   | `/appointments/doctor/start-session`   | JWT  | ADMIN, RECEPTION         | Start doctor's session             |
| POST   | `/appointments/doctor/end-session`     | JWT  | ADMIN, RECEPTION         | End doctor's session               |

**Queue Logic**: Sequential token traversal with skip handling. CHECKED_IN only set via check-in endpoint. End-session auto-marks remaining patients as NO_SHOW.

## OPD (`/opd`)

| Method | Endpoint                                      | Auth | Roles                    | Description                    |
|--------|-----------------------------------------------|------|--------------------------|--------------------------------|
| POST   | `/opd/visits`                                 | JWT  | ADMIN, RECEPTION, DOCTOR | Start/update OPD visit         |
| GET    | `/opd/visits/:id`                             | JWT  | All                      | Full visit details             |
| GET    | `/opd/visits/by-appointment/:appointmentId`   | JWT  | All                      | Visit by appointment ID        |
| PATCH  | `/opd/visits/:id`                             | JWT  | ADMIN, DOCTOR            | Update visit (diagnosis, etc.) |
| POST   | `/opd/visits/:id/prescription`                | JWT  | ADMIN, DOCTOR            | Write prescription             |
| POST   | `/opd/visits/:id/prescription-upload`         | JWT  | ADMIN, RECEPTION, DOCTOR | Upload paper prescription      |
| GET    | `/opd/patient/:patientId/history`             | JWT  | All                      | Patient consultation history   |

## Billing (`/billing`)

| Method | Endpoint                        | Auth | Roles            | Description                  |
|--------|---------------------------------|------|------------------|------------------------------|
| POST   | `/billing/bills`                | JWT  | ADMIN, RECEPTION | Generate bill                |
| GET    | `/billing/bills/:id`            | JWT  | All              | Full bill details            |
| GET    | `/billing/patient/:patientId`   | JWT  | All              | Patient billing history      |
| POST   | `/billing/bills/:id/payment`    | JWT  | ADMIN, RECEPTION | Record payment               |
| GET    | `/billing/summary`              | JWT  | ADMIN, RECEPTION | Daily revenue summary        |

## OPD Chambers (`/opd-chambers`)

| Method | Endpoint                             | Auth | Roles            | Description                        |
|--------|--------------------------------------|------|------------------|------------------------------------|
| GET    | `/opd-chambers`                      | JWT  | All              | List chambers                      |
| POST   | `/opd-chambers`                      | JWT  | ADMIN            | Create chamber                     |
| PATCH  | `/opd-chambers/:id`                  | JWT  | ADMIN            | Update chamber                     |
| DELETE | `/opd-chambers/:id`                  | JWT  | ADMIN            | Deactivate chamber                 |
| GET    | `/opd-chambers/assignments`          | JWT  | All              | Chamber assignments for a date     |
| POST   | `/opd-chambers/assignments`          | JWT  | ADMIN            | Assign doctor to chamber           |
| DELETE | `/opd-chambers/assignments/:id`      | JWT  | ADMIN            | Remove assignment                  |
| POST   | `/opd-chambers/start-session`        | JWT  | ADMIN, RECEPTION | Start doctor session in chamber    |
| POST   | `/opd-chambers/end-session`          | JWT  | ADMIN, RECEPTION | End doctor session                 |

## Consumables (`/consumables`)

| Method | Endpoint                               | Auth | Roles            | Description                     |
|--------|----------------------------------------|------|------------------|----------------------------------|
| GET    | `/consumables`                         | JWT  | All              | List consumables                 |
| POST   | `/consumables`                         | JWT  | ADMIN            | Add consumable to catalogue      |
| PATCH  | `/consumables/:id`                     | JWT  | ADMIN            | Update consumable                |
| POST   | `/consumables/visits/:visitId/add`     | JWT  | ADMIN, DOCTOR    | Add consumable to visit (N02)   |
| GET    | `/consumables/visits/:visitId`         | JWT  | All              | Visit consumables                |
| DELETE | `/consumables/visits/:visitId/:usageId`| JWT  | ADMIN, DOCTOR    | Remove consumable from visit     |

## Reports (`/reports`)

| Method | Endpoint              | Auth | Roles  | Description                 |
|--------|-----------------------|------|--------|-----------------------------|
| GET    | `/reports/dashboard`  | JWT  | ADMIN  | Today's ops snapshot        |
| GET    | `/reports/opd`        | JWT  | ADMIN  | OPD footfall (date range)   |
| GET    | `/reports/revenue`    | JWT  | ADMIN  | Revenue report              |
| GET    | `/reports/doctors`    | JWT  | ADMIN  | Doctor performance          |
| GET    | `/reports/patients`   | JWT  | ADMIN  | Patient registration report |

## Audit (`/audit`)

| Method | Endpoint | Auth | Roles  | Description                |
|--------|----------|------|--------|----------------------------|
| GET    | `/audit` | JWT  | ADMIN  | Searchable audit log       |

## Stub Modules

The following modules have placeholder routes returning empty data:
- `/lab` — Lab test ordering & results
- `/pharmacy` — Medicine dispensing
- `/inventory` — Stock management
- `/ipd` — In-patient admissions
- `/notifications` — SMS/Email/WhatsApp

## Health

| Method | Endpoint           | Auth | Description         |
|--------|--------------------|------|---------------------|
| GET    | `/health`          | No   | Server health check |
| GET    | `/api/v1/health`   | No   | API health check    |
