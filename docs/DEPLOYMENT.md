# 🚀 DEPLOYMENT.md — Deployment & Operations Guide

> Production deployment and operations guide for the RAQ Chatbot platform, covering Docker orchestration, cloud platforms, and monitoring strategies.

---

## 📑 Table of Contents

- [1. Deployment Options Overview](#1-deployment-options-overview)
- [2. Option 1: Full Docker Compose (Local / VPS)](#2-option-1-full-docker-compose-local--vps)
- [3. Option 2: Hybrid Deployment (Server DB + Managed Platforms)](#3-option-2-hybrid-deployment-server-db--managed-platforms)
- [4. Dockerfile Specifications](#4-dockerfile-specifications)
- [5. Production Configuration](#5-production-configuration)
- [6. Monitoring & Logging](#6-monitoring--logging)
- [7. Backup & Recovery](#7-backup--recovery)
- [8. Troubleshooting](#8-troubleshooting)

---

## 1. Deployment Options Overview

| Option | DB & MinIO | Backend | Frontend | Best For |
|--------|------------|---------|----------|----------|
| **1. All-in-One Docker** | Docker container | Docker container | Docker container | Demos, single VPS, grading |
| **2. Hybrid (Recommended)** | Server/VPS (Docker) | Render / Railway / Cloud Run | Vercel / Netlify | Light production, small teams |

---

## 2. Option 1: Full Docker Compose (Local / VPS)

### 2.1 Requirements

- VPS / Dedicated Server: ≥ 4 vCPUs, ≥ 8 GB RAM, ≥ 20 GB SSD
- Docker ≥ 24.x + Docker Compose V2
- Domain name and SSL certificate (for public deployments)

### 2.2 Step-by-Step Deployment

**Step 1: Clone repository**
```bash
git clone <repository-url>
cd RAQ_CHAT_BOT
```

**Step 2: Configure environment**
```bash
cp backend/.env.example backend/.env
```

Modify `backend/.env`:
```env
# ── Mandatory production changes ────────────────────────
JWT_SECRET_KEY=<random-string-32-chars>
USE_MOCK_LLM=false

# ── API Keys (Required when USE_MOCK_LLM=false) ─────────
SYSTEM_DEFAULT_API_KEY=nvapi-xxxx
SYSTEM_DEFAULT_EMBEDDING_KEY=nvapi-yyyy

# ── Models ──────────────────────────────────────────────
DEFAULT_CHAT_MODEL=deepseek-ai/deepseek-v4-pro-0813
DEFAULT_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b
```

**Step 3: Update docker-compose.yml for production**

Adjust values in `docker-compose.yml`:
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: <strong-password>  # Change from default

  minio:
    environment:
      MINIO_ROOT_USER: <minio-admin-user>
      MINIO_ROOT_PASSWORD: <strong-password>  # Change from default

  backend:
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:<strong-password>@postgres:5432/raq_chatbot
      - MINIO_ACCESS_KEY=<minio-admin-user>
      - MINIO_SECRET_KEY=<strong-password>
      - JWT_SECRET_KEY=<random-string>
      - USE_MOCK_LLM=false
      - FRONTEND_URL=https://your-domain.com

  frontend:
    build:
      args:
        - NEXT_PUBLIC_API_URL=https://api.your-domain.com
    environment:
      - NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

**Step 4: Build and launch**
```bash
docker compose up --build -d
```

**Step 5: Verify status**
```bash
# Check container status
docker compose ps

# Check backend health
curl http://localhost:8000/api/health

# Inspect logs
docker compose logs -f backend
docker compose logs -f frontend
```

### 2.3 Reverse Proxy (Nginx)

When deploying to a VPS with a domain, configure Nginx as a reverse proxy:

```nginx
# /etc/nginx/sites-available/raq-chatbot
server {
    listen 80;
    server_name your-domain.com api.your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 443 ssl;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # SSE streaming configurations
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## 3. Option 2: Hybrid Deployment (Server DB + Managed Platforms)

### 3.1 Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐
│   Vercel     │────▶│  Render /    │────▶│  VPS (Docker)        │
│  (Frontend)  │     │  Railway     │     │  ┌────────────────┐  │
│              │     │  (Backend)   │     │  │  PostgreSQL 16 │  │
│  Next.js 16  │     │  FastAPI     │     │  │  + pgvector    │  │
│  Static +    │     │  Python 3.11 │     │  └────────────────┘  │
│  Edge SSR    │     │              │     │  ┌────────────────┐  │
└──────────────┘     └──────────────┘     │  │  MinIO S3      │  │
                                          │  └────────────────┘  │
                                          └──────────────────────┘
```

### 3.2 Step 1: Deploy DB + MinIO on VPS

**docker-compose.infra.yml** (Infrastructure services only):

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: raq_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: raq_chatbot
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: raq_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
  miniodata:
```

```bash
# On the VPS
docker compose -f docker-compose.infra.yml up -d
```

> ⚠️ **Security**: Configure VPS firewall rules to only allow ingress on ports 5432 and 9000 from the IP ranges of Render / Railway. Do not expose these database ports publicly.

### 3.3 Step 2: Deploy Backend to Render / Railway

**Render Setup:**
1. Connect GitHub repository
2. Root Directory: `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Environment Variables:
```
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<vps-ip>:5432/raq_chatbot
MINIO_ENDPOINT=<vps-ip>:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=<strong-password>
MINIO_BUCKET_NAME=pdf-storage
MINIO_USE_SSL=false
JWT_SECRET_KEY=<random-string>
USE_MOCK_LLM=false
SYSTEM_DEFAULT_API_KEY=nvapi-xxxx
SYSTEM_DEFAULT_EMBEDDING_KEY=nvapi-yyyy
DEFAULT_CHAT_MODEL=deepseek-ai/deepseek-v4-pro-0813
DEFAULT_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b
FRONTEND_URL=https://your-app.vercel.app
```

**Railway Setup:**
1. New Project → Deploy from GitHub
2. Set identical environment variables as Render
3. Railway automatically detects Dockerfile or uses `Procfile`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 3.4 Step 3: Deploy Frontend to Vercel

1. Import project repository from GitHub
2. Framework Preset: Next.js
3. Root Directory: `frontend`
4. Environment Variables:
```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

> **Note**: `NEXT_PUBLIC_API_URL` is a build-time variable in Next.js. Any change requires triggering a project redeploy.

---

## 4. Dockerfile Specifications

### 4.1 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Key Characteristics:**
- Base image: `python:3.11-slim` (lightweight, ~150MB base)
- Layer caching: `requirements.txt` is copied and installed prior to application source code
- Configurable port: Adapts to hosting platform `$PORT` variables

### 4.2 Frontend Dockerfile

```dockerfile
# frontend/Dockerfile — Multi-stage build
# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: Builder
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# Stage 3: Production Runner
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
USER nextjs
EXPOSE 3000
CMD ["npm", "start"]
```

**Key Characteristics:**
- Multi-stage build (deps → builder → runner) yields an optimized production image (~200MB)
- Execution runs under the non-privileged `nextjs` system user
- `NEXT_PUBLIC_API_URL` injected at build-time via Docker build arguments

### 4.3 Docker Ignore Files

**backend/.dockerignore:**
```
venv/
__pycache__/
*.pyc
.env
.git
.pytest_cache
tests/
```

**frontend/.dockerignore:**
```
node_modules/
.next/
.git
.env.local
```

---

## 5. Production Configuration

### 5.1 Security Checklist

| # | Item | Action |
|---|------|--------|
| 1 | JWT Secret | Set `JWT_SECRET_KEY` to a random, unguessable string ≥ 32 characters |
| 2 | Database Password | Replace default `POSTGRES_PASSWORD` with a strong password |
| 3 | MinIO Password | Replace default `MINIO_ROOT_PASSWORD` with a strong password |
| 4 | CORS Whitelist | Only permit actual frontend domains in `FRONTEND_URL` |
| 5 | Mock Mode | Ensure `USE_MOCK_LLM=false` is set in production |
| 6 | SSL / TLS | Enforce HTTPS across all frontend and API endpoints |
| 7 | Firewall | Expose only necessary ingress ports (80, 443) |
| 8 | Secrets Management | Never commit production API keys or credentials to Git |

### 5.2 Scaling Considerations

| Component | Horizontal Scaling | Notes |
|-----------|-------------------|-------|
| Frontend | ✅ Fully Stateless | Scales seamlessly on Vercel or CDN edges |
| Backend | ⚠️ Single-worker recommended | Background `asyncio.create_task` ingestion runs within the local process |
| PostgreSQL | ❌ Single instance | Requires read-replicas for extreme query loads |
| MinIO | ✅ Supported | MinIO offers native distributed cluster mode |

### 5.3 Performance Tuning

**PostgreSQL (pgvector):**
```sql
-- Optimize cosine similarity search for large datasets
CREATE INDEX idx_chunks_embedding ON document_chunks
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Recommended when document_chunks exceeds 10,000 records
```

**Backend Process:**
```bash
# Production: run single worker per container when relying on in-process background tasks
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> ⚠️ **Note**: Since the backend executes ingestion tasks via `asyncio.create_task()`, running multiple workers without an external queue (such as Celery / Redis) can lead to uncoordinated job states.

---

## 6. Monitoring & Logging

### 6.1 Health Check

```bash
# Cron job to verify backend health every 5 minutes
*/5 * * * * curl -sf http://localhost:8000/api/health || echo "Backend DOWN" | mail -s "Alert" admin@example.com
```

### 6.2 Docker Logs

```bash
# Real-time backend logs
docker compose logs -f --tail 100 backend

# Logs for all services across the last hour
docker compose logs --since 1h

# Export logs to file
docker compose logs backend > backend_$(date +%Y%m%d).log
```

### 6.3 Key Metrics to Monitor

| Metric | Verification Method | Warning Threshold |
|--------|---------------------|-------------------|
| API Response Latency | Nginx access logs | > 5s for non-streaming calls |
| Database Connections | `SELECT count(*) FROM pg_stat_activity` | > 80% of `max_connections` |
| MinIO Disk Usage | `docker exec raq_minio du -sh /data` | > 80% disk capacity |
| Ingestion Failure Rate | Query `documents` WHERE status='failed' | > 5% failure rate |
| Memory Consumption | `docker stats` | > 80% container memory limit |

---

## 7. Backup & Recovery

### 7.1 Database Backup

```bash
# Dump PostgreSQL database
docker exec raq_postgres pg_dump -U postgres raq_chatbot > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from SQL dump
cat backup.sql | docker exec -i raq_postgres psql -U postgres raq_chatbot
```

### 7.2 MinIO Storage Backup

```bash
# Using MinIO Client (mc)
mc alias set myraq http://localhost:9000 minioadmin minioadmin
mc mirror myraq/pdf-storage /path/to/backup/pdf-storage/
```

### 7.3 Automated Backup Script

```bash
#!/bin/bash
# backup.sh — Run daily via cron
BACKUP_DIR="/backups/raq/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec raq_postgres pg_dump -U postgres raq_chatbot | gzip > $BACKUP_DIR/db.sql.gz

# Mirror MinIO bucket
mc mirror --overwrite myraq/pdf-storage $BACKUP_DIR/minio/

# Retain backups for 30 days
find /backups/raq/ -maxdepth 1 -mtime +30 -type d -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

```cron
# Crontab: Run at 2:00 AM daily
0 2 * * * /scripts/backup.sh >> /var/log/raq_backup.log 2>&1
```

---

## 8. Troubleshooting

### 8.1 Frequently Encountered Issues

| Issue | Root Cause | Resolution |
|-------|------------|------------|
| `Connection refused` (DB) | PostgreSQL container is still initializing | Wait for healthcheck to pass; inspect `docker compose ps` |
| `CORS error` in frontend | Incorrect `FRONTEND_URL` | Match `FRONTEND_URL` in `backend/.env` with the frontend origin |
| `Upload failed` | MinIO bucket does not exist | Log in to MinIO Console (:9001) and create bucket `pdf-storage` |
| `Embedding error 401` | Missing or invalid API key | Verify `SYSTEM_DEFAULT_API_KEY` or provide BYOK key |
| `429 Resource Exhausted` | LLM provider rate limit exceeded | Wait for the indicated cooldown or provide a personal BYOK key |
| `Document status: failed` | Corrupted PDF or model timeout | Check `ingestion_jobs.error_message` and retry document upload |
| Frontend build error | Missing `NEXT_PUBLIC_API_URL` | Supply `--build-arg NEXT_PUBLIC_API_URL=...` during image build |

### 8.2 Debug Commands

```bash
# Test PostgreSQL connection
docker exec -it raq_postgres psql -U postgres -d raq_chatbot -c "SELECT count(*) FROM users;"

# Inspect MinIO bucket contents
docker exec -it raq_minio mc ls local/pdf-storage/

# Search for backend exceptions
docker compose logs backend 2>&1 | grep "Error"

# Verify container connectivity
docker exec -it raq_backend ping postgres
docker exec -it raq_backend ping minio

# Restart specific service
docker compose restart backend

# Rebuild and restart backend
docker compose up --build -d backend
```

### 8.3 Reset All Data

```bash
# ⚠️ CAUTION: Irreversibly purges all data
docker compose down -v
docker compose up --build -d
```

> The `-v` flag deletes all Docker volumes (PostgreSQL records + MinIO files). Database schemas will re-initialize automatically from `sql/init.sql`.
