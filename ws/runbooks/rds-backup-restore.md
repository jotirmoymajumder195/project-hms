# RDS Backup & Restore Runbook

## Overview

This runbook covers all RDS backup/restore operations for the HMS production PostgreSQL database (`hms-prod` in `ap-south-1`).

| Item | Value |
|------|-------|
| RDS Instance | `hms-prod` |
| Engine | PostgreSQL |
| Region | `ap-south-1` |
| Backend .env file | `hms-backend/.env.prod` |
| PM2 app name | `hms-backend` |
| App directory | `/home/ubuntu/hms-backend` |

---

## 1. Enable 30-Day Automated Backups

**When:** First-time production setup, or after creating a new RDS instance.

```bash
aws rds modify-db-instance \
  --db-instance-identifier hms-prod \
  --backup-retention-period 30 \
  --preferred-backup-window "02:00-03:00" \
  --preferred-maintenance-window "sun:03:00-sun:04:00" \
  --backup-target region \
  --region ap-south-1
```

> ⚠️ Changing `--backup-retention-period` from 0 to 1+ causes an immediate reboot. Setting it from 1 to 30 does **not** reboot — it takes effect immediately.

**Verify:**
```bash
aws rds describe-db-instances \
  --db-instance-identifier hms-prod \
  --region ap-south-1 \
  --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow,EarliestRestorableTime]' \
  --output table
```

Expected output: `BackupRetentionPeriod=30`, `EarliestRestorableTime` populated.

---

## 2. Take Manual Snapshot Before Every Release

**When:** Before every production deployment, **before** running `scripts/deploy.sh`.

**Quick command:**
```bash
cd /home/ubuntu/hms-backend && bash scripts/db-restore.sh snapshot
```

This creates a snapshot named `hms-prod-manual-YYYY-MM-DD-HHMMSS` and waits for completion.

**Manual equivalent:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier hms-prod \
  --db-snapshot-identifier "hms-prod-manual-$(date -u '+%Y-%m-%d-%H%M%S')" \
  --region ap-south-1 \
  --tags Key=Environment,Value=production Key=CreatedBy,Value=pre-deploy

# Wait for completion before proceeding with deploy:
aws rds wait db-snapshot-complete \
  --db-instance-identifier hms-prod \
  --db-snapshot-identifier "hms-prod-manual-$(date -u '+%Y-%m-%d-%H%M%S')" \
  --region ap-south-1
```

**Validate the snapshot:**
```bash
aws rds describe-db-snapshots \
  --db-snapshot-identifier hms-prod-manual-2026-06-05-143000 \
  --region ap-south-1 \
  --query 'DBSnapshots[0].[Status,PercentProgress]' --output table
```

> **Integration with deploy.sh:** Until the deploy script is updated to auto-snapshot, add this step to your pre-deploy checklist manually.

---

## 3. List Available Snapshots & Restorable Times

```bash
# List all manual snapshots (last 20)
cd /home/ubuntu/hms-backend && bash scripts/db-restore.sh list

# Equivalent AWS CLI:
aws rds describe-db-snapshots \
  --db-instance-identifier hms-prod \
  --region ap-south-1 \
  --query "sort_by(DBSnapshots[?Status=='available'],&SnapshotCreateTime) | reverse(@) | [0:20].[DBSnapshotIdentifier,SnapshotCreateTime,SnapshotType]" \
  --output table

# Check PITR window:
aws rds describe-db-instances \
  --db-instance-identifier hms-prod \
  --region ap-south-1 \
  --query 'DBInstances[0].[EarliestRestorableTime,LatestRestorableTime]' \
  --output table
```

---

## 4. Restore RDS (Point-in-Time Recovery)

**Use case:** Data corruption, accidental schema change, or ransomware recovery.

### 4a. Quick restore (recommended — script handles everything)

```bash
# Restore to latest restorable time
cd /home/ubuntu/hms-backend && bash scripts/db-restore.sh restore --latest

# Restore to a specific timestamp (ISO 8601 UTC)
bash scripts/db-restore.sh restore --pitr "2026-06-05T03:00:00Z"

# Restore from a named manual snapshot
bash scripts/db-restore.sh restore --snapshot hms-prod-manual-2026-06-05-020000
```

The script will:
1. Create a new RDS instance named `hms-prod-restored-<timestamp>`
2. Wait for it to become available
3. Auto-update `.env.prod` DATABASE_URL to point at the new endpoint
4. Reload PM2 with `--update-env` to pick up the new connection string
5. Run health checks (up to 12 attempts @ 5s intervals)
6. Report success or failure

### 4b. Manual restore (step by step)

```bash
# Step 1: Create the restored instance
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier hms-prod \
  --target-db-instance-identifier hms-prod-restored-2026-06-05 \
  --restore-time "2026-06-05T03:00:00Z" \
  --region ap-south-1 \
  --db-instance-class db.t3.medium \
  --multi-az true \
  --no-publicly-accessible

