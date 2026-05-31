# Phase 1 Deploy Checklist

Run these steps on your Hetzner server to bring up the dashboard.

## Prerequisites
- Docker and Docker Compose installed on the server
- Domain `mylife.smoelgaard.com` DNS A-record pointing to server IP
- Domain `ntfy.smoelgaard.com` DNS A-record pointing to same server IP

## Steps

### 1. Clone and configure
```bash
git clone <repo-url> personal-dashboard
cd personal-dashboard
cp .env.example .env
```

Edit `.env` and fill in:
- `POSTGRES_PASSWORD` — a strong random password
- `DATABASE_URL` — update password to match POSTGRES_PASSWORD
- `JWT_SECRET` — run `openssl rand -hex 32`
- `OWNER_PASSWORD` — your dashboard login password
- `ANTHROPIC_API_KEY` — from console.anthropic.com (can leave empty for now)
- `DOMAIN=mylife.smoelgaard.com`

### 2. Start the stack
```bash
docker compose up -d
```

### 3. Run database migrations
```bash
docker compose exec backend python -m alembic upgrade head
```

### 4. Verify health
```bash
curl https://mylife.smoelgaard.com/api/health
# Expected: {"status":"ok"}
```

### 5. Test login
Open https://mylife.smoelgaard.com in your browser and log in with OWNER_PASSWORD.

### 6. Test Ntfy
```bash
curl -d "Test" -H "Title: Test" https://ntfy.smoelgaard.com/mylife
```
Open the Ntfy app and subscribe to `https://ntfy.smoelgaard.com/mylife`.

### 7. Verify TLS
Both domains should have green padlock (Caddy auto-provisions Let's Encrypt).

## Backup Setup (do after verifying everything works)
```bash
# Add to server crontab (crontab -e):
0 2 * * * docker compose exec -T db pg_dump -U dashboard dashboard | gzip | gpg --symmetric --cipher-algo AES256 -o /backup/dashboard-$(date +%Y%m%d).sql.gz.gpg
```
Replace with actual Hetzner Storage Box path once configured.
