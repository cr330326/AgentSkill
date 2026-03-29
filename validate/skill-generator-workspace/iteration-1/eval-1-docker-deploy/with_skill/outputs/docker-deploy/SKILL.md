---
name: docker-deploy
description: >
  Containerize applications and deploy them to servers using Docker and Docker Compose.
  Use this skill when the user wants to dockerize an app, create a Dockerfile, write a
  docker-compose.yml, set up multi-service orchestration, deploy containers to a server,
  or says "docker deploy", "containerize", "docker compose", "multi-container",
  "docker 部署", "容器化", "容器部署", "多服务编排". Also use when the user describes
  a multi-service architecture (e.g. web app + database + cache + reverse proxy) even if
  they don't explicitly mention Docker -- if containers are the natural deployment path,
  use this skill. Do NOT use for Kubernetes orchestration (use a k8s-specific skill),
  CI/CD pipeline setup (use ci-cd skill), or cloud-managed container services like
  AWS ECS or Azure Container Apps (use cloud-specific skills).
---

# Docker Deploy

Containerize applications and deploy them to servers with Docker and Docker Compose.
Covers everything from writing Dockerfiles to multi-service orchestration to production
deployment over SSH.

## When to use

- User has an application (any language/framework) and wants to run it in Docker
- User needs a `docker-compose.yml` for multiple services (app + db + cache + proxy, etc.)
- User wants to deploy containers to a remote server
- User needs help optimizing Dockerfiles (multi-stage builds, layer caching, image size)
- User has an existing Docker setup that needs debugging or improvement

## Prerequisites

- Docker Engine installed on the local machine (for building/testing)
- Docker Compose v2 (comes with Docker Desktop, or install `docker-compose-plugin`)
- SSH access to the target server (for remote deployment)
- The target server should have Docker and Docker Compose installed

Check prerequisites with:
```bash
docker --version
docker compose version
```

## Workflow

### Phase 1: Analyze the application

Before writing any Docker configuration, understand what needs to be containerized.

#### 1.1 Identify the application stack

Read the project structure and determine:

- **Language/runtime**: Node.js, Python, Go, Java, Ruby, PHP, Rust, etc.
- **Framework**: Express, Django, FastAPI, Spring Boot, Rails, Laravel, etc.
- **Build system**: npm, pip, cargo, gradle, maven, etc.
- **Entry point**: How the app starts (e.g., `node server.js`, `python manage.py runserver`)
- **Port**: What port the app listens on
- **Static assets**: Whether there's a frontend build step

#### 1.2 Identify supporting services

Common patterns:

| Service | Image | Default port | Typical use |
|---------|-------|-------------|-------------|
| PostgreSQL | `postgres:16-alpine` | 5432 | Relational database |
| MySQL | `mysql:8` | 3306 | Relational database |
| Redis | `redis:7-alpine` | 6379 | Cache, sessions, queues |
| MongoDB | `mongo:7` | 27017 | Document database |
| Nginx | `nginx:alpine` | 80/443 | Reverse proxy, static files |
| Traefik | `traefik:v3` | 80/443/8080 | Reverse proxy with auto-SSL |
| RabbitMQ | `rabbitmq:3-management-alpine` | 5672/15672 | Message broker |
| MinIO | `minio/minio` | 9000/9001 | Object storage (S3-compatible) |

#### 1.3 Identify environment configuration

Look for:
- `.env` files or `.env.example`
- Config files that reference environment variables
- Database connection strings, API keys, secrets
- Development vs. production differences

### Phase 2: Create the Dockerfile

#### 2.1 Choose a base image

Prefer slim/alpine variants for production. Use the decision table below:

| Language | Dev image | Prod image |
|----------|-----------|------------|
| Node.js | `node:20` | `node:20-alpine` |
| Python | `python:3.12` | `python:3.12-slim` |
| Go | `golang:1.22` | `gcr.io/distroless/static-debian12` |
| Java | `eclipse-temurin:21` | `eclipse-temurin:21-jre-alpine` |
| Rust | `rust:1.77` | `debian:bookworm-slim` |
| PHP | `php:8.3-fpm` | `php:8.3-fpm-alpine` |

#### 2.2 Write a multi-stage Dockerfile

Multi-stage builds keep production images small. The general structure:

```dockerfile
# Stage 1: Build
FROM <dev-image> AS builder
WORKDIR /app
COPY package-files .
RUN install-dependencies
COPY . .
RUN build-command

# Stage 2: Production
FROM <prod-image>
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE <port>
USER node
CMD ["node", "dist/server.js"]
```

#### 2.3 Dockerfile best practices

- **Order layers by change frequency** -- copy dependency files first, then source code. This maximizes layer cache hits.
- **Use `.dockerignore`** -- exclude `node_modules/`, `.git/`, `*.log`, test files, and local env files.
- **Run as non-root** -- add `USER <username>` before CMD. Most base images provide a non-root user (e.g., `node` for Node.js images).
- **Pin versions** -- use specific tags (`node:20.11-alpine`) rather than `latest` in production.
- **Minimize layers** -- combine related RUN commands with `&&`.
- **Use HEALTHCHECK** -- add a health check so Docker can monitor container status:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1
  ```

### Phase 3: Write docker-compose.yml

#### 3.1 Structure

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${APP_PORT:-3000}:3000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:

networks:
  app-network:
    driver: bridge
```

