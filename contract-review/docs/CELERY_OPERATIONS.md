# Celery Operations Runbook

Complete guide for operating and troubleshooting the Celery task queue system.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Common Operations](#common-operations)
3. [Monitoring & Metrics](#monitoring--metrics)
4. [Troubleshooting](#troubleshooting)
5. [Emergency Procedures](#emergency-procedures)
6. [Performance Tuning](#performance-tuning)
7. [Deployment Guide](#deployment-guide)

---

## Architecture Overview

### Components

```
┌──────────────────────────────────────────────────────┐
│                   Contract Upload                     │
│                         ↓                             │
│              FastAPI Endpoint                         │
│                         ↓                             │
│         process_contract_task.delay()                 │
│                         ↓                             │
│                   Redis Queue                         │
│           (default | urgent | batch)                  │
│                         ↓                             │
│            Celery Worker Pool (3 workers)             │
│                         ↓                             │
│              contract_processor.py                    │
│         (Claude API + Database Updates)               │
└──────────────────────────────────────────────────────┘
```

### Queue Priorities

| Queue | Use Case | Priority | Rate Limit |
|-------|----------|----------|------------|
| `urgent` | Manual re-analysis | High | N/A |
| `default` | Normal uploads | Medium | 10/min |
| `batch` | Bulk uploads | Low | N/A |

### Worker Configuration

- **Concurrency:** 3 workers per service instance
- **Prefetch:** 1 task per worker (prevents hogging)
- **Task Timeout:** 10 min soft, 15 min hard
- **Worker Restart:** After 100 tasks (memory leak prevention)
- **Retry Policy:** 3 attempts with exponential backoff (60s → 120s → 240s)

---

## Common Operations

### View Active Tasks

```bash
# Via Celery CLI
celery -A celery_app inspect active

# Via Flower (browser)
# Open: http://localhost:5555 or https://flower.railway.app
```

### Purge Queue (Clear All Pending)

```bash
celery -A celery_app purge

# ⚠️ WARNING: This deletes ALL pending tasks!
# Use with caution in production
```

### Revoke Specific Task

```bash
# Soft revoke (task won't start if pending)
celery -A celery_app control revoke <task-id>

# Hard revoke (terminate if already running)
celery -A celery_app control revoke <task-id> --terminate
```

### Check Queue Depth

**Via Python:**
```python
from celery_app import celery_app

inspect = celery_app.control.inspect()
active = inspect.active()
reserved = inspect.reserved()

print(f"Active tasks: {sum(len(tasks) for tasks in active.values())}")
print(f"Reserved tasks: {sum(len(tasks) for tasks in reserved.values())}")
```

**Via Redis CLI:**
```bash
redis-cli LLEN celery  # Default queue length
```

### Scale Workers

**Railway Dashboard:**
1. Go to Worker service
2. Settings → Replicas
3. Adjust count (recommended: 3-5)

**Railway CLI:**
```bash
railway service scale worker --replicas 5
```

**Local Development:**
```bash
# Stop current worker (Ctrl+C)
# Start with new concurrency
celery -A celery_app worker --concurrency=5 --loglevel=info
```

### View Worker Stats

```bash
celery -A celery_app inspect stats
```

Returns:
```json
{
  "worker@hostname": {
    "total": {"tasks.contract_tasks.process_contract_task": 42},
    "rusage": {"maxrss": 256000},
    "pool": {"max-concurrency": 3}
  }
}
```

---

## Monitoring & Metrics

### Flower Dashboard

Access: `http://localhost:5555` (dev) or `https://flower.railway.app` (prod)

**Key Metrics:**
- **Success Rate:** Target > 95%
- **Avg Processing Time:** Target < 45 seconds
- **Queue Depth:** Alert if > 50
- **Worker Failures:** Alert if > 5/hour

**Screenshots:**
- Tasks tab: See all task history
- Workers tab: Monitor worker health
- Monitor tab: Real-time graphs

### Health Check Endpoint

```bash
curl https://your-api.railway.app/health/celery
```

**Healthy Response:**
```json
{
  "status": "healthy",
  "redis": "connected",
  "workers": 3,
  "queues": ["default", "urgent", "batch"]
}
```

**Degraded Response (no workers):**
```json
{
  "status": "degraded",
  "redis": "connected",
  "workers": 0
}
```

**Unhealthy Response:**
```json
{
  "status": "unhealthy",
  "redis": "disconnected",
  "error": "Connection refused"
}
```

### Admin Stats Endpoint

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://your-api.railway.app/api/admin/celery/stats
```

Returns:
```json
{
  "success": true,
  "stats": {
    "workers": 3,
    "active_tasks": 2,
    "reserved_tasks": 5,
    "scheduled_tasks": 0,
    "worker_details": {
      "worker1@hostname": [
        {"id": "task-abc-123", "name": "process_contract_task"}
      ]
    }
  }
}
```

### Logging

**Worker Logs (Railway):**
```bash
railway logs --service worker
```

**Look for:**
- ✅ `Starting task: tasks.contract_tasks.process_contract_task [ID: ...]`
- ✅ `Completed task: tasks.contract_tasks.process_contract_task [ID: ...]`
- ⚠️ `Retrying contract processing: <doc_id> (attempt 2/3)`
- ❌ `Contract processing FAILED permanently: <doc_id>`

### Recommended Alerts

Set up alerts for:
- Queue depth > 50 (backlog building up)
- Worker count = 0 (all workers crashed)
- Task failure rate > 10%
- Avg task time > 120 seconds
- Redis connection errors

---

## Troubleshooting

### Issue: Tasks Not Processing

**Symptoms:**
- Contracts stuck in "processing" status
- Queue depth increasing
- No activity in Flower

**Diagnosis:**
```bash
# 1. Check Redis
redis-cli ping  # Should return "PONG"

# 2. Check workers
celery -A celery_app inspect active  # Should show workers

# 3. Check logs
railway logs --service worker | grep ERROR
```

**Solutions:**
- **Redis down:** Restart Redis service in Railway
- **No workers:** Restart worker service
- **Workers hung:** Revoke stuck tasks and restart workers
- **Environment variable missing:** Check `REDIS_URL` is set

---

### Issue: High Task Failure Rate

**Symptoms:**
- Many contracts with `error: ...` status
- Flower shows high failure %

**Diagnosis:**
```bash
# View failed task details in Flower
# Check specific error messages in documents table
SELECT processing_status FROM documents WHERE processing_status LIKE 'error:%';
```

**Common Causes:**
- **Claude API rate limits:** Wait, or increase `CELERY_CLAUDE_API_RATE_LIMIT`
- **Timeout errors:** Increase `CELERY_TASK_SOFT_TIME_LIMIT`
- **Memory errors:** Reduce `CELERY_WORKER_CONCURRENCY`
- **Database connection:** Check Supabase status

---

### Issue: Slow Processing

**Symptoms:**
- Avg task time > 60 seconds
- Queue building up

**Diagnosis:**
```bash
# Check queue depth
celery -A celery_app inspect reserved

# Check worker resource usage
railway logs --service worker | grep "memory"
```

**Solutions:**
- **High queue depth:** Scale workers (`railway service scale worker --replicas 5`)
- **Claude API slow:** Check Anthropic status page
- **Memory pressure:** Reduce `CELERY_MAX_TASKS_PER_CHILD` to force more restarts
- **Database slow:** Check Supabase performance metrics

---

### Issue: Workers Crashing

**Symptoms:**
- Worker count drops to 0
- Railway shows "crashed" status
- Restarts frequently

**Diagnosis:**
```bash
railway logs --service worker | tail -100
```

**Common Causes:**

**OOM (Out of Memory):**
```
Exit code: 137  # Killed by OOM
```
**Solution:** Reduce concurrency or upgrade Railway plan

**Unhandled Exception:**
```
Traceback (most recent call last):
  ...
```
**Solution:** Fix code bug, deploy update

**Connection Lost:**
```
ConnectionError: Redis connection lost
```
**Solution:** Check Redis service health

---

### Issue: Redis Connection Errors

**Symptoms:**
- Health check shows "redis: disconnected"
- Workers can't connect

**Diagnosis:**
```bash
# Check Redis status
railway status --service redis

# Test connection locally
redis-cli -h <redis-host> -p <redis-port> -a <password> ping
```

**Solutions:**
- **Railway Redis down:** Restart service
- **Wrong `REDIS_URL`:** Verify environment variable
- **Network issue:** Check Railway status page

---

## Emergency Procedures

### System Overload

**Situation:** Too many uploads, system slowing down

**Steps:**
1. **Stop new uploads** (optional):
   ```bash
   # Set feature flag
   railway variables set USE_CELERY=false
   # Falls back to BackgroundTasks (not ideal but works)
   ```

2. **Increase worker capacity:**
   ```bash
   railway service scale worker --replicas 10
   ```

3. **Purge low-priority tasks:**
   ```bash
   # Only if absolutely necessary
   celery -A celery_app control revoke --queue batch
   ```

4. **Monitor recovery:**
   - Watch Flower for queue depth decreasing
   - Check `/health/celery` for worker count

---

### All Workers Dead

**Situation:** No workers running, contracts piling up

**Steps:**
1. **Check Railway service:**
   ```bash
   railway status --service worker
   ```

2. **View crash logs:**
   ```bash
   railway logs --service worker | tail -200
   ```

3. **Restart service:**
   ```bash
   railway service restart worker
   ```

4. **If restart fails:**
   - Check for deployment errors
   - Verify all environment variables set
   - Check Redis is running

---

### Data Loss Prevention

**Situation:** Need to prevent task loss during maintenance

**Steps:**
1. **Stop accepting new tasks:**
   ```bash
   # Pause uploads (set maintenance mode in app)
   ```

2. **Wait for queue to drain:**
   ```bash
   watch "celery -A celery_app inspect reserved | grep -c task"
   # Wait until count reaches 0
   ```

3. **Perform maintenance**

4. **Resume:**
   ```bash
   # Re-enable uploads
   ```

---

## Performance Tuning

### Optimize for Throughput

**Goal:** Process more contracts per hour

**Config changes in `celery_app.py`:**
```python
worker_prefetch_multiplier = 4  # Workers prefetch 4 tasks
task_annotations = {
    'tasks.contract_tasks.process_contract_task': {
        'rate_limit': '20/m'  # Increase from 10/m (if Claude API allows)
    }
}
```

**Scale workers:**
```bash
railway service scale worker --replicas 5
```

**Expected Impact:** 2-3x throughput increase

---

### Optimize for Memory

**Goal:** Reduce memory usage and prevent crashes

**Config changes:**
```python
worker_max_tasks_per_child = 50  # Restart more frequently
worker_prefetch_multiplier = 1  # Only prefetch 1 task
task_time_limit = 600  # Reduce from 900 (10 min instead of 15)
```

**Expected Impact:** 30-40% memory reduction

---

### Optimize for Latency

**Goal:** Faster contract processing

**Config changes:**
```python
worker_prefetch_multiplier = 2  # Anticipate next task
task_acks_late = False  # Acknowledge immediately (riskier)
```

**Scale workers:**
```bash
railway service scale worker --replicas 5
```

**Expected Impact:** 20-30% faster processing

---

## Deployment Guide

### First-Time Setup

**1. Add Redis to Railway:**
```bash
# In Railway dashboard:
# Click "+ New Service" → "Redis" → Deploy
```

**2. Link Redis to Backend:**
```bash
# Railway automatically sets REDIS_URL
# Verify:
railway variables list | grep REDIS_URL
```

**3. Deploy Backend with Celery:**
```bash
git push railway main
# Backend now includes Celery code (but USE_CELERY=false by default)
```

**4. Create Worker Service:**
```bash
# In Railway dashboard:
# Click "+ New Service" → "GitHub Repo" → Select same repo
# Settings:
#   - Root Directory: backend
#   - Build Command: pip install -r requirements.txt
#   - Start Command: celery -A celery_app worker --loglevel=info --concurrency=3 -Q default,urgent,batch
```

**5. Enable Celery:**
```bash
railway variables set USE_CELERY=true
```

**6. Verify:**
```bash
curl https://your-api.railway.app/health/celery
# Should show workers: 3
```

---

### Zero-Downtime Deployment

**Steps:**

1. **Deploy new code with Celery disabled:**
   ```bash
   railway variables set USE_CELERY=false
   git push railway main
   ```

2. **Deploy workers:**
   ```bash
   # Workers start (queue is empty since Celery disabled)
   railway service restart worker
   ```

3. **Verify workers healthy:**
   ```bash
   curl https://your-api.railway.app/health/celery
   ```

4. **Enable Celery (gradual rollout):**
   ```python
   # In contracts.py, add canary:
   import random
   use_celery = random.random() < 0.1  # 10% of uploads
   ```

5. **Monitor for 24 hours**

6. **Full rollout:**
   ```bash
   railway variables set USE_CELERY=true
   ```

---

### Rollback Plan

**If issues occur:**

```bash
# Immediately disable Celery
railway variables set USE_CELERY=false

# System reverts to BackgroundTasks
# Existing queue will drain naturally
```

---

## Best Practices

1. **Always monitor Flower** during high-traffic periods
2. **Set up alerts** for queue depth > 50
3. **Test deployments** in staging first
4. **Keep worker count odd** (3, 5, 7) for better load distribution
5. **Review failed tasks** daily in Flower
6. **Update Celery/Redis** regularly for security patches
7. **Document any config changes** in this file

---

## Support Contacts

- **Celery Issues:** https://github.com/celery/celery/issues
- **Railway Support:** https://railway.app/help
- **Redis Issues:** https://github.com/redis/redis/issues

---

**Last Updated:** 2025-01-06
**Version:** 1.0
**Author:** Charlie Fuller
