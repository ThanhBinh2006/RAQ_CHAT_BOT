# 🚀 DEPLOYMENT.md — Hướng dẫn Triển khai & Vận hành

> Tài liệu hướng dẫn triển khai RAQ Chatbot lên môi trường production, bao gồm Docker, cloud platforms và các chiến lược giám sát.

---

## 📑 Mục lục

- [1. Tổng quan các phương án triển khai](#1-tổng-quan-các-phương-án-triển-khai)
- [2. Phương án 1: Docker Compose toàn bộ (local/VPS)](#2-phương-án-1-docker-compose-toàn-bộ-localvps)
- [3. Phương án 2: DB + MinIO trên server, FE + BE trên nền tảng](#3-phương-án-2-db--minio-trên-server-fe--be-trên-nền-tảng)
- [4. Chi tiết Dockerfile](#4-chi-tiết-dockerfile)
- [5. Cấu hình Production](#5-cấu-hình-production)
- [6. Giám sát & Logging](#6-giám-sát--logging)
- [7. Backup & Recovery](#7-backup--recovery)
- [8. Troubleshooting](#8-troubleshooting)

---

## 1. Tổng quan các phương án triển khai

| Phương án | DB & MinIO | Backend | Frontend | Phù hợp |
|----------|-----------|---------|----------|---------|
| **1. All-in-One Docker** | Docker container | Docker container | Docker container | Demo, VPS đơn, chấm điểm |
| **2. Hybrid (khuyến nghị)** | Server/VPS (Docker) | Render / Railway / Cloud Run | Vercel / Netlify | Production nhẹ, team nhỏ |

---

## 2. Phương án 1: Docker Compose toàn bộ (local/VPS)

### 2.1 Yêu cầu

- VPS/Server: ≥ 4 vCPU, ≥ 8 GB RAM, ≥ 20 GB SSD
- Docker ≥ 24.x + Docker Compose V2
- Domain + SSL (nếu public)

### 2.2 Các bước triển khai

**Bước 1: Clone repository**
```bash
git clone <repository-url>
cd RAQ_CHAT_BOT
```

**Bước 2: Cấu hình environment**
```bash
cp backend/.env.example backend/.env
```

Sửa `backend/.env`:
```env
# ── Bắt buộc đổi cho production ─────────────────────────
JWT_SECRET_KEY=<random-string-32-chars>
USE_MOCK_LLM=false

# ── API Keys (bắt buộc khi USE_MOCK_LLM=false) ────────
SYSTEM_DEFAULT_API_KEY=nvapi-xxxx
SYSTEM_DEFAULT_EMBEDDING_KEY=nvapi-yyyy

# ── Models ──────────────────────────────────────────────
DEFAULT_CHAT_MODEL=deepseek-ai/deepseek-v4-pro-0813
DEFAULT_EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b
```

**Bước 3: Cập nhật docker-compose.yml (production)**

Sửa các giá trị trong `docker-compose.yml`:
```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: <strong-password>  # Đổi khỏi "postgres"

  minio:
    environment:
      MINIO_ROOT_USER: <minio-admin-user>
      MINIO_ROOT_PASSWORD: <strong-password>  # Đổi khỏi "minioadmin"

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

**Bước 4: Build và chạy**
```bash
docker compose up --build -d
```

**Bước 5: Verify**
```bash
# Kiểm tra tất cả services
docker compose ps

# Kiểm tra health
curl http://localhost:8000/api/health

# Xem logs
docker compose logs -f backend
docker compose logs -f frontend
```

### 2.3 Reverse Proxy (Nginx)

Nếu deploy trên VPS với domain, thêm Nginx reverse proxy:

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

        # SSE streaming support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## 3. Phương án 2: DB + MinIO trên server, FE + BE trên nền tảng

### 3.1 Kiến trúc

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

### 3.2 Bước 1: Deploy DB + MinIO trên VPS

**docker-compose.infra.yml** (chỉ DB + MinIO):

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
# Trên VPS
docker compose -f docker-compose.infra.yml up -d
```

> ⚠️ **Bảo mật**: Cấu hình firewall chỉ mở port 5432 và 9000 cho IP của Render/Railway. Không mở public.

### 3.3 Bước 2: Deploy Backend lên Render/Railway

**Render:**
1. Connect GitHub repo
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

**Railway:**
1. New Project → Deploy from GitHub
2. Cùng environment variables như Render
3. Railway auto-detect Dockerfile hoặc dùng `Procfile`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### 3.4 Bước 3: Deploy Frontend lên Vercel

1. Import project từ GitHub
2. Framework Preset: Next.js
3. Root Directory: `frontend`
4. Environment Variables:
```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

> **Lưu ý**: `NEXT_PUBLIC_API_URL` là build-time variable trong Next.js. Phải rebuild khi thay đổi.

---

## 4. Chi tiết Dockerfile

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

**Đặc điểm:**
- Base image: `python:3.11-slim` (nhẹ, ~150MB)
- Layer caching: `requirements.txt` copy riêng trước source code
- PORT configurable qua env (phù hợp Render/Railway)

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

**Đặc điểm:**
- 3-stage build: deps → build → production (~200MB final image)
- Non-root user `nextjs` (bảo mật)
- `NEXT_PUBLIC_API_URL` inject lúc build (ARG → ENV)

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

## 5. Cấu hình Production

### 5.1 Checklist bảo mật

| # | Hạng mục | Hành động |
|---|---------|-----------|
| 1 | JWT Secret | Đổi `JWT_SECRET_KEY` sang chuỗi random ≥ 32 ký tự |
| 2 | DB Password | Đổi `POSTGRES_PASSWORD` sang mật khẩu mạnh |
| 3 | MinIO Password | Đổi `MINIO_ROOT_PASSWORD` sang mật khẩu mạnh |
| 4 | CORS | Chỉ cho phép domain frontend thực tế trong `FRONTEND_URL` |
| 5 | Mock Mode | Set `USE_MOCK_LLM=false` (production) |
| 6 | SSL/TLS | Cấu hình HTTPS cho tất cả endpoints |
| 7 | Firewall | Chỉ mở ports cần thiết (80, 443) |
| 8 | API Keys | Không commit API keys vào Git |

### 5.2 Scaling

| Component | Horizontal Scale | Lưu ý |
|-----------|-----------------|--------|
| Frontend | ✅ Stateless | Scale freely trên Vercel/CDN |
| Backend | ⚠️ Cẩn thận | `asyncio.create_task` cho ingestion chỉ hoạt động trong cùng process |
| PostgreSQL | ❌ Single instance | Cần read replicas cho scale lớn |
| MinIO | ✅ Cluster mode | MinIO hỗ trợ distributed mode |

### 5.3 Performance Tuning

**PostgreSQL:**
```sql
-- Tối ưu cho pgvector search
CREATE INDEX idx_chunks_embedding ON document_chunks
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Chỉ tạo khi có > 10,000 chunks
```

**Backend:**
```bash
# Production: dùng multiple workers (cẩn thận với background tasks)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> ⚠️ **Lưu ý**: Vì backend sử dụng `asyncio.create_task()` cho ingestion, nên **không nên dùng nhiều workers** trừ khi chuyển sang task queue (Celery/Redis).

---

## 6. Giám sát & Logging

### 6.1 Health Check

```bash
# Cron job kiểm tra health mỗi 5 phút
*/5 * * * * curl -sf http://localhost:8000/api/health || echo "Backend DOWN" | mail -s "Alert" admin@example.com
```

### 6.2 Docker Logs

```bash
# Xem logs real-time
docker compose logs -f --tail 100 backend

# Xem logs của tất cả services
docker compose logs --since 1h

# Export logs
docker compose logs backend > backend_$(date +%Y%m%d).log
```

### 6.3 Key Metrics để theo dõi

| Metric | Cách kiểm tra | Ngưỡng cảnh báo |
|--------|--------------|-----------------|
| API response time | Nginx access log | > 5s cho non-streaming |
| DB connections | `SELECT count(*) FROM pg_stat_activity` | > 80% max_connections |
| Disk usage (MinIO) | `docker exec raq_minio du -sh /data` | > 80% disk |
| Ingestion failure rate | Check `documents` WHERE status='failed' | > 5% |
| Memory usage | `docker stats` | > 80% container limit |

---

## 7. Backup & Recovery

### 7.1 Database Backup

```bash
# Backup PostgreSQL
docker exec raq_postgres pg_dump -U postgres raq_chatbot > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
cat backup.sql | docker exec -i raq_postgres psql -U postgres raq_chatbot
```

### 7.2 MinIO Backup

```bash
# Sử dụng mc (MinIO Client)
mc alias set myraq http://localhost:9000 minioadmin minioadmin
mc mirror myraq/pdf-storage /path/to/backup/pdf-storage/
```

### 7.3 Automated Backup Script

```bash
#!/bin/bash
# backup.sh — Chạy hàng ngày qua cron
BACKUP_DIR="/backups/raq/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# DB backup
docker exec raq_postgres pg_dump -U postgres raq_chatbot | gzip > $BACKUP_DIR/db.sql.gz

# MinIO backup
mc mirror --overwrite myraq/pdf-storage $BACKUP_DIR/minio/

# Retain 30 days
find /backups/raq/ -maxdepth 1 -mtime +30 -type d -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

```cron
# Cron: 2:00 AM daily
0 2 * * * /scripts/backup.sh >> /var/log/raq_backup.log 2>&1
```

---

## 8. Troubleshooting

### 8.1 Các lỗi thường gặp

| Lỗi | Nguyên nhân | Giải pháp |
|-----|------------|-----------|
| `Connection refused` (DB) | PostgreSQL chưa ready | Đợi healthcheck pass, kiểm tra `docker compose ps` |
| `CORS error` trên frontend | `FRONTEND_URL` sai | Kiểm tra biến `FRONTEND_URL` trong backend .env |
| `Upload failed` | MinIO chưa tạo bucket | Truy cập MinIO Console (9001) tạo bucket `pdf-storage` |
| `Embedding error 401` | API key sai/hết hạn | Kiểm tra `SYSTEM_DEFAULT_API_KEY` |
| `429 Resource Exhausted` | Rate limit LLM | Đợi theo thời gian hệ thống báo, hoặc dùng BYOK key |
| `Document status: failed` | PDF corrupt hoặc embedding lỗi | Xem `ingestion_jobs.error_message`, re-upload |
| Frontend build lỗi | `NEXT_PUBLIC_API_URL` không set | Set ARG lúc build: `--build-arg NEXT_PUBLIC_API_URL=...` |

### 8.2 Debug Commands

```bash
# Kiểm tra database connection
docker exec -it raq_postgres psql -U postgres -d raq_chatbot -c "SELECT count(*) FROM users;"

# Kiểm tra MinIO
docker exec -it raq_minio mc ls local/pdf-storage/

# Kiểm tra backend logs chi tiết
docker compose logs backend 2>&1 | grep "Error"

# Kiểm tra network giữa containers
docker exec -it raq_backend ping postgres
docker exec -it raq_backend ping minio

# Restart một service cụ thể
docker compose restart backend

# Rebuild và restart
docker compose up --build -d backend
```

### 8.3 Reset toàn bộ dữ liệu

```bash
# ⚠️ CẢNH BÁO: Xóa toàn bộ dữ liệu
docker compose down -v
docker compose up --build -d
```

> Lệnh `-v` xóa tất cả Docker volumes (PostgreSQL data + MinIO files). Schema sẽ tự tạo lại từ `sql/init.sql`.