# Step 2: Wait (10-30 minutes)
aws rds wait db-instance-available \
  --db-instance-identifier hms-prod-restored-2026-06-05 \
  --region ap-south-1

# Step 3: Get the new endpoint
ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier hms-prod-restored-2026-06-05 \
  --region ap-south-1 \
  --query 'DBInstances[0].Endpoint.Address' --output text)
echo "New endpoint: $ENDPOINT"

# Step 4: Update .env.prod
cd /home/ubuntu/hms-backend
OLD_URL=$(grep -oP 'DATABASE_URL=\K.*' .env.prod)
NEW_URL=$(echo "$OLD_URL" | sed -E "s|@[^:/]+:[0-9]+|@${ENDPOINT}:5432|")
sed -i "s|DATABASE_URL=${OLD_URL}|DATABASE_URL=${NEW_URL}|" .env.prod

# Step 5: Reload PM2
pm2 reload hms-backend --update-env

# Step 6: Health check
sleep 5
curl -s http://localhost:5000/api/v1/health | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('status','UNKNOWN'))"
```

---

## 5. Smoke Test After Restore

After the health check passes, run these smoke tests:

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: hms_prod" \
  -d '{"email":"admin@hospital.com","password":"..."}' | \
  python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")

[ -n "$TOKEN" ] && echo "PASS: Login works" || echo "FAIL: Login broken"

# 2. List patients (verify DB connectivity)
curl -s http://localhost:5000/api/v1/patients \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: hms_prod" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'PASS: {len(d.get(\"data\",[]))} patients found')" \
  || echo "FAIL: Patients endpoint returned error"

# 3. Verify counts match expected
curl -s http://localhost:5000/api/v1/health | python3 -m json.tool

# 4. Test a write operation (create a test appointment, then clean up)
curl -s -X POST http://localhost:5000/api/v1/appointments \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-tenant-id: hms_prod" \
  -H "Content-Type: application/json" \
  -d '{"doctorId":"existing-doctor-id","patientId":"existing-patient-id","date":"2026-06-10","timeSlot":"09:00-09:15"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('PASS: Write works' if d.get('success') else 'WRITE FAILED')"
```

---

## 6. Switching Traffic to a Restored Instance

After a restore, the restored instance becomes primary. The original instance still exists and can be kept as a backup or deleted.

### DNS cutover (if using Route53):
```bash
# If you manage a CNAME record for the DB endpoint:
aws route53 change-resource-record-sets \
  --hosted-zone-id ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "db.hms.example.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "NEW_ENDPOINT"}]
      }
    }]
  }'
```

### Clean up old instance (after confirming restored instance is stable — wait 48h):
```bash
aws rds delete-db-instance \
  --db-instance-identifier hms-prod \
  --region ap-south-1 \
  --skip-final-snapshot \
  --no-delete-automated-backups

# Rename the restored instance to the original name:
aws rds modify-db-instance \
  --db-instance-identifier hms-prod-restored-2026-06-05 \
  --new-db-instance-identifier hms-prod \
  --region ap-south-1 \
  --apply-immediately
```

> ⚠️ Wait 48 hours before deleting the old instance to allow rollback.

---

## 7. Integrate Snapshot into deploy.sh

To make pre-deploy snapshots automatic, add this block after `cd "$APP_DIR"` in `scripts/deploy.sh`:

```bash
# ── Pre-deploy RDS snapshot ──────────────────────────────────────────────
echo "[0/5] Taking manual RDS snapshot before deploy..."
SNAPSHOT_ID="hms-prod-manual-$(date -u '+%Y-%m-%d-%H%M%S')"
aws rds create-db-snapshot \
  --db-instance-identifier hms-prod \
  --db-snapshot-identifier "${SNAPSHOT_ID}" \
  --region ap-south-1 \
  --tags Key=Environment,Value=production Key=CreatedBy,Value=deploy.sh \
  --query 'DBSnapshot.[DBSnapshotIdentifier,Status]' --output text
echo "      Snapshot ${SNAPSHOT_ID} in progress (non-blocking — deploy continues)..."
```

**Do not** wait for snapshot completion inside deploy.sh — that would add 10-30 minutes to every deploy. The snapshot runs in the background. Verify it completed after the deploy finishes:

