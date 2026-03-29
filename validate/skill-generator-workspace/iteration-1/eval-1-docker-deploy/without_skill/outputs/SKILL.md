---
name: docker-deploy
description: >
  Containerize and deploy applications to servers using Docker and Docker Compose.
  Supports multi-service orchestration, Dockerfile generation, compose file authoring,
  image building, container management, and production deployment best practices.
  Use when user asks to "dockerize", "containerize", "deploy with docker",
  "docker compose", "multi-service deployment", "container orchestration",
  or needs help with Dockerfile, docker-compose.yml, or server deployment.
---

# Docker Deploy Skill

Helps users containerize applications and deploy them to servers using Docker and Docker Compose, with support for multi-service orchestration.

## Scope

**IN SCOPE:**
- Generating Dockerfiles for various application stacks (Node.js, Python, Go, Java, Rust, PHP, Ruby, .NET, static sites)
- Authoring `docker-compose.yml` / `compose.yml` files with multi-service orchestration
- Building and pushing Docker images
- Deploying containers to remote servers via SSH
- Configuring networks, volumes, environment variables, secrets, and health checks
- Setting up reverse proxies (Nginx, Traefik, Caddy) as compose services
- Database services (PostgreSQL, MySQL, MongoDB, Redis) as compose dependencies
- SSL/TLS certificate automation (Let's Encrypt via Traefik/Caddy/certbot)
- CI/CD integration for automated Docker deployments
- Troubleshooting container issues (logs, exec, inspect)

**OUT OF SCOPE:**
- Kubernetes / K8s orchestration (suggest user find a dedicated k8s skill)
- Cloud-provider managed container services (ECS, Cloud Run, Azure Container Apps) beyond basic Docker host deployment
- Building the application code itself (focus is on containerization and deployment)

## Workflow

### Phase 1: Analyze the Application

1. **Identify the tech stack** by examining the project files:
   - Look for `package.json` (Node.js), `requirements.txt` / `pyproject.toml` / `Pipfile` (Python), `go.mod` (Go), `pom.xml` / `build.gradle` (Java), `Cargo.toml` (Rust), `composer.json` (PHP), `Gemfile` (Ruby), `*.csproj` (C#/.NET)
   - Check for existing `Dockerfile`, `docker-compose.yml`, or `.dockerignore`
   - Identify the application entry point, build commands, and runtime requirements
   - Detect required services (databases, caches, message queues, etc.)

2. **Ask clarifying questions** if the following are unclear:
   - Target deployment environment (local dev, staging, production)
   - Required external services (DB, cache, queue, object storage)
   - Domain name and SSL requirements
   - Resource constraints (memory, CPU limits)
   - Whether the user needs a reverse proxy

### Phase 2: Generate Dockerfile

Follow these best practices when generating Dockerfiles:

#### Multi-stage Builds

Always use multi-stage builds for compiled languages and frontend assets to minimize image size.

```dockerfile
# Example: Node.js multi-stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
EXPOSE 3000
USER node
CMD ["node", "dist/index.js"]
```

#### Dockerfile Best Practices

- **Base image**: Use specific version tags (not `latest`), prefer `-alpine` or `-slim` variants
- **Layer ordering**: Copy dependency manifests first, install dependencies, then copy source code (maximizes layer caching)
- **Security**: Add a non-root `USER` directive; never run as root in production
- **`.dockerignore`**: Always generate a `.dockerignore` alongside the Dockerfile
- **Health checks**: Include `HEALTHCHECK` instruction when appropriate
- **Labels**: Add `LABEL` for maintainer, version, description metadata
- **Signal handling**: Use `exec` form for `CMD` (JSON array syntax) so the process receives signals properly
- **Minimize layers**: Combine related `RUN` commands with `&&`

#### Stack-Specific Templates

Refer to `references/dockerfile-templates.md` for ready-to-use Dockerfile templates for each supported stack.

### Phase 3: Author Docker Compose File

Use Compose Specification (v3.8+ / compose spec) format.

#### Compose File Structure

```yaml
# compose.yml (preferred filename per Compose Specification)
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${APP_PORT:-3000}:3000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    networks:
      - app-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"

  db:
    image: postgres:16-alpine
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME:-app}
      POSTGRES_USER: ${DB_USER:-app}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-app}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped

volumes:
  db-data:

networks:
  app-network:
    driver: bridge
```

#### Compose Best Practices

- **Environment variables**: Use `.env` file with `env_file` directive; use `${VAR:-default}` syntax for defaults and `${VAR:?error}` for required vars
- **Depends on with health checks**: Always use `depends_on` with `condition: service_healthy` instead of bare `depends_on`
- **Named volumes**: Use named volumes for persistent data; never bind-mount production data directories
- **Networks**: Define explicit networks; avoid using the default bridge
- **Restart policy**: Use `restart: unless-stopped` for production services
- **Resource limits**: Set `deploy.resources.limits` for memory and CPU
- **Secrets**: For sensitive data, prefer Docker secrets or mounted files over environment variables in production
- **Logging**: Configure logging drivers if needed (`json-file` with `max-size` and `max-file`)

#### Common Service Patterns

Refer to `references/compose-services.md` for pre-built service blocks for:
- Reverse proxies (Nginx, Traefik, Caddy)
- Databases (PostgreSQL, MySQL, MongoDB)
- Caches (Redis, Memcached)
- Message queues (RabbitMQ, NATS)
- Monitoring (Prometheus, Grafana)

### Phase 4: Generate Supporting Files

Always generate these alongside the Dockerfile and compose file:

1. **`.dockerignore`** - Exclude unnecessary files from build context:
   ```
   .git
   .github
   node_modules
   .env*
   !.env.example
   *.md
   .vscode
   .idea
   __pycache__
   *.pyc
   .pytest_cache
   coverage
   .nyc_output
   dist
   build
   ```

2. **`.env.example`** - Template for required environment variables (never commit actual `.env`):
   ```
   # Application
   APP_PORT=3000
   NODE_ENV=production

   # Database
   DB_HOST=db
   DB_PORT=5432
   DB_NAME=app
   DB_USER=app
   DB_PASSWORD=changeme

   # Redis
   REDIS_URL=redis://redis:6379
   ```

3. **`deploy.sh`** - Deployment helper script (when deploying to remote server):
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   # See references/deploy-script-template.sh for full template
   ```

### Phase 5: Build and Test Locally

Guide the user through local validation:

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f app

# Run health checks
docker compose exec app curl -f http://localhost:3000/health || echo "Health check failed"

# Stop services
docker compose down
```

### Phase 6: Deploy to Remote Server

#### Option A: Direct Docker Compose on Server

1. **Prepare the server** (first-time setup):
   ```bash
   # Install Docker and Docker Compose on the remote server
   ssh user@server 'curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER'
   ```

2. **Transfer files and deploy**:
   ```bash
   # Copy project files to server
   rsync -avz --exclude='.git' --exclude='node_modules' ./ user@server:/opt/app/

   # SSH into server and deploy
   ssh user@server 'cd /opt/app && docker compose pull && docker compose up -d --build'
   ```

3. **Verify deployment**:
   ```bash
   ssh user@server 'cd /opt/app && docker compose ps && docker compose logs --tail=50 app'
   ```

#### Option B: Build Locally, Push Image, Pull on Server

1. **Build and push**:
   ```bash
   docker build -t registry.example.com/app:latest .
   docker push registry.example.com/app:latest
   ```

2. **Pull and deploy on server**:
   ```bash
   ssh user@server 'cd /opt/app && docker compose pull && docker compose up -d'
   ```

#### Option C: CI/CD Automated Deployment

Refer to `references/cicd-templates.md` for GitHub Actions and GitLab CI templates.

### Phase 7: Production Hardening

For production deployments, verify:

- [ ] Non-root user in Dockerfile
- [ ] Health checks defined for all services
- [ ] Resource limits set (memory, CPU)
- [ ] Restart policies configured
- [ ] Volumes for persistent data use named volumes
- [ ] Sensitive data uses secrets, not plain environment variables
- [ ] Logging configured with rotation (`max-size`, `max-file`)
- [ ] SSL/TLS termination configured (via reverse proxy)
- [ ] Firewall rules restrict exposed ports
- [ ] Backup strategy for database volumes
- [ ] Monitoring and alerting in place

## Troubleshooting

### Common Issues

| Problem | Diagnosis | Fix |
|---------|-----------|-----|
| Container exits immediately | `docker compose logs <service>` | Check entry point, missing env vars, or crash in app |
| Port already in use | `docker compose ps` or `lsof -i :<port>` | Change host port mapping or stop conflicting service |
| Build cache not working | Layers rebuilt unnecessarily | Reorder Dockerfile: deps before source code |
| Container can't reach another | DNS resolution failure | Ensure both on same network; use service name as hostname |
| Volume permission denied | UID mismatch | Match container user UID to host volume owner |
| Out of disk space | `docker system df` | `docker system prune -a --volumes` (caution: removes unused data) |
| Image too large | `docker images` | Use multi-stage build; use alpine base; add `.dockerignore` |
| Health check failing | `docker inspect <container>` | Verify health check command runs inside container context |

### Useful Diagnostic Commands

```bash
# View real-time logs
docker compose logs -f --tail=100

# Execute shell in running container
docker compose exec <service> sh

# Inspect container details
docker inspect <container_id>

# Check resource usage
docker stats

# List networks and inspect
docker network ls
docker network inspect <network_name>

# Clean up unused resources
docker system prune -af --volumes
```

## Rules

- NEVER put real passwords, API keys, or secrets directly in `docker-compose.yml` or Dockerfiles. Always use `.env` files (excluded from git) or Docker secrets.
- NEVER use `latest` tag for base images in production Dockerfiles. Always pin to a specific version.
- NEVER expose database ports to the public internet. Keep them on internal Docker networks only.
- ALWAYS generate a `.dockerignore` file when creating a Dockerfile.
- ALWAYS generate a `.env.example` file when using environment variables.
- ALWAYS use health checks with `depends_on` conditions for service dependencies.
- ALWAYS verify the user's existing project structure before generating files to avoid overwriting.
- PREFER `compose.yml` as the filename (Compose Specification standard) over `docker-compose.yml`, but respect the user's existing convention.
- WARN the user before running any destructive commands (`docker system prune`, `docker volume rm`).
