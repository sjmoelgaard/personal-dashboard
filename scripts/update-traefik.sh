#!/bin/bash
# Update Traefik dynamic config with current container IPs from coolify network.
# Run after: docker compose up -d --build

set -e

FRONTEND_IP=$(docker inspect personal-dashboard-frontend-1 --format '{{range .NetworkSettings.Networks}}{{if eq (index . "NetworkID") ""}}{{else}}{{end}}{{end}}' 2>/dev/null || true)

# Get IPs from the coolify network
FRONTEND_IP=$(docker inspect personal-dashboard-frontend-1 --format '{{(index .NetworkSettings.Networks "coolify").IPAddress}}')
BACKEND_IP=$(docker inspect personal-dashboard-backend-1 --format '{{(index .NetworkSettings.Networks "coolify").IPAddress}}')
NTFY_IP=$(docker inspect personal-dashboard-ntfy-1 --format '{{(index .NetworkSettings.Networks "coolify").IPAddress}}')

echo "Frontend IP: $FRONTEND_IP"
echo "Backend IP:  $BACKEND_IP"
echo "Ntfy IP:     $NTFY_IP"

cat > /tmp/personal-dashboard.yml << EOF
http:
  routers:
    dashboard-frontend:
      rule: "Host(\`mylife.smoelgaard.com\`)"
      entryPoints:
        - https
      service: dashboard-frontend
      tls:
        certResolver: letsencrypt
      priority: 100

    dashboard-api:
      rule: "Host(\`mylife.smoelgaard.com\`) && PathPrefix(\`/api\`)"
      entryPoints:
        - https
      service: dashboard-api
      tls:
        certResolver: letsencrypt
      priority: 110

    dashboard-ntfy:
      rule: "Host(\`ntfy.smoelgaard.com\`)"
      entryPoints:
        - https
      service: dashboard-ntfy
      tls:
        certResolver: letsencrypt
      priority: 100

  services:
    dashboard-frontend:
      loadBalancer:
        servers:
          - url: "http://${FRONTEND_IP}:80"

    dashboard-api:
      loadBalancer:
        servers:
          - url: "http://${BACKEND_IP}:8000"

    dashboard-ntfy:
      loadBalancer:
        servers:
          - url: "http://${NTFY_IP}:80"
EOF

docker cp /tmp/personal-dashboard.yml coolify-proxy:/traefik/dynamic/personal-dashboard.yml
echo "Traefik config updated."

sleep 2
curl -s https://mylife.smoelgaard.com/api/health && echo " ← backend OK"