```bash
aws rds wait db-snapshot-complete \
  --db-instance-identifier hms-prod \
  --db-snapshot-identifier "hms-prod-manual-$(date -u '+%Y-%m-%d-%H%M%S')" \
  --region ap-south-1
```

---

## 8. Disaster Recovery Scenarios

### Scenario A: Database corruption detected (bad data, not schema)

1. Stop the app (optional, to prevent further writes):
   ```bash
   pm2 stop hms-backend
   ```
2. Identify target restore time (before corruption occurred)
3. Run PITR restore:
   ```bash
   bash scripts/db-restore.sh restore --pitr "2026-06-05T02:30:00Z"
   ```
4. The script auto-updates DATABASE_URL and reloads PM2
5. Verify data integrity via smoke tests
6. If the original corruption was due to an application bug, fix and deploy before going live

### Scenario B: Failed destructive migration

1. The rollback script (`scripts/rollback.sh`) warns that destructive migrations need manual DB restore
2. Find the most recent manual snapshot taken before the deploy:
   ```bash
   bash scripts/db-restore.sh list
   ```
3. Restore from that snapshot:
   ```bash
   bash scripts/db-restore.sh restore --snapshot hms-prod-manual-2026-06-05-020000
   ```
4. The new instance has pre-migration schema; roll back app code:
   ```bash
   bash scripts/rollback.sh HEAD~1
   ```

### Scenario C: Entire AWS region failure

RDS automated backups are stored in the same region. Cross-region backup replication is **not configured** (add as future work).

For region-level failures:
1. Wait for AWS to restore the region
2. If the instance is gone, restore from the final snapshot in a different region:
   ```bash
   aws rds copy-db-snapshot \
     --source-db-snapshot-identifier arn:aws:rds:ap-south-1:ACCOUNT:snapshot:hms-prod-manual-2026-06-05 \
     --target-db-snapshot-identifier hms-prod-manual-copy \
     --region ap-southeast-1
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier hms-prod-dr \
     --db-snapshot-identifier hms-prod-manual-copy \
     --region ap-southeast-1
   ```

---

## 9. RTO/RPO Targets

| Metric | Target | Current Status |
|--------|--------|----------------|
| RPO (Recovery Point Objective) | ≤ 5 min | ✅ RDS automated backups (5-min window) |
| RTO (Recovery Time Objective) | ≤ 30 min | ⚠️ Depends on DB size (10-30 min restore time) |

---

## 10. Quarterly Restore Drill

Run this **once per quarter** to verify backup integrity:

1. On a staging/non-production AWS account (or use a different instance name):
   ```bash
   bash scripts/db-restore.sh restore --latest
   # Uses RDS_INSTANCE=hms-staging to avoid touching prod
   ```
2. Run full smoke test suite
3. Verify row counts match expected ranges
4. Tear down the restored instance:
   ```bash
   aws rds delete-db-instance \
     --db-instance-identifier hms-prod-restored-* \
     --skip-final-snapshot \
     --region ap-south-1
   ```
5. Document the drill date and results in `ws/runbooks/restore-drills.log`

---

## 11. Monitoring & Alerting

### CloudWatch alarms (created by `scripts/setup-cloudwatch.sh`):
- `HMS-DB-Connections-High`: > 80% of max_connections for 5 min
- `HMS-DB-ReplicaLag`: > 100 MB (if read replica is added)
- `HMS-5xx-Error-Rate`: > 10% for 5 min

### Manual checks:
```bash
# Check RDS free storage space
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=hms-prod \
  --start-time "$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ')" \
  --end-time "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --period 300 --statistics Average \
  --region ap-south-1 \
  --query 'Datapoints[*].[Timestamp,Average]' --output table
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│                      QUICK REFERENCE                                │
├─────────────────────────────────────────────────────────────────────┤
│ Manual snapshot before deploy:                                      │
│   • bash scripts/db-restore.sh snapshot                             │
│                                                                      │
│ PITR restore:                                                       │
│   • bash scripts/db-restore.sh restore --pitr "2026-06-05T03:00:00Z"│
│                                                                      │
│ List snapshots + PITR window:                                       │
│   • bash scripts/db-restore.sh list                                 │
│                                                                      │
│ Enable 30-day backups:                                              │
│   • aws rds modify-db-instance                                      │
│     --db-instance-identifier hms-prod                               │
│     --backup-retention-period 30                                    │
│     --region ap-south-1                                             │
│                                                                      │
│ Smoke test after restore:                                           │
│   • Curl /api/v1/health for OK status                               │
│   • Login, list patients, create appointment                        │
│                                                                      │
│ App restart after DATABASE_URL change:                              │
│   • pm2 reload hms-backend --update-env                             │
└─────────────────────────────────────────────────────────────────────┘
```
