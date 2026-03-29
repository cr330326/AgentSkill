# SSL Setup with Docker

Guide for setting up SSL/TLS certificates in a Dockerized environment.

## Table of Contents

1. [Option A: Certbot with Nginx](#option-a-certbot-with-nginx)
2. [Option B: Traefik with auto-SSL](#option-b-traefik-with-auto-ssl)
3. [Option C: Self-signed for development](#option-c-self-signed-for-development)

## Option A: Certbot with Nginx

Use Let's Encrypt with Certbot for free, auto-renewing certificates.

### docker-compose.yml additions

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot_webroot:/var/www/certbot:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - app
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_webroot:/var/www/certbot
      - certbot_certs:/etc/letsencrypt
    entrypoint: /bin/sh -c 'trap exit TERM; while :; do sleep 12h & wait $${!}; certbot renew; done'

volumes:
  certbot_webroot:
  certbot_certs:
```

### Initial certificate request

```bash
# Step 1: Start nginx without SSL first (use an HTTP-only config)
docker compose up -d nginx

# Step 2: Request certificate
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  -d example.com \
  -d www.example.com \
  --email admin@example.com \
  --agree-tos \
  --no-eff-email

# Step 3: Switch nginx to SSL config and restart
docker compose restart nginx
```

### Nginx config for Certbot challenge

Add this location block to the HTTP server:

```nginx
server {
    listen 80;
    server_name example.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect everything else to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}
```

### Renewal

Certbot auto-renews via the entrypoint loop. To manually renew:

```bash
docker compose run --rm certbot renew
docker compose restart nginx
```

## Option B: Traefik with auto-SSL

Traefik handles SSL automatically with zero Nginx configuration needed.

### docker-compose.yml

```yaml
services:
  traefik:
    image: traefik:v3.0
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_certs:/letsencrypt
    restart: unless-stopped

  app:
    build: .
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app.rule=Host(`example.com`)"
      - "traefik.http.routers.app.entrypoints=websecure"
      - "traefik.http.routers.app.tls.certresolver=letsencrypt"
      - "traefik.http.services.app.loadbalancer.server.port=3000"
    restart: unless-stopped

volumes:
  traefik_certs:
```

This configuration:
- Automatically obtains and renews Let's Encrypt certificates
- Redirects HTTP to HTTPS
- Discovers services via Docker labels (no config files to maintain)

## Option C: Self-signed for development

Generate self-signed certificates for local development or testing:

```bash
mkdir -p nginx/ssl

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/C=US/ST=Dev/L=Dev/O=Dev/CN=localhost"
```

Mount in docker-compose.yml:

```yaml
services:
  nginx:
    volumes:
      - ./nginx/ssl:/etc/nginx/ssl:ro
```

Self-signed certificates will show browser warnings. Only use for development.
