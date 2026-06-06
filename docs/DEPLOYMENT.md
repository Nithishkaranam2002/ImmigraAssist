# Production Deployment Guide

## Requirements

- Docker & Docker Compose
- 4GB+ RAM (8GB recommended for full scrape)
- OpenAI API key
- Domain (optional, for HTTPS)

## Quick Deploy

```bash
git clone https://github.com/Nithishkaranam2002/ImmigraAssist.git
cd ImmigraAssist
cp backend/.env.example backend/.env
# Edit backend/.env with your secrets

docker compose up -d --build
```

App will be available at `http://<server-ip>` on port 80.

## Production Checklist

- [ ] Set strong `SECRET_KEY` and `ADMIN_PASSWORD` in `backend/.env`
- [ ] Set `CORS_ORIGINS` to your domain (not `*`)
- [ ] Set `DEBUG=False` to disable public `/docs`
- [ ] Enable `RATE_LIMIT_ENABLED=true` (default)
- [ ] Add HTTPS via Caddy or nginx + Let's Encrypt
- [ ] Add swap (4GB) on small droplets to prevent OOM during model load
- [ ] Rotate demo credentials before sharing publicly

## Updating

```bash
cd ImmigraAssist
git pull
docker compose build frontend backend
docker compose up -d frontend backend
```

## Health Checks

- Frontend: `curl http://localhost/` → 200
- Backend: `curl http://localhost/health` → `{"status":"healthy"}`
- Admin health: `GET /api/v1/admin/health` (requires admin JWT)
