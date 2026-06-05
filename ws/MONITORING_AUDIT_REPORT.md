# Metrics Monitoring Audit

**Date:** 2026-06-05
**Auditor:** Senior DevOps Engineer
**Scope:** Winston logging, CloudWatch integration, PM2 configuration, metrics collection, alerting

---

## Status Summary

| Component | Status |
|-----------|--------|
| Metrics Collection | ⚠️ Partially Configured |
| Winston Logging | ✅ Configured |
| PM2 Integration | ⚠️ Partially Configured |
| CloudWatch Integration | ❌ Missing |
| Alerting Configuration | ❌ Missing |

---

## Findings

### A. Metrics Collection ⚠️ Partially Configured

**File:** `hms-backend/src/middleware/metrics.js`

| Aspect | Status | Details |
|--------|--------|---------|
| Request counts | ✅ Working | Collected in `_window` array (`metrics.js:25`) |
| Error counts (5xx) | ✅ Working | `_window.filter(r => r.status >= 500).length` (`metrics.js:50`) |
| 60-second rolling window | ✅ Working | Entries pruned lazily on each request via `splice` (`metrics.js:39-41`) |
| p95 latency | ✅ Working | `durations[Math.floor(durations.length * 0.95)]` (`metrics.js:102`) |
| p99 latency | ✅ Working | `durations[Math.floor(durations.length * 0.99)]` (`metrics.js:103`) |
| Health metrics endpoint | ✅ Working | `GET /api/v1/health/metrics` — ADMIN only (`server.js:202-204`) |
| Memory usage | ❌ Missing | No `process.memoryUsage()` anywhere |
| CPU usage | ❌ Missing | No `os` module or `process.cpuUsage()` anywhere |
| Per-endpoint breakdown | ⚠️ Partial | Status code breakdown by 2xx/4xx/5xx buckets, but no per-route granularity |

**How it works:**

Every request passes through `metricsMiddleware` (`server.js:159`). On response `finish`, the middleware:
1. Records `{ time, status, duration, path, method }` to `_window` array
2. Prunes entries older than 60s (`metrics.js:39-41`)
3. Logs warnings for slow requests (>2s)
4. Logs error-level alerts if error rate >10%
5. All data is **in-memory only** — lost on process restart

```js
// metrics.js:30-45 — core collection logic
res.on('finish', () => {
  const duration = Date.now() - startMs;
  const now = Date.now();
  const status = res.statusCode;
  _window.push({ time: now, status, duration, path: req.path, method: req.method });

  let i = 0;
  while (i < _window.length && _window[i].time < now - WINDOW_MS) i++;
  if (i > 0) _window.splice(0, i);
  // ...
});
```

**Gap:** No process-level metrics (memory, CPU, event loop lag, garbage collection). No persistent metric store — all data is lost if the process restarts.

---

### B. Winston Logging ✅ Configured

**File:** `hms-backend/src/utils/logger.js`

```js
const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');

const logger = winston.createLogger({
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    // Console — DEV only
    ...(process.env.NODE_ENV !== 'production'
      ? [new winston.transports.Console({ format: winston.format.simple() })]
      : []),
    // Rotating file — errors
    new DailyRotateFile({
      filename: 'logs/error-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      level: 'error',
      maxFiles: '30d',
    }),
    // Rotating file — all levels
    new DailyRotateFile({
      filename: 'logs/combined-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      maxFiles: '30d',
    }),
  ],
});
```

**Key observations:**

- ✅ JSON structured logging with timestamp
- ✅ Log rotation: daily, 30-day retention
- ✅ Error-level logs separated to `error-%DATE%.log`
- ✅ Stack traces captured via `winston.format.errors({ stack: true })`
- ⚠️ **Console transport disabled in production** — no stdout/stderr output. This means PM2's `out_file` and `error_file` will NOT capture Winston logs. Only the `logs/` directory files contain production logs.
- ❌ **No CloudWatch transport** — logs only go to local filesystem
- ❌ **No log shipping** — no mechanism to get logs off the EC2 instance

**Sample alert log messages (from code):**

```js
// metrics.js:45 — slow request
logger.warn('Slow request', { method: req.method, path: req.path, duration, status });

// metrics.js:71 — elevated error rate
logger.warn('Elevated 5xx error rate', { errorRate: '7.3%', errors: 11, total: 150 });

// metrics.js:55 — critical alert
logger.error('ALERT: High 5xx error rate', { errorRate: '15.2%', errors: 23, total: 151, window: '60s' });
```

**Where `logger.warn` and `logger.error` are triggered:**

