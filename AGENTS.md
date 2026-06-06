# HMS Project Context

## Project Structure
- **Frontend**: `hms-frontend/` — Next.js 14, port 3000
- **Backend**: `hms-backend/` — Express.js, port 5000 (API base: `/api/v1`)
- **Workspace**: `ws/` — docs, backlogs
- **Prisma schema**: `hms-backend/prisma/schema.prisma`

## Running the App
```bash
# Backend (port 5000)
cd hms-backend && npm run dev

# Frontend (port 3000)
cd hms-frontend && npm run dev
```

## Multi-Tenant Architecture
- Every request requires `x-tenant-id` header or JWT with tenant context
- `authenticate` middleware sets `req.user.tenantId` — always use this when creating records
- Patient, ConsentLog, and all other resources require `tenantId`

## Known Fixes
- Patient registration was missing `tenantId: req.user.tenantId` — fixed in `patient.routes.js:72`
- ConsentLog creation also needed `tenantId` — fixed in `patient.routes.js:85`

## IPD Module Status
- Schema fully designed & migrated (Module 11 in schema.prisma, ~line 954)
- Backend routes stub at `hms-backend/src/modules/ipd/ipd.routes.js` — needs full implementation
- IPD routes registered at `/api/v1/ipd` in `server.js:169`
- Frontend pages not yet built
- Spec: `ws/Project Backlogs/ipd-module-document.md`
