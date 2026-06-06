# 🔐 Security Actions — Manual Checklist

These actions CANNOT be done in code. They must be done by the system administrator
before the system goes live with a second tenant or in a public environment.

---

## CRITICAL — Do These Before Any Second Tenant Onboards

### 1. Rotate JWT_SECRET

The current JWT_SECRET in `.env` may have been exposed. Rotating it will
invalidate ALL active sessions (all users will be logged out once).

```bash
# Generate a strong new secret (128 hex characters = 512 bits of entropy)
openssl rand -hex 64
```

Update `hms-backend/.env`:
```
JWT_SECRET=<output of above command>
```

Redeploy the backend. All existing JWT tokens become invalid immediately.

---

### 2. Set POSTGRES_PASSWORD (remove "strongpassword")

```bash
# Generate a strong database password
openssl rand -base64 32
```

**Steps:**
1. Stop the postgres container: `docker compose stop postgres`
2. Update `hms-backend/.env` and `.env` (root): `POSTGRES_PASSWORD=<new-password>`
3. Update DATABASE_URL in `.env`: `postgresql://hms_user:<new-password>@postgres:5432/hms_db`
4. Delete the postgres data volume and recreate: `docker compose down -v && docker compose up -d`
   ⚠️ This deletes all data — make a backup first if you have live data
5. Alternatively for live system: connect to running postgres and run:
   ```sql
   ALTER USER hms_user WITH PASSWORD '<new-password>';
   ```
   Then update `.env` and restart backend container only.

---

### 3. Set REDIS_PASSWORD

```bash
openssl rand -hex 24
```

Add to `.env`:
```
REDIS_PASSWORD=<output of above>
```

The `docker-compose.yml` already reads `${REDIS_PASSWORD}` — just add this to `.env`.
Then restart containers: `docker compose restart redis backend`

---

### 4. Rotate ENCRYPTION_KEY (used for Aadhaar encryption)

The ENCRYPTION_KEY is used for AES-256-GCM encryption of Aadhaar numbers.
Rotating it requires re-encrypting all stored Aadhaar fields.

```bash
openssl rand -hex 32
```

**Steps:**
1. Keep the OLD key in a separate variable (e.g. `ENCRYPTION_KEY_OLD=...`)
2. Set `ENCRYPTION_KEY=<new-key>` in `.env`
3. Write and run a one-time migration script:
   ```javascript
   // re-encrypt-aadhaar.js
   const { encrypt, decrypt } = require('./src/utils/encryption');
   // temporarily use old key to decrypt, new key to re-encrypt
   const patients = await prisma.patient.findMany({ where: { aadhaarEncrypted: { not: null } } });
   for (const p of patients) {
     const plain = decryptWithOldKey(p.aadhaarEncrypted);
     const newEncrypted = encrypt(plain); // uses new key from env
     await prisma.patient.update({ where: { id: p.id }, data: { aadhaarEncrypted: newEncrypted } });
   }
   ```
4. Verify a few records decrypt correctly
5. Remove `ENCRYPTION_KEY_OLD` from environment

---

### 5. Check Git History for Committed Secrets

If `.env` was ever committed to git, the secrets are in history even if deleted.

```bash
# Check if .env was ever in git history
cd hms-backend
git log --all --full-history -- .env

# If it appears in history, purge it:
pip install git-filter-repo
git filter-repo --path .env --invert-paths --force

# Then force-push (coordinate with team):
git push origin --force --all
```

---

### 6. Verify .gitignore Is Protecting Secrets

```bash
# These files must NOT be tracked:
git check-ignore -v hms-backend/.env
git check-ignore -v .env

# If either returns nothing, add to .gitignore and remove from tracking:
echo ".env" >> .gitignore
git rm --cached hms-backend/.env
git commit -m "chore: remove .env from tracking"
```

---

## HIGH — Do Before Going Live With Any External Users

### 7. Enable HTTPS on Production Domain

Ensure Nginx (or AWS ALB) terminates SSL and redirects HTTP → HTTPS.
Never run the HMS app over plain HTTP in production.

### 8. Restrict Security Groups (AWS)

- PostgreSQL RDS: port 5432 accessible ONLY from the backend EC2 security group
- Redis: port 6379 accessible ONLY from the backend EC2 security group
- Backend EC2: port 5000 accessible ONLY from Nginx/ALB
- Nginx: ports 80 (redirect) and 443 only, from anywhere
- NO direct public access to database ports

### 9. Enable AWS RDS Automated Backups

```bash
aws rds modify-db-instance \
  --db-instance-identifier hms-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "02:00-03:00" \
  --region ap-south-1
```

Test restore quarterly.

---

## Status Tracker

| Action | Priority | Done |
|--------|----------|------|
| Rotate JWT_SECRET | CRITICAL | ☐ |
| Change POSTGRES_PASSWORD | CRITICAL | ☐ |
| Set REDIS_PASSWORD | CRITICAL | ☐ |
| Rotate ENCRYPTION_KEY | CRITICAL | ☐ |
| Check git history for .env | CRITICAL | ☐ |
| Verify .gitignore | HIGH | ☐ |
| HTTPS on production | HIGH | ☐ |
| AWS Security Groups | HIGH | ☐ |
| RDS Automated Backups | HIGH | ☑ |
