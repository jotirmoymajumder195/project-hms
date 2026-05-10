# Environment Setup

## Backend

### Prerequisites
- Node.js >= 18
- PostgreSQL (local or RDS)
- Redis (local or ElastiCache)
- AWS account (optional, for S3 uploads)

### Setup

```bash
cd hms-backend

# 1. Install dependencies
npm install

# 2. Copy and edit environment variables
cp .env.example .env
# Edit .env with your values (see below)

# 3. Generate Prisma client and run migrations
npx prisma generate
npx prisma migrate dev --name init

# 4. Seed database
node prisma/seed.js
# Creates: admin@mbshospital.com / Admin@123!

# 5. Start development server
npm run dev
```

### Required .env Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | 64-char random hex string |
| `ENCRYPTION_KEY` | 32-char random hex string |
| `REDIS_URL` | Redis connection string |
| `AWS_ACCESS_KEY_ID` | AWS credentials (for S3) |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `AWS_S3_BUCKET` | S3 bucket name |
| `TWILIO_ACCOUNT_SID` | Twilio credentials |
| `TWILIO_AUTH_TOKEN` | Twilio credentials |
| `TWILIO_PHONE_NUMBER` | Twilio phone number |
| `SMTP_HOST` | SMTP server (e.g., smtp.gmail.com) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASS` | SMTP password/app password |

Generate secrets:
```bash
openssl rand -hex 64   # JWT_SECRET
openssl rand -hex 32   # ENCRYPTION_KEY
```

## Frontend

### Setup

```bash
cd hms-frontend

# 1. Install dependencies
npm install

# 2. Create .env or .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:5000/api/v1" > .env.local

# 3. Start development server
npm run dev
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://13.206.144.153/api/v1` | Backend API URL |

## Running Together

```bash
# Terminal 1 — Backend
cd hms-backend && npm run dev

# Terminal 2 — Frontend
cd hms-frontend && npm run dev
```

Frontend: http://localhost:3000
Backend: http://localhost:5000

## Default Login Credentials

After seeding:
- **Email**: admin@mbshospital.com
- **Password**: Admin@123!
- **Role**: ADMIN

**IMPORTANT**: Change this password immediately after first login.