| File | Line | Condition | Level |
|------|------|-----------|-------|
| `src/middleware/metrics.js` | 45 | Request duration > 2s | `warn` |
| `src/middleware/metrics.js` | 55 | Error rate >= 10% | `error` |
| `src/middleware/metrics.js` | 71 | Error rate >= 5% | `warn` |
| `src/utils/alerter.js` | 27 | Webhook returns non-2xx | `warn` |
| `src/utils/alerter.js` | 32 | Webhook request fails | `warn` |
| `src/utils/alerter.js` | 36 | Webhook URL invalid | `warn` |

---

### C. PM2 Integration ⚠️ Partially Configured

**File:** `hms-backend/ecosystem.config.js`

```js
module.exports = {
  apps: [
    {
      name: 'hms-backend',
      script: 'src/server.js',
      instances: 'max',
      exec_mode: 'cluster',
      max_memory_restart: '500M',
      restart_delay: 1000,
      listen_timeout: 10000,
      kill_timeout: 5000,
      env: { NODE_ENV: 'development' },
      env_production: { NODE_ENV: 'production' },
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: 'logs/pm2-error.log',
      out_file: 'logs/pm2-out.log',
      merge_logs: true,
    },
  ],
};
```

**Key observations:**

| Aspect | Status | Details |
|--------|--------|---------|
| Cluster mode | ✅ | `instances: 'max'` — one worker per CPU |
| Zero-downtime reload | ✅ | `listen_timeout: 10000` — new workers start before old ones die |
| Graceful shutdown | ✅ | `kill_timeout: 5000` — 5s for in-flight requests |
| Memory restart | ✅ | `max_memory_restart: '500M'` — auto-restart on OOM |
| PM2 log files | ✅ | `logs/pm2-error.log`, `logs/pm2-out.log` |
| Log rotation | ⚠️ | `pm2-logrotate` plugin mentioned but no config file found |
| Deploy script | ✅ | `scripts/deploy.sh` — full zero-downtime CI/CD pipeline |

**Deploy script** (`scripts/deploy.sh`) does:
```
1. git pull
2. npm ci --omit=dev
3. npx prisma migrate deploy
4. pm2 reload hms-backend --update-env
5. curl health check → fail if not OK
```

**Gap:** PM2 log files are on the local EC2 filesystem. There is no mechanism to ship PM2 logs to CloudWatch or any centralized log aggregator. If the EC2 instance is terminated, all logs are lost.

---

### D. CloudWatch Integration ❌ Missing

**Verdict: NOT CONFIGURED**

After exhaustive search of the entire repository, there is **zero CloudWatch configuration**:

| Item | Status | Evidence |
|------|--------|----------|
| CloudWatch Agent config | ❌ | No `amazon-cloudwatch-agent.json` or `cloudwatch-config.json` anywhere |
| `winston-cloudwatch` transport | ❌ | Not in `package.json`, not imported anywhere |
| `@aws-sdk/client-cloudwatch` | ❌ | Not in `package.json` (only `@aws-sdk/client-s3` exists) |
| CloudWatch Log Group names | ❌ | None defined |
| CloudWatch Metric Filters | ❌ | None configured |
| CloudWatch Alarms | ❌ | None configured |
| SNS Topics | ❌ | No SNS references in code |
| IAM permissions for CloudWatch | ❌ | Not documented |
| Terraform/CloudFormation | ❌ | No IaC files exist |
| Log shipping from PM2 | ❌ | PM2 outputs only to local filesystem |

**The only references to CloudWatch are in documentation as planned/future items:**

- `hms-backend/README.md:208` — `7. **CloudWatch** — Monitor logs and alerts`
- `ws/Project Backlogs/project-backlog.md:335` — `- [ ] **CloudWatch / Datadog**: server metrics (CPU, memory, disk, request rate)`
- `ws/PRODUCTION_READINESS_REVIEW.md:442` — `- No request rate, error rate, or latency percentiles`

**Consequence:** Winston logs, PM2 logs, and application metrics stay on the EC2 instance's local disk. There is no log aggregation, no centralized monitoring, no way to alert on infrastructure or application health outside the EC2 instance.

---

### E. Alerting Configuration ❌ Missing

**Verdict: Only in-process logging — NO external alerting**

| Item | Status | Details |
|------|--------|---------|
| In-process log alerts | ✅ | `logger.warn` / `logger.error` in `metrics.js` |
| Webhook alerter | ⚠️ Implemented but **NOT wired** | `alerter.js` exists but `ALERT_WEBHOOK_URL` env var is NOT set in any `.env` file |
| CloudWatch Metric Filters → Alarms | ❌ | Not configured |
| CloudWatch Alarms → SNS | ❌ | Not configured |
| Email notifications | ❌ | Not configured |
| Slack/Teams/PagerDuty | ❌ | Not configured |
| SNS topics | ❌ | Not created or referenced |

