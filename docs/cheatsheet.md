# Personal Dashboard — Cheatsheet

## Servere

| Server | IP | Formål |
|---|---|---|
| coolifyserver | 46.62.165.156 | Personal Dashboard (dette projekt) |
| Gammel Hetzner-server | (den anden server) | Fodboldprojekt — rør ikke nginx! |

## SSH Login

```bash
# Login på coolify-server (personal dashboard)
ssh root@46.62.165.156

# Login på gammel server (fodboldprojekt)
ssh root@<gammel-server-ip>
```

## Vigtige stier på coolify-server

```bash
# Personal dashboard projekt
cd ~/personal-dashboard

# .env fil (passwords og secrets)
nano ~/personal-dashboard/.env

# Traefik routing config (HTTPS routing)
/traefik/dynamic/personal-dashboard.yml
```

## Docker kommandoer

```bash
# Se kørende containers
docker ps

# Se status på dashboard containers
cd ~/personal-dashboard
docker compose ps

# Stop alle containers
docker compose down

# Start alle containers
docker compose up -d

# FULD DEPLOY (efter kode-ændringer fra Windows: git push)
cd ~/personal-dashboard
git pull
docker compose down
docker compose up -d --build
bash scripts/update-traefik.sh     # ← VIGTIGT: opdater Traefik IPs efter rebuild!
docker compose exec backend python -m alembic upgrade head

# Se logs fra en container
docker logs personal-dashboard-backend-1
docker logs personal-dashboard-frontend-1

# Kør database migration
docker compose exec backend python -m alembic upgrade head
```

## Traefik routing

Traefik bruger en statisk config-fil i coolify-proxy containeren. Den **skal opdateres efter hvert deploy** fordi container IPs kan ændre sig.

```bash
# Opdatér Traefik routing (kør dette efter docker compose up --build)
cd ~/personal-dashboard
bash scripts/update-traefik.sh
```

## URLs

| URL | Formål |
|---|---|
| https://mylife.smoelgaard.com | Personal Dashboard |
| https://ntfy.smoelgaard.com/mylife | Push notifikationer |
| http://46.62.165.156:8000 | Coolify UI |

## GitHub

```bash
# Repository
https://github.com/sjmoelgaard/personal-dashboard

# Push ændringer fra Windows
cd "C:\Users\stm\OneDrive - Ziton\Documents\Claude\Personal-dashboard"
git add .
git commit -m "beskrivelse af ændring"
git push

# Hent ændringer på server
cd ~/personal-dashboard
git pull
docker compose up -d --build
```

## Lokale stier (Windows)

```
Projekt:  C:\Users\stm\OneDrive - Ziton\Documents\Claude\Personal-dashboard
.env:     C:\Users\stm\OneDrive - Ziton\Documents\Claude\Personal-dashboard\.env (ikke committed!)
Spec:     docs/superpowers/specs/2026-05-31-personal-dashboard-design.md
Plan:     docs/superpowers/plans/2026-05-31-phase-1-shell.md
```

## Hvis noget går galt

```bash
# Genstart alle containers
cd ~/personal-dashboard
docker compose restart

# Tjek at backend svarer
curl http://localhost:8801/api/health

# Genindlæs Traefik routing (hvis HTTPS ikke virker)
docker exec coolify-proxy sh -c 'ls /traefik/dynamic/'

# Tjek container logs
docker compose logs backend
docker compose logs frontend
```
