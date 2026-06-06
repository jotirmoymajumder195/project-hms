# HMS — Architecture Overview

## Project Structure

```
hms-backend/                    # Node.js + Express API server
  src/
    server.js                   # Entry point — mounts all middleware & routes
    config/
      index.js                  # Central env config (JWT, AWS, Redis, etc.)
      redis.js                  # Redis connection client
    middleware/
      auth.js                   # JWT authentication + role authorization
      errorHandler.js           # Global error handler
    modules/
      auth/                     # Staff login, register, password management
      patient/                  # Patient CRUD, DPDPA consent, data requests
      doctor/                   # Doctor profiles, schedules, available slots
      appointment/              # Booking, walk-in, check-in, queue management
      opd/                      # OPD visits, prescriptions, upload
      billing/                  # Bills, payments, daily summary
      lab/                      # Lab tests & orders (stub — full build pending)
      pharmacy/                 # Pharmacy & medicine dispensing (stub)
      inventory/                # General inventory management (stub)
      ipd/                      # In-patient admissions & beds (stub)
      reports/                  # Dashboard, OPD, revenue, doctor reports
      notifications/            # SMS/WhatsApp/Email notifications (stub)
      audit/                    # Audit log search & filtering
      consumables/              # Consumables catalogue & visit usage
      opd-chambers/             # OPD rooms, assignments, session management
    utils/
      logger.js                 # Winston structured logger
      errors.js                 # AppError custom class
      encryption.js             # AES-256-GCM encrypt/decrypt for Aadhaar
      idGenerators.js           # UHID, bill number, admission number, etc.
      auditHelper.js            # Audit log helper
  prisma/
    schema.prisma               # Database schema (PostgreSQL, 30+ models)
    seed.js                     # Seeds admin user, hospital settings, wards

hms-frontend/                   # Next.js 14 (App Router) + TypeScript
  src/
    app/
      layout.tsx                # Root layout — AuthProvider, fonts, Toaster
      page.tsx                  # Root → redirects to /dashboard
      globals.css               # Tailwind + component classes
      login/                    # Login page + first-login password change
      dashboard/                # Admin/doctor/reception dashboard
      appointments/             # Queue view, OPD sessions, walk-in, booking
      opd/                      # OPD queue, consultation page
      patients/                 # Patient search, registration, details
      doctors/                  # Doctor profiles & schedules
      billing/                  # Daily summary, bill generation, invoices
      lab/                      # Lab orders (placeholder)
      pharmacy/                 # Pharmacy dispense (placeholder)
      inventory/                # Inventory management (placeholder)
      ipd/                      # In-patient management (placeholder)
      reports/                  # Admin reports & analytics
      notifications/            # Notifications (placeholder)
      settings/                 # Admin settings
      audit/                    # Audit log viewer
      token-board/              # Fullscreen TV token board display
      (print)/                  # Printable invoices & prescriptions
    components/
      layout/
        AppLayout.tsx           # Auth guard + sidebar + role-based routing
        Sidebar.tsx             # Navigation sidebar with role filtering
        CheckInModal.tsx        # Modal for check-in billing UI
      CheckInModal.tsx          # Duplicate? Check usage
    lib/
      api.ts                    # Axios client + all API endpoint functions
      auth-context.tsx          # Auth state, login/logout, role helpers
```

## Technology Stack

| Layer          | Technology                              |
|----------------|-----------------------------------------|
| Frontend       | Next.js 14, React 18, TypeScript        |
| Styling        | Tailwind CSS + custom design tokens     |
| API Client     | Axios, TanStack React Query (installed) |
| Backend        | Node.js, Express 4, JavaScript          |
| Database       | PostgreSQL via Prisma ORM               |
| Cache          | Redis (session, queue, rate limiting)   |
| Auth           | JWT (jsonwebtoken, bcryptjs)            |
| File Storage   | AWS S3 (via multer-s3, @aws-sdk/client-s3) |
| SMS            | Twilio                                  |
| Email          | Nodemailer (SMTP)                       |
| Logging        | Winston + daily rotate file             |
| Validation     | express-validator, Joi (installed)      |
| Encryption     | AES-256-GCM (for Aadhaar fields)        |

## Data Flow

```
Browser (Next.js) ←→ Axios ←→ Express API (:5000) ←→ Prisma ←→ PostgreSQL
                                              ←→ Redis
                                              ←→ AWS S3 (uploads)
                                              ←→ Twilio (SMS)
                                              ←→ SMTP (email)
```

- Frontend runs on port 3000, backend on port 5000
- API base path: `/api/v1`
- JWT token stored in cookie (`hms_token`) — auto-attached to all requests
- 401 responses auto-redirect to `/login`
- DISPLAY role gets a 1-year token (never expires on the TV board)