**The alerting pipeline currently:**
```
Request → metricsMiddleware → logger.warn/error → local file on EC2
```

**Theoretical pipeline if ALERT_WEBHOOK_URL were set:**
```
Request → metricsMiddleware → alerter.js → HTTP POST → Slack/Teams
```
But `ALERT_WEBHOOK_URL` is absent from `.env`, `.env.prod`, and `.env.example`.

The webhook alerter (`src/utils/alerter.js`) supports Slack-compatible webhooks with:
- Rate-limited (5 min cooldown to prevent alert storms)
- Error vs Warning severity
- JSON payload with color-coded attachments
- 5-second HTTP timeout
- Silent failure on errors (logs warning only)

---

## Evidence

### Files examined

| File | Purpose |
|------|---------|
| `hms-backend/src/utils/logger.js` | Winston logger configuration |
| `hms-backend/src/middleware/metrics.js` | Metrics collection and threshold alerting |
| `hms-backend/src/utils/alerter.js` | Webhook-based external alerting |
| `hms-backend/src/server.js` | Middleware registration, health/metrics endpoints |
| `hms-backend/ecosystem.config.js` | PM2 cluster configuration |
| `hms-backend/scripts/deploy.sh` | Zero-downtime deploy script |
| `hms-backend/.env` | Local environment variables |
| `hms-backend/.env.prod` | Production environment variables |
| `hms-backend/.env.example` | Environment variable template |
| `hms-backend/README.md` | Project documentation |
| `ws/Project Backlogs/project-backlog.md` | Backlog with planned monitoring items |
| `hms-backend/package.json` | Dependencies (no CloudWatch packages) |

### Key code snippets

**Metrics middleware registration:**
```js
// server.js:158-159
// In-process request metrics — tracks error rates and response times
app.use(metricsMiddleware);
```

**Health metrics endpoint:**
```js
// server.js:200-204
app.get('/api/v1/health/metrics', _authM, _authZ(_ROLES.ADMIN, _ROLES.SUPER_ADMIN), (_req, res) => {
  res.json({ success: true, ...getMetrics() });
});
```

**Rolling window implementation:**
```js
// metrics.js:24-25, 39-41
const _window = [];  // module-scoped array, survives between requests
// ...
let i = 0;
while (i < _window.length && _window[i].time < now - WINDOW_MS) i++;
if (i > 0) _window.splice(0, i);
```

**p95/p99 calculation:**
```js
// metrics.js:100-103
const durations = samples.map(r => r.duration).sort((a, b) => a - b);
const p95 = durations[Math.floor(durations.length * 0.95)] ?? durations[durations.length - 1];
const p99 = durations[Math.floor(durations.length * 0.99)] ?? durations[durations.length - 1];
```

---

## Production Readiness Score

| Category | Score | Rationale |
|----------|-------|-----------|
| **Metrics Collection** | 5/10 | Request rate, error rate, p95/p99 latency all collected. Missing memory, CPU, per-route breakdown, persistent store. |
| **PM2 Logging** | 6/10 | Cluster mode, zero-downtime reload, auto-restart, log rotation configured. Logs are local-only, no shipping mechanism. |
| **CloudWatch Logging** | 0/10 | Zero CloudWatch configuration. No agent, no log groups, no IAM, no transport. |
| **Alerting** | 2/10 | In-process threshold detection works. Only output is local log files. Webhook exists but is not wired (env var missing). No SNS, no email, no PagerDuty. |
| **Observability** | 2/10 | Metrics are in-memory (lost on restart). No dashboards. No centralized log aggregation. No tracing. No external visibility into system health. |

**Overall Observability Score: 3/10**

---

## Gaps

### Critical (blocks production incident detection)
1. **No CloudWatch Agent** — Winston logs stay on EC2 local disk. If the instance is terminated or the disk fills up, logs are lost permanently.
2. **No CloudWatch Alarms** — There are zero metric filters or alarms. High error rates are logged to a file but nobody gets notified.
3. **No external alerting** — `ALERT_WEBHOOK_URL` is not set in any `.env` file. The webhook alerter exists but is dead code.
4. **No SNS topics** — Even if CloudWatch Alarms were added, there's no notification channel configured.

### High (reduces operational visibility)
5. **No process metrics** — Memory usage, CPU usage, event loop lag, and garbage collection are not tracked.
6. **No metric persistence** — The rolling window is in-memory. A process restart wipes all metrics.
7. **No dashboard** — No Grafana, CloudWatch Dashboard, or any visualization of system health.
8. **Console transport disabled in production** — PM2's `out_file`/`error_file` will not capture Winston logs because the console transport is gated by `NODE_ENV !== 'production'`.

