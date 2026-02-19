# Deployment Guide — AML SAR System

> **Covers:** Docker Compose (recommended), Manual VPS, and Windows local production.
> **Prerequisites:** Machine with 8+ GB RAM and a GPU (recommended for Ollama).

---

## Table of Contents

1. [Quick Reference — What You're Deploying](#1-quick-reference)
2. [Option A — Docker Compose (Recommended)](#2-option-a--docker-compose)
3. [Option B — Manual VPS / Linux Server](#3-option-b--manual-vps--linux-server)
4. [Option C — Windows Local Production](#4-option-c--windows-local-production)
5. [Seed the Database](#5-seed-the-database)
6. [Verify Deployment](#6-verify-deployment)
7. [Production Hardening](#7-production-hardening)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Quick Reference

| Component | Port | Tech |
|-----------|------|------|
| **Frontend** | 3000 (dev) / 80 (prod) | React 19, served by Nginx |
| **Backend** | 8000 | FastAPI + Uvicorn |
| **Database** | 5432 | PostgreSQL 16 + pgvector |
| **LLM Engine** | 11434 | Ollama (Mistral 7B + nomic-embed-text) |

### Required Environment Variables

```env
DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/aml_system
OLLAMA_URL=http://localhost:11434
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

## 2. Option A — Docker Compose

This is the easiest way — one command brings up everything.

### Step 1: Create Dockerfiles

Create these files in your project root (`aml-system/`):

#### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps for WeasyPrint (PDF export)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libcairo2 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `frontend/aml-ui/Dockerfile`

```dockerfile
# --- Build stage ---
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# --- Production stage ---
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

# Nginx config for React Router (SPA)
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Step 2: Create `docker-compose.yml`

Create this in `aml-system/`:

```yaml
version: "3.9"

services:
  # ─── PostgreSQL + pgvector ────────────────────────
  db:
    image: pgvector/pgvector:pg16
    container_name: aml-db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
      POSTGRES_DB: aml_system
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ─── Ollama (LLM Engine) ──────────────────────────
  ollama:
    image: ollama/ollama:latest
    container_name: aml-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # If you have an NVIDIA GPU, uncomment below:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  # ─── Backend (FastAPI) ────────────────────────────
  backend:
    build: ./backend
    container_name: aml-backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres123@db:5432/aml_system
      OLLAMA_URL: http://ollama:11434
      SECRET_KEY: change-this-to-a-random-64-char-string
      ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 1440
    depends_on:
      db:
        condition: service_healthy
      ollama:
        condition: service_started
    restart: unless-stopped

  # ─── Frontend (React → Nginx) ─────────────────────
  frontend:
    build: ./frontend/aml-ui
    container_name: aml-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  pgdata:
  ollama_data:
```

### Step 3: Update Frontend API Base URL

Before building, update `frontend/aml-ui/src/services/api.js`:

```js
// For Docker deployment, use relative URL or your server IP
const API_BASE = 'http://localhost:8000';
// If deploying to a remote server, change to:
// const API_BASE = 'http://YOUR_SERVER_IP:8000';
```

### Step 4: Build and Run

```bash
cd aml-system

# Build and start all services
docker compose up -d --build

# Wait ~30 seconds for everything to start, then pull Ollama models
docker exec -it aml-ollama ollama pull mistral:7b-instruct-q4_K_M
docker exec -it aml-ollama ollama pull nomic-embed-text

# Seed the database with test data
docker exec -it aml-backend python generate_data.py
```

### Step 5: Verify

```bash
# Check all containers are running
docker compose ps

# Check backend health
curl http://localhost:8000/health

# Check Ollama models
curl http://localhost:11434/api/tags
```

Open `http://localhost` in your browser → Login → Analyze.

### Useful Docker Commands

```bash
# View backend logs (you'll see the pipeline logging)
docker compose logs -f backend

# Restart just the backend
docker compose restart backend

# Stop everything
docker compose down

# Stop and delete all data (fresh start)
docker compose down -v
```

---

## 3. Option B — Manual VPS / Linux Server

For Ubuntu 22.04+ or Debian 12+.

### Step 1: Install System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PostgreSQL 16 + pgvector
sudo apt install -y postgresql-16 postgresql-16-pgvector

# Install WeasyPrint dependencies (PDF export)
sudo apt install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libcairo2 libffi-dev pkg-config

# Install Nginx (for serving frontend)
sudo apt install -y nginx

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Set Up PostgreSQL

```bash
sudo -u postgres psql <<EOF
CREATE USER aml_user WITH PASSWORD 'your_strong_password';
CREATE DATABASE aml_system OWNER aml_user;
\c aml_system
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

### Step 3: Pull Ollama Models

```bash
# Start Ollama service
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull models (~4.5 GB total)
ollama pull mistral:7b-instruct-q4_K_M
ollama pull nomic-embed-text
```

### Step 4: Deploy Backend

```bash
# Clone/copy your project to the server
cd /opt
sudo mkdir aml-system && sudo chown $USER:$USER aml-system
# Copy your project files here (scp, git clone, etc.)

# Set up Python environment
cd /opt/aml-system/backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env <<EOF
DATABASE_URL=postgresql://aml_user:your_strong_password@localhost:5432/aml_system
OLLAMA_URL=http://localhost:11434
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EOF

# Seed the database
python generate_data.py

# Test run (check for errors)
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+C after you see "Application startup complete"
```

### Step 5: Create Backend Systemd Service

```bash
sudo cat > /etc/systemd/system/aml-backend.service <<EOF
[Unit]
Description=AML SAR Backend
After=network.target postgresql.service ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/aml-system/backend
Environment=PATH=/opt/aml-system/backend/venv/bin:/usr/bin
EnvironmentFile=/opt/aml-system/backend/.env
ExecStart=/opt/aml-system/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable aml-backend
sudo systemctl start aml-backend

# Check status
sudo systemctl status aml-backend
```

### Step 6: Build and Deploy Frontend

```bash
cd /opt/aml-system/frontend/aml-ui

# Update API base URL to your server IP
# Edit src/services/api.js → change API_BASE to 'http://YOUR_SERVER_IP:8000'

npm ci
npm run build

# Copy build to Nginx
sudo cp -r build/* /var/www/html/
```

### Step 7: Configure Nginx

```bash
sudo cat > /etc/nginx/sites-available/aml <<EOF
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    # Frontend (React SPA)
    root /var/www/html;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;  # Pipeline takes 2-3 min
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/aml /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

> **Note:** If you use the Nginx proxy (`/api/`), update `api.js` to use
> `const API_BASE = '/api'` so all API calls go through Nginx.

### Step 8: (Optional) Add HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 4. Option C — Windows Local Production

You're already running this locally. To make it more "production-like":

### Step 1: Keep Services Running

Instead of running in terminal, create batch files:

#### `start-backend.bat`
```batch
@echo off
cd /d D:\barclays\aml-system\backend
call venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### `start-frontend.bat`
```batch
@echo off
cd /d D:\barclays\aml-system\frontend\aml-ui
set PORT=3000
npm start
```

#### `start-all.bat`
```batch
@echo off
echo Starting AML SAR System...
start "AML Backend" cmd /k "D:\barclays\aml-system\start-backend.bat"
timeout /t 5
start "AML Frontend" cmd /k "D:\barclays\aml-system\start-frontend.bat"
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
```

### Step 2: Build frontend for production (optional)

```bash
cd D:\barclays\aml-system\frontend\aml-ui
npm run build
# Outputs to build/ folder — serve with any static server
npx serve -s build -l 3000
```

---

## 5. Seed the Database

After deployment, seed test data:

```bash
# Docker
docker exec -it aml-backend python generate_data.py

# Manual/Windows
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python generate_data.py
```

Then register a user:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@barclays.com", "password": "test123"}'
```

---

## 6. Verify Deployment

Run these checks after deployment:

```bash
# 1. Backend health
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 2. Ollama models
curl http://localhost:11434/api/tags
# Expected: 2 models (mistral, nomic-embed-text)

# 3. Database connection
curl http://localhost:8000/test-db
# Expected: {"status":"Database connected"}

# 4. Login test
curl -X POST http://localhost:8000/auth/login \
  -d "username=analyst@barclays.com&password=test123" \
  -H "Content-Type: application/x-www-form-urlencoded"
# Expected: {"access_token":"...","token_type":"bearer"}

# 5. Customer list (use token from step 4)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/customers
# Expected: JSON array of 10 customers

# 6. Frontend
# Open http://localhost (Docker/Nginx) or http://localhost:3000 (dev)
# Login → Dashboard → Enter Customer ID 11 → Analyze
# Should take 2-3 minutes, then shows SAR with typology + quality score
```

---

## 7. Production Hardening

### Security Checklist

| Item | Action |
|------|--------|
| **SECRET_KEY** | Generate a random 64-char key: `python -c "import secrets; print(secrets.token_hex(32))"` |
| **Database Password** | Change from `postgres123` to a strong password |
| **CORS Origins** | In `main.py`, change `allow_origins` to only your domain |
| **HTTPS** | Use Let's Encrypt (Linux) or Cloudflare Tunnel (any OS) |
| **Token Expiry** | Reduce `ACCESS_TOKEN_EXPIRE_MINUTES` from 1440 to 60-120 |
| **Rate Limiting** | Add `slowapi` to FastAPI for API rate limiting |
| **Firewall** | Only expose ports 80/443; keep 5432, 8000, 11434 internal |

### Performance Tuning

| Setting | Recommendation |
|---------|---------------|
| **Uvicorn workers** | Use `--workers 2` for multi-core (not with `--reload`) |
| **Ollama GPU** | Use GPU if available — reduces pipeline from 3 min to ~30 sec |
| **PostgreSQL** | Increase `shared_buffers` to 25% of RAM |
| **Connection pooling** | SQLAlchemy default pool is fine for single-server |

### Backup

```bash
# Backup database
pg_dump -U postgres aml_system > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres aml_system < backup_20260218.sql
```

---

## 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` on :8000 | Backend not running. Check `systemctl status aml-backend` or Docker logs |
| `Connection refused` on :11434 | Ollama not running. Run `ollama serve` or `systemctl start ollama` |
| `model not found` | Pull models: `ollama pull mistral:7b-instruct-q4_K_M` |
| Pipeline returns 500 | Check backend logs: `docker compose logs backend` or `journalctl -u aml-backend` |
| Frontend blank page | React Router issue — ensure Nginx has `try_files $uri /index.html` |
| CORS errors in browser | Update `allow_origins` in `main.py` to include your domain |
| Pipeline takes > 5 min | Ollama running on CPU — get a GPU or use a smaller model |
| `pgvector` extension error | Run `CREATE EXTENSION IF NOT EXISTS vector;` in PostgreSQL |
| Out of memory | Mistral 7B needs ~6 GB RAM. Reduce with `mistral:7b-instruct-q4_0` (smaller quant) |
| `WeasyPrint` import error | Install system libs: `apt install libpango-1.0-0 libpangocairo-1.0-0` |

---

## Minimum Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16 GB |
| **GPU** | None (CPU works) | NVIDIA 8+ GB VRAM |
| **Disk** | 10 GB | 20 GB (models ~5 GB) |
| **OS** | Windows 10+ / Ubuntu 22.04+ | Ubuntu 22.04 LTS |

---

*Generated for the AML SAR System v2.0 — 7-Agent Pipeline Architecture*