#### 3.2 Compose best practices

- **Use `depends_on` with health checks** -- `condition: service_healthy` ensures databases are ready before the app starts.
- **Named volumes for persistence** -- never use bind mounts for database data in production.
- **Environment variables** -- use `.env` file or `${VAR:-default}` syntax. Never hardcode secrets in compose files.
- **Restart policies** -- use `unless-stopped` for production services.
- **Custom networks** -- isolate service groups. Only expose ports that need external access.
- **Resource limits** -- set memory and CPU limits for production:
  ```yaml
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
  ```

#### 3.3 Adding a reverse proxy

For production, add Nginx or Traefik in front of the app:

```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - app-network
```

See `references/nginx-config.md` for Nginx configuration templates.

### Phase 4: Create supporting files

#### 4.1 .dockerignore

Always create a `.dockerignore` to keep the build context small:

```
.git
.gitignore
node_modules
npm-debug.log
.env
.env.local
*.md
tests/
__tests__/
coverage/
.vscode/
.idea/
docker-compose*.yml
Dockerfile
```

#### 4.2 .env.example

Provide a template so users know what environment variables are needed:

```env
# Application
APP_PORT=3000
NODE_ENV=production

# Database
DB_HOST=db
DB_PORT=5432
DB_USER=user
DB_PASSWORD=changeme
DB_NAME=mydb

# Redis
REDIS_URL=redis://redis:6379

# Secrets (change these!)
JWT_SECRET=change-this-to-a-random-string
```

#### 4.3 Deploy script

Create a deployment helper script at `deploy.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Configuration
REMOTE_HOST="${DEPLOY_HOST:?Set DEPLOY_HOST}"
REMOTE_USER="${DEPLOY_USER:-root}"
REMOTE_DIR="${DEPLOY_DIR:-/opt/app}"

echo "Deploying to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}..."

# Sync project files
rsync -avz --exclude '.git' --exclude 'node_modules' \
  -e ssh ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

# Build and restart on remote
ssh "${REMOTE_USER}@${REMOTE_HOST}" << 'EOF'
  cd ${REMOTE_DIR}
  docker compose pull
  docker compose build --no-cache
  docker compose up -d
  docker compose ps
  echo "Deployment complete!"
EOF
```

### Phase 5: Deploy to server

#### 5.1 First-time server setup

On the remote server, ensure Docker is installed:

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Verify
docker --version
docker compose version
```

#### 5.2 Deploy

Run the deployment:

```bash
# Option A: Using the deploy script
chmod +x deploy.sh
DEPLOY_HOST=your-server.com ./deploy.sh

# Option B: Manual deployment
scp -r . user@server:/opt/app/
ssh user@server 'cd /opt/app && docker compose up -d'
```

#### 5.3 Post-deploy verification

```bash
# Check containers are running
docker compose ps

# View logs
docker compose logs -f app

# Test the endpoint
curl -f http://localhost:3000/health
```

## Common patterns

### Development vs. production compose files

Use `docker-compose.override.yml` for development-specific settings:

```yaml
# docker-compose.override.yml (auto-loaded in dev)
services:
  app:
    build:
      target: builder    # Use the build stage for hot-reload
    volumes:
      - .:/app           # Mount source code for hot-reload
      - /app/node_modules # Exclude node_modules from mount
    environment:
      - NODE_ENV=development
    command: npm run dev
```

Production uses only the base `docker-compose.yml`. For explicit production config:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### SSL with Let's Encrypt

For automatic SSL, use Traefik or Certbot with Nginx. See `references/ssl-setup.md`.

### Logging and monitoring

Add log rotation to prevent disk exhaustion:

```yaml
services:
  app:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|---------|
| Container exits immediately | App crashes on startup | Check `docker compose logs app` for error |
| Port already in use | Another process on the port | Change host port in compose or stop conflicting process |
| Database connection refused | DB not ready when app starts | Add `depends_on` with `condition: service_healthy` |
| Permission denied on volume | UID mismatch | Match container user UID to host directory owner |
| Build cache not working | COPY order wrong | Copy dependency files before source code |
| Image too large | No multi-stage build | Use multi-stage Dockerfile, add `.dockerignore` |
| Container can't resolve service name | Not on same network | Ensure services share a Docker network |

## Output checklist

After generating Docker configuration, verify these files exist and are correct:

- [ ] `Dockerfile` with multi-stage build
- [ ] `.dockerignore` with appropriate exclusions
- [ ] `docker-compose.yml` with all required services
- [ ] `.env.example` documenting all environment variables
- [ ] Nginx/proxy config if the app is web-facing
- [ ] `deploy.sh` if remote deployment is needed
- [ ] Health check endpoints in both Dockerfile and compose