### Medium
9. **No log shipping** — No mechanism (fluentd, logstash, CloudWatch agent) to ship logs off-instance.
10. **No per-route metrics** — Status code breakdown is by 2xx/4xx/5xx buckets, not by individual route.
11. **`winston-daily-rotate-file` retention** — 30-day retention is set but there's no alert when disk usage approaches capacity.

---

## Recommended Next Actions

### Phase 1 — Immediate (1-2 days, $0-10/mo)

1. **Set ALERT_WEBHOOK_URL in production**
   - Create a Slack webhook or similar
   - Add `ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...` to `.env.prod`
   - Restart the app — alerts begin flowing immediately
   - **Cost:** $0 (if using Slack free tier)

2. **Add process metrics to the metrics endpoint**
   ```js
   // In getMetrics(), add:
   const mem = process.memoryUsage();
   return {
     ...currentMetrics,
     memory: {
       rss: Math.round(mem.rss / 1024 / 1024) + 'MB',
       heapTotal: Math.round(mem.heapTotal / 1024 / 1024) + 'MB',
       heapUsed: Math.round(mem.heapUsed / 1024 / 1024) + 'MB',
     },
     cpu: process.cpuUsage(),
     uptime: process.uptime(),
   };
   ```
   - **Cost:** $0

3. **Enable console transport in production**
   - Remove the `NODE_ENV !== 'production'` gate on the Console transport, or add a separate transport for PM2
   - This allows PM2's `out_file`/`error_file` to capture application logs
   - **Cost:** $0

### Phase 2 — CloudWatch Setup (3-5 days, ~$5-20/mo)

4. **Install and configure CloudWatch Agent on EC2**
   - Create `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`
   - Configure it to tail `logs/combined-*.log` and `logs/error-*.log`
   - Configure it to collect system metrics (CPU, memory, disk, network)
   - **Cost:** $0 for the agent (standard EC2 monitoring pricing ~$3.50/instance/month)

5. **Create CloudWatch Log Groups**
   - `/hms/backend/combined`
   - `/hms/backend/error`
   - `/hms/pm2`
   - Set retention to 90 days
   - **Cost:** ~$2-5/month for log ingestion

6. **Add `winston-cloudwatch` transport** (alternative to CloudWatch Agent)
   ```js
   // In logger.js, add:
   new CloudWatchTransport({
     logGroupName: '/hms/backend',
     logStreamName: `backend-${require('os').hostname()}`,
     jsonMessage: true,
   })
   ```
   - Requires `npm install winston-cloudwatch`
   - Requires IAM role with `logs:PutLogEvents`, `logs:CreateLogStream`, `logs:CreateLogGroup`
   - **Cost:** Same as CloudWatch Agent approach

### Phase 3 — Alerting Pipeline (3-5 days)

7. **Create CloudWatch Metric Filters**
   - Filter on `"ALERT: High 5xx error rate"` → publish to metric `HMS/5xxErrorRate`
   - Filter on `"Slow request"` → publish to metric `HMS/SlowRequestCount`
   - Filter on `status >= 500` count → publish to metric `HMS/5xxCount`

8. **Create CloudWatch Alarms**
   - `HMS-5xxRate-High` — error rate > 10% for 2 consecutive minutes → SNS
   - `HMS-5xxRate-Elevated` — error rate > 5% for 5 minutes → SNS
   - `HMS-SlowRequests` — > 10 slow requests per minute → SNS
   - `HMS-HealthCheck` — health endpoint returns non-200 → SNS

9. **Create SNS Topics**
   - `hms-alerts-critical` — PagerDuty or Slack (immediate response)
   - `hms-alerts-warning` — Email to on-call engineer

### Phase 4 — Observability Platform (1-2 weeks)

10. **Add structured logging with correlation IDs**
    - Generate a `requestId` per request
    - Include it in every log message and downstream API call
    - Enables tracing across the stack

11. **Set up Grafana or CloudWatch Dashboard**
    - Request rate (rps), error rate (%), p95/p99 latency (ms)
    - System metrics (CPU, memory, disk)
    - Active users / concurrent sessions
    - Cost: CloudWatch Dashboards are free; Grafana on EC2 ~$10/mo

12. **Replace in-memory metrics with persistent store**
    - Option A: Export to CloudWatch Metrics API (`putMetricData`)
    - Option B: Export to Prometheus endpoint (`/metrics` in Prometheus format) and scrape with Prometheus
    - This eliminates data loss on process restart
